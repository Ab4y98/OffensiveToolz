import logging
from copy import deepcopy
import re
import netaddr
import yaml
from spiderfoot import SpiderFootDb


class SpiderFootCorrelator:
    """SpiderFoot correlation capabilities."""

    log = logging.getLogger("spiderfoot.correlator")
    dbh = None
    scanId = None
    types = None
    rules = list()
    type_entity_map = dict()

    # For syntax checking
    mandatory_components = ["meta", "collections", "headline"]
    components = {
        # collect a set of data elements based on various conditions
        "meta": {
            "strict": ["name", "description", "risk"],
            "optional": ["author", "url"]
        },
        "collections": {
            "strict": ["collect"]
        },
        "aggregation": {
            "strict": ["field"]
        },
        # TODO: Make the rule checking per analysis method
        "analysis": {
            "strict": ["method"],
            "optional": ["field", "maximum_percent", "noisy_percent", "minimum", "maximum", "must_be_unique", "match_method"]
        },
        "headline": {},
        "id": {},
        "version": {},
        "enabled": {},
        "rawYaml": {}
    }

    def __init__(self, dbh: SpiderFootDb, ruleset: dict, scanId: str = None):
        self.dbh = dbh
        self.scanId = scanId
        self.types = self.dbh.eventTypes()
        self.rules = list()
        for t in self.types:
            self.type_entity_map[t[1]] = t[3]

        # Sanity-check the rules
        for rule_id in ruleset.keys():
            self.debug(f"Parsing rule {rule_id}...")
            try:
                self.rules.append(yaml.safe_load(ruleset[rule_id]))
                self.rules[len(self.rules) - 1]['rawYaml'] = ruleset[rule_id]
                # Strip any extra newlines that may have creeped into meta
                for rule in self.rules:
                    for k in rule['meta'].keys():
                        if isinstance(rule['meta'][k], str):
                            rule['meta'][k] = rule['meta'][k].strip()
                        else:
                            rule['meta'][k] = rule[k]
                continue
            except BaseException as e:
                raise SyntaxError(f"Unable to process a YAML correlation rule [{rule_id}]: {e}")

        if not self.check_ruleset_validity(self.rules):
            raise SyntaxError("Sanity check of correlation rules failed, aborting.")

    def get_ruleset(self):
        return self.rules

    def error(self, message):
        self.log.error(message)

    def debug(self, message):
        self.log.debug(message)

    def status(self, message):
        self.log.info(message)

    def run_correlations(self):
        for rule in self.rules:
            self.debug(f"Processing rule: {rule['id']}")
            results = self.process_rule(rule)
            if not results:
                self.debug(f"No results for rule {rule['id']}.")
                continue

            self.status(f"Rule {rule['id']} returned {len(results.keys())} results.")

            for result in results:
                self.create_correlation(rule, results[result])

    def build_db_criteria(self, matchrule: dict) -> dict:
        """Build up the criteria to be used to query the database.

        Args:
            matchrule (dict): dict representing a match rule

        Returns:
            dict: criteria to be used with SpiderFootDb.scanResultEvent()
        """

        criterias = dict()

        if "." in matchrule['field']:
            self.error("The first collection must either be data, type or module.")
            return None

        if matchrule['field'] == "data" and matchrule['type'] == "regex":
            self.error("The first collection cannot use regex on data.")
            return None

        if matchrule['field'] == "module" and matchrule['method'] != 'exact':
            self.error("Collection based on module names doesn't support regex.")
            return None

        # Build up the event type part of the query
        if matchrule['field'] == "type":
            if 'eventType' not in criterias:
                criterias['eventType'] = list()

            if matchrule['method'] == 'regex':
                if type(matchrule['value']) != list:
                    regexps = [matchrule['value']]
                else:
                    regexps = matchrule['value']

                for r in regexps:
                    for t in self.types:
                        if re.search(r, t[1]):
                            criterias['eventType'].append(t[1])

            if matchrule['method'] == 'exact':
                if type(matchrule['value']) != list:
                    matches = [matchrule['value']]
                else:
                    matches = matchrule['value']

                for m in matches:
                    matched = False
                    for t in self.types:
                        if t[1] == m:
                            matched = True
                            criterias['eventType'].append(t[1])
                    if not matched:
                        self.error(f"Invalid type specified: {m}")
                        return None

        # Match by module(s)
        if matchrule['field'] == "module":
            if 'srcModule' not in criterias:
                criterias['srcModule'] = list()

            if matchrule['method'] == 'exact':
                if type(matchrule['value']) == list:
                    criterias['srcModule'].extend(matchrule['value'])
                else:
                    criterias['srcModule'].append(matchrule['value'])

        # Match by data
        if matchrule['field'] == "data":
            if 'data' not in criterias:
                criterias['data'] = list()

            if type(matchrule['value']) == list:
                for v in matchrule['value']:
                    criterias['data'].append(v.encode('raw_unicode_escape'))
            else:
                criterias['data'].append(matchrule['value'].encode('raw_unicode_escape'))

        return criterias

    def enrich_event_sources(self, events: dict):
        event_chunks = [list(events.keys())[x:(x + 5000)] for x in range(0, len(list(events.keys())), 5000)]

        for chunk in event_chunks:
            # Get sources
            self.debug(f"Getting sources for {len(chunk)} events")
            source_data = self.dbh.scanElementSourcesDirect(self.scanId, chunk)
            for row in source_data:
                events[row[8]]['source'].append({
                    'type': row[15],
                    'data': row[2],
                    'module': row[16],
                    'id': row[9],
                    'entity_type': self.type_entity_map[row[15]]
                })

    def enrich_event_children(self, events: dict):
        event_chunks = [list(events.keys())[x:x + 5000] for x in range(0, len(list(events.keys())), 5000)]

        for chunk in event_chunks:
            # Get children
            self.debug(f"Getting children for {len(chunk)} events")
            child_data = self.dbh.scanResultEvent(self.scanId, sourceId=chunk)
            for row in child_data:
                events[row[9]]['child'].append({
                    'type': row[4],
                    'data': row[1],
                    'module': row[3],
                    'id': row[8]
                })

    def enrich_event_entities(self, events: dict):
        # Given our starting set of ids, loop through the source
        # of each until you have a match according to the criteria
        # provided.
        entity_missing = dict()
        for event_id in events:
            if 'source' not in events[event_id]:
                continue

            row = events[event_id]
            # Go through each source if it's not an ENTITY, capture its ID
            # so we can capture its source, otherwise copy the source as
            # an entity record, since it's of a valid type to be considered one.
            for source in row['source']:
                if source['entity_type'] in ['ENTITY', 'INTERNAL']:
                    events[row['id']]['entity'].append(source)
                else:
                    # key is the element ID that we need to find an entity for
                    # by checking its source, and the value is the original ID
                    # for which we are seeking an entity. As we traverse up the
                    # discovery path the key will change but the value must always
                    # point back to the same ID.
                    entity_missing[source['id']] = row['id']

        while len(entity_missing) > 0:
            self.debug(f"{len(entity_missing.keys())} entities are missing, going deeper...")
            new_missing = dict()
            self.debug(f"Getting sources for {len(entity_missing.keys())} items")
            if len(entity_missing.keys()) > 5000:
                chunks = [list(entity_missing.keys())[x:x + 5000] for x in range(0, len(list(entity_missing.keys())), 5000)]
                entity_data = list()
                self.debug("Fetching data in chunks")
                for chunk in chunks:
                    self.debug(f"chunk size: {len(chunk)}")
                    entity_data.extend(self.dbh.scanElementSourcesDirect(self.scanId, chunk))
            else:
                self.debug(f"fetching sources for {len(entity_missing)} items")
                entity_data = self.dbh.scanElementSourcesDirect(self.scanId, list(entity_missing.keys()))

            for entity_candidate in entity_data:
                event_id = entity_missing[entity_candidate[8]]
                if self.type_entity_map[entity_candidate[15]] not in ['ENTITY', 'INTERNAL']:
                    # key of this dictionary is the id we need to now get a source for,
                    # and the value is the original ID of the item missing an entity
                    new_missing[entity_candidate[9]] = event_id
                else:
                    events[event_id]['entity'].append({
                        'type': entity_candidate[15],
                        'data': entity_candidate[2],
                        'module': entity_candidate[16],
                        'id': entity_candidate[9],
                        'entity_type': self.type_entity_map[entity_candidate[15]]
                    })

            if len(new_missing) == 0:
                break

            entity_missing = deepcopy(new_missing)

    def collect_from_db(self, matchrule: dict, fetchChildren: bool, fetchSources: bool, fetchEntities: bool) -> list:
        events = dict()

        self.debug(f"match rule: {matchrule}")
        # Parse the criteria from the match rule
        query_args = self.build_db_criteria(matchrule)
        if not query_args:
            self.error(f"Error encountered parsing match rule: {matchrule}.")
            return None

        query_args['instanceId'] = self.scanId
        self.debug(f"db query: {query_args}")
        for row in self.dbh.scanResultEvent(**query_args):
            events[row[8]] = {
                'type': row[4],
                'data': row[1],
                'module': row[3],
                'id': row[8],
                'entity_type': self.type_entity_map[row[4]],
                'source': [],
                'child': [],
                'entity': []
            }

        # You need to fetch sources if you need entities, since
        # the source will often be the entity.
        if fetchSources or fetchEntities:
            self.enrich_event_sources(events)

        if fetchChildren:
            self.enrich_event_children(events)

        if fetchEntities:
            self.enrich_event_entities(events)

        self.debug(f"returning {len(events.values())} events from match_rule {matchrule}")
        return list(events.values())

    def event_extract(self, event: dict, field: str) -> list:
        if "." in field:
            ret = list()
            key, field = field.split(".")
            for subevent in event[key]:
                ret.extend(self.event_extract(subevent, field))
            return ret

        return [event[field]]

    def event_keep(self, event: dict, field: str, patterns: str, patterntype: str) -> bool:
        if "." in field:
            key, field = field.split(".")
            for subevent in event[key]:
                if self.event_keep(subevent, field, patterns, patterntype):
                    return True
            return False

        value = event[field]

        if patterntype == "exact":
            ret = False
            for pattern in patterns:
                if pattern.startswith("not "):
                    ret = True
                    pattern = re.sub(r"^not\s+", "", pattern)
                    if value == pattern:
                        return False
                else:
                    if value == pattern:
                        return True
            if ret:
                return True
            return False

        if patterntype == "regex":
            ret = False
            for pattern in patterns:
                if pattern.startswith("not "):
                    ret = True
                    pattern = re.sub(r"^not\s+", "", pattern)
                    if re.search(pattern, value, re.IGNORECASE):
                        return False
                else:
                    ret = False
                    if re.search(pattern, value, re.IGNORECASE):
                        return True
            if ret:
                return True
            return False

        return False

    def refine_collection(self, matchrule: dict, events: list) -> None:
        # Cull events from the events list if they
        # don't meet the match criteria
        patterns = list()

        if type(matchrule['value']) == list:
            for r in matchrule['value']:
                patterns.append(str(r))
        else:
            patterns = [str(matchrule['value'])]

        field = matchrule['field']
        self.debug(f"attempting to match {patterns} against the {field} field in {len(events)} events")

        # Go through each event, remove it if we shouldn't keep it
        # according to the match rule patterns.
        for event in events[:]:
            if not self.event_keep(event, field, patterns, matchrule['method']):
                self.debug(f"removing {event} because of {field}")
                events.remove(event)

    # Collect data for aggregation and analysis
    def collect_events(self, collection: dict, fetchChildren: bool, fetchSources: bool, fetchEntities: bool, collectIndex: int) -> list:
        step = 0

        for matchrule in collection:
            # First match rule means we fetch from the database, every
            # other step happens locally to avoid burdening the db.
            if step == 0:
                events = self.collect_from_db(matchrule,
                                              fetchEntities=fetchEntities,
                                              fetchChildren=fetchChildren,
                                              fetchSources=fetchSources)
                step += 1
                continue

            # Remove events in-place based on subsequent match-rules
            self.refine_collection(matchrule, events)

        # Stamp events with this collection ID for potential
        # use in analysis later.
        for e in events:
            e['_collection'] = collectIndex
            if fetchEntities:
                for ee in e['entity']:
                    ee['_collection'] = collectIndex
            if fetchChildren:
                for ce in e['child']:
                    ce['_collection'] = collectIndex
            if fetchSources:
                for se in e['source']:
                    se['_collection'] = collectIndex

        self.debug("returning collection...")
        return events

    # Aggregate events according to the rule
    def aggregate_events(self, rule: dict, events: list) -> dict:
        if 'field' not in rule:
            self.error("Unable to find field definition for aggregation in {rule['id']}")
            return False

        # strip sub fields that don't match value
        def event_strip(event, field, value):
            topfield, subfield = field.split(".")
            if field.startswith(topfield + "."):
                for s in event[topfield]:
                    if s[subfield] != value:
                        event[topfield].remove(s)

        ret = dict()
        for e in events:
            buckets = self.event_extract(e, rule['field'])
            for b in buckets:
                e_copy = deepcopy(e)
                # if the bucket is of a child, source or entity,
                # remove the children, sources or entities that
                # aren't matching this bucket
                if "." in rule['field']:
                    event_strip(e_copy, rule['field'], b)
                if b in ret:
                    ret[b].append(e_copy)
                    continue
                ret[b] = [e_copy]

        return ret

    # Analyze events according to the rule. Modifies buckets
    # in-place.
    def analyze_events(self, rule: dict, buckets: dict) -> None:
        self.debug(f"applying {rule}")
        if rule['method'] == "threshold":
            return self.analysis_threshold(rule, buckets)
        if rule['method'] == "outlier":
            return self.analysis_outlier(rule, buckets)
        if rule['method'] == "first_collection_only":
            return self.analysis_first_collection_only(rule, buckets)
        if rule['method'] == "match_all_to_first_collection":
            return self.analysis_match_all_to_first_collection(rule, buckets)
        if rule['method'] == "both_collections":
            # TODO: Implement when genuine case appears
            pass
        return None

    # Find buckets that are in the first collection
    def analysis_match_all_to_first_collection(self, rule: dict, buckets: dict) -> None:
        self.debug(f"called with buckets {buckets}")

        def check_event(events: list, reference: list) -> bool:
            for event_data in events:
                if rule['match_method'] == 'subnet':
                    for r in reference:
                        try:
                            self.debug(f"checking if {event_data} is in {r}")
                            if netaddr.IPAddress(event_data) in netaddr.IPNetwork(r):
                                self.debug(f"found subnet match: {event_data} in {r}")
                                return True
                        except Exception:
                            pass

                if rule['match_method'] == 'exact':
                    if event_data in reference:
                        self.debug(f"found exact match: {event_data} in {reference}")
                        return True

                if rule['match_method'] == 'contains':
                    for r in reference:
                        if event_data in r:
                            self.debug(f"found pattern match: {event_data} in {r}")
                            return True

            return False

        # 1. Build up the list of values from collection 0
        # 2. Go through each event in each collection > 0 and drop any events that aren't
        #    in collection 0.
        # 3. For each bucket, if there are no events from collection > 0, drop them.

        reference = set()
        for bucket in buckets:
            for event in buckets[bucket]:
                if event['_collection'] == 0:
                    reference.update(self.event_extract(event, rule['field']))

        for bucket in list(buckets.keys()):
            pluszerocount = 0
            for event in buckets[bucket][:]:
                if event['_collection'] == 0:
                    continue
                else:
                    pluszerocount += 1

                if not check_event(self.event_extract(event, rule['field']), reference):
                    buckets[bucket].remove(event)
                    pluszerocount -= 1

            # delete the bucket if there are no events > collection 0
            if pluszerocount == 0:
                del(buckets[bucket])

    def analysis_first_collection_only(self, rule: dict, buckets: dict) -> None:
        colzero = set()

        for bucket in buckets:
            for e in buckets[bucket]:
                if e['_collection'] == 0:
                    colzero.add(e[rule['field']])

        for bucket in list(buckets.keys()):
            delete = False
            for e in buckets[bucket]:
                if e['_collection'] > 0 and e[rule['field']] in colzero:
                    delete = True
                    break
            if delete:
                del(buckets[bucket])

        # Remove buckets with collection > 0 values
        for bucket in list(buckets.keys()):
            for e in buckets[bucket]:
                if e['_collection'] > 0:
                    del(buckets[bucket])
                    break

    def analysis_outlier(self, rule: dict, buckets: dict) -> None:
        countmap = dict()
        for bucket in list(buckets.keys()):
            countmap[bucket] = len(buckets[bucket])

        if len(list(countmap.keys())) == 0:
            for bucket in list(buckets.keys()):
                del(buckets[bucket])
            return

        total = float(sum(countmap.values()))
        avg = total / float(len(list(countmap.keys())))
        avgpct = (avg / total) * 100.0

        self.debug(f"average percent is {avgpct} based on {avg} / {total} * 100.0")
        if avgpct < rule.get('noisy_percent', 10):
            self.debug(f"Not correlating because the average percent is {avgpct} (too anomalous)")
            for bucket in list(buckets.keys()):
                del(buckets[bucket])
            return

        # Figure out which buckets don't contain outliers and delete them
        delbuckets = list()
        for bucket in buckets:
            if (countmap[bucket] / total) * 100.0 > rule['maximum_percent']:
                delbuckets.append(bucket)

        for bucket in set(delbuckets):
            del(buckets[bucket])

    def analysis_threshold(self, rule: dict, buckets: dict) -> None:
        for bucket in list(buckets.keys()):
            countmap = dict()
            for event in buckets[bucket]:
                e = self.event_extract(event, rule['field'])
                for ef in e:
                    if ef not in countmap:
                        countmap[ef] = 0
                    countmap[ef] += 1

            if not rule.get('count_unique_only'):
                for v in countmap:
                    if countmap[v] >= rule.get('minimum', 0) and countmap[v] <= rule.get('maximum', 999999999):
                        continue
                    # Delete the bucket of events if it didn't meet the
                    # analysis criteria.
                    if bucket in buckets:
                        del(buckets[bucket])
                continue

            # If we're only looking at the number of times the requested
            # field appears in the bucket...
            uniques = len(list(countmap.keys()))
            if uniques < rule.get('minimum', 0) or uniques > rule.get('maximum', 999999999):
                del(buckets[bucket])

    def analyze_field_scope(self, field: str) -> list:
        children = False
        source = False
        entity = False

        if field.startswith('child.'):
            children = True
        if field.startswith('source.'):
            source = True
        if field.startswith('entity.'):
            entity = True

        return children, source, entity

    # Analyze the rule for use of children, sources or entities
    # so that they can be fetched during collection
    def analyze_rule_scope(self, rule: dict) -> list:
        children = False
        source = False
        entity = False

        if rule.get('collections'):
            for collection in rule['collections']:
                for method in collection['collect']:
                    c, s, e = self.analyze_field_scope(method['field'])
                    if c:
                        children = True
                    if s:
                        source = True
                    if e:
                        entity = True

        if rule.get('aggregation'):
            c, s, e = self.analyze_field_scope(rule['aggregation']['field'])
            if c:
                children = True
            if s:
                source = True
            if e:
                entity = True

        if rule.get('analysis'):
            for analysis in rule['analysis']:
                if 'field' not in analysis:
                    continue
                c, s, e = self.analyze_field_scope(analysis['field'])
                if c:
                    children = True
                if s:
                    source = True
                if e:
                    entity = True

        return children, source, entity

    # Work through all the components of the rule to produce a final
    # set of data elements for building into correlations.
    def process_rule(self, rule: dict) -> list:
        events = list()
        buckets = dict()

        fetchChildren, fetchSources, fetchEntities = self.analyze_rule_scope(rule)

        # Go through collections and collect the data from the DB
        collectIndex = 0
        for c in rule.get('collections'):
            events.extend(self.collect_events(c['collect'],
                          fetchChildren,
                          fetchSources,
                          fetchEntities,
                          collectIndex))
            collectIndex += 1

        if not events:
            self.debug("no events found after going through collections")
            return None

        self.debug(f"{len(events)} proceeding to next stage: aggregation.")
        self.debug(f"{events} ready to be processed.")

        # Perform aggregations. Aggregating breaks up the events
        # into buckets with the key being the field to aggregate by.
        if 'aggregation' in rule:
            buckets = self.aggregate_events(rule['aggregation'], events)
            if not buckets:
                self.debug("no buckets found after aggregation")
                return None
        else:
            buckets = {'default': events}

        # Perform analysis across the buckets
        if 'analysis' in rule:
            for method in rule['analysis']:
                # analyze() will operate on the bucket, make changes
                # and empty it if the analysis doesn't yield results.
                self.analyze_events(method, buckets)

        return buckets

    # Build the correlation title with field substitution
    def build_correlation_title(self, rule: dict, data: list) -> str:
        title = rule['headline']
        if type(title) == dict:
            title = title['text']
        fields = re.findall(r"{([a-z\.]+)}", title)
        for m in fields:
            try:
                v = self.event_extract(data[0], m)[0]
            except Exception:
                self.error(f"Field requested was not available: {m}")
                pass
            title = title.replace("{" + m + "}", v.replace("\r", "").split("\n")[0])
        return title

    # Put the correlation into the backend.
    def create_correlation(self, rule: dict, data: list, readonly=False) -> bool:
        title = self.build_correlation_title(rule, data)
        self.status(f"New correlation [{rule['id']}]: {title}")
        if readonly:
            return True

        eventIds = list()
        for e in data:
            eventIds.append(e['id'])

        corrId = self.dbh.correlationResultCreate(self.scanId,
                                                  rule['id'],
                                                  rule['meta']['name'],
                                                  rule['meta']['description'],
                                                  rule['meta']['risk'],
                                                  rule['rawYaml'],
                                                  title,
                                                  eventIds)
        if not corrId:
            self.error(f"Unable to create correlation in DB for {rule['id']}")
            return False

        return True

    # Syntax-check rules
    def check_ruleset_validity(self, rules: list) -> bool:
        ok = True
        for rule in rules:
            fields = set(rule.keys())
            for f in self.mandatory_components:
                if f not in fields:
                    self.error(f"Mandatory rule component, {f}, not found in {rule['id']}.")
                    ok = False

            validfields = set(self.components.keys())
            if len(fields.union(validfields)) > len(validfields):
                self.error(f"Unexpected field(s) in correlation rule {rule['id']}: {[f for f in fields if f not in validfields]}")
                ok = False

            for collection in rule.get('collections', list()):
                # Match by data element type(s) or type regexps
                for matchrule in collection['collect']:
                    if matchrule['method'] not in ["exact", "regex"]:
                        self.error(f"Invalid collection method: {matchrule['method']}")
                        ok = False

                    if matchrule['field'] not in ["type", "module", "data",
                                                  "child.type", "child.module", "child.data",
                                                  "source.type", "source.module", "source.data",
                                                  "entity.type", "entity.module", "entity.data"]:
                        self.error(f"Invalid collection field: {matchrule['field']}")
                        ok = False

                    if 'value' not in matchrule:
                        self.error(f"Value missing for collection rule in {rule['id']}")
                        ok = False

                if 'analysis' in rule:
                    valid_methods = ["threshold", "outlier", "first_collection_only",
                                     "both_collections", "match_all_to_first_collection"]
                    for method in rule['analysis']:
                        if method['method'] not in valid_methods:
                            self.error(f"Unknown analysis method '{method['method']}' defined for {rule['id']}.")
                            ok = False

            for field in fields:
                # Check strict options are defined
                strictoptions = self.components[field].get('strict', list())
                otheroptions = self.components[field].get('optional', list())
                alloptions = set(strictoptions).union(otheroptions)

                for opt in strictoptions:
                    if type(rule[field]) == list:
                        item = 0
                        for optelement in rule[field]:
                            if not optelement.get(opt):
                                self.error(f"Required field for {field} missing in {rule['id']}, item {item}: {opt}")
                                ok = False
                            item += 1
                        continue

                    if not rule[field].get(opt):
                        self.error(f"Required field for {field} missing in {rule['id']}: {opt}")
                        ok = False

                    # Check if any of the options aren't valid
                    if opt not in alloptions:
                        self.error(f"Unexpected option, {opt}, found in {field} for {rule['id']}. Must be one of {alloptions}.")
                        ok = False
        if ok:
            return True
        return False
