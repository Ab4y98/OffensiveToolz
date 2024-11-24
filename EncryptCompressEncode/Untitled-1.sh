
# Colors for formatting
GREEN='\e[32m'
RED='\e[31m'
BLUE='\e[34m'

echo "${GREEN}[+] Start Installing .\e[0m"

# Install Golang-Go
apt install golang-go -y > /dev/null 2>&1 && echo "${GREEN}[+] Installation of golang-go is complete .\e[0m"

#!/bin/sh

# Detect user's shell and set the config file and source command accordingly
if echo "$SHELL" | grep -q "bash"; then
    CONFIG_FILE="$HOME/.bashrc"
    SOURCE_CMD=". $CONFIG_FILE"  # Use sh-compatible source command
elif echo "$SHELL" | grep -q "zsh"; then
    CONFIG_FILE="$HOME/.zshrc"
    SOURCE_CMD="zsh -c '. $CONFIG_FILE'"  # Source the file using zsh
else
    echo "${RED}Unsupported shell. Please add the path manually.\e[0m"
    exit 1
fi

# Path to add
GO_PATH='export PATH=$PATH:$HOME/go/bin'

# Check if the path is already in the config file
if grep -q "$GO_PATH" "$CONFIG_FILE"; then
    echo "${RED}Go path is already added to $CONFIG_FILE\e[0m"
else
    # Add the path to the config file
    echo "$GO_PATH" >> "$CONFIG_FILE"
    echo "${GREEN}Go path added to $CONFIG_FILE\e[0m"
fi

# Apply the changes using the correct shell command
eval "$SOURCE_CMD"
echo "${BLUE}Changes applied. You can now use Go binaries from $HOME/go/bin.\e[0m"


# More Packages

apt install parallel -y > /dev/null 2>&1 && echo "${GREEN}[+] Installation of parallel is complete .\e[0m"
apt install subfinder -y > /dev/null 2>&1 && echo "${GREEN}[+] Installation of subfinder is complete .\e[0m"
go install github.com/lc/gau/v2/cmd/gau@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of gau is complete .\e[0m"
go install github.com/tomnomnom/gf@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of gf is complete .\e[0m"
go install github.com/tomnomnom/qsreplace@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of qsreplace is complete .\e[0m"
go install github.com/jaeles-project/gospider@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of gospider is complete .\e[0m"
go install github.com/hahwul/dalfox/v2@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of dalfox is complete .\e[0m"
go install github.com/003random/getJS/v2@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of getJS is complete .\e[0m"
go install github.com/tomnomnom/assetfinder@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of assetfinder is complete .\e[0m"
go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of naabu is complete .\e[0m"
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of subfinder is complete .\e[0m"
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of dnsx is complete .\e[0m"
go install github.com/projectdiscovery/katana/cmd/katana@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of katana is complete .\e[0m"
go install github.com/hakluke/hakrawler@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of hakrawler is complete .\e[0m"
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of nuclei is complete .\e[0m"
go install github.com/bp0lr/gauplus@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of gauplus is complete .\e[0m"
go install github.com/utkusen/socialhunter@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of socialhunter is complete .\e[0m"
go install github.com/tomnomnom/anew@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of anew is complete .\e[0m"
go install github.com/dwisiswant0/unew@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of unew is complete .\e[0m"
go install github.com/tomnomnom/httprobe@latest > /dev/null 2>&1 && echo "${GREEN}[+] Installation of httprobe is complete .\e[0m"

# Confirm installation
echo "${BLUE}[+] Installation of tools is complete .\e[0m"
