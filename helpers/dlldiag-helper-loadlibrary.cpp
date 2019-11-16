#include <windows.h>
#include <iostream>
using std::cout;
using std::endl;

int wmain(int argc, wchar_t *argv[])
{
	if (argc > 1)
	{
		//Prevent Windows from attempting to display any error dialogs
		SetErrorMode(SEM_FAILCRITICALERRORS);
		
		//Attempt to load the specified module
		cout << "[LOADLIBRARY][START]" << endl;
		HINSTANCE handle =  LoadLibraryW(argv[1]);
		cout << "[LOADLIBRARY][END]" << endl;
		
		//Determine if loading was successful
		if (handle != NULL) {
			FreeLibrary(handle); 
		}
		else {
			return GetLastError();
		}
	}
	else
	{
		cout << "Usage:" << endl;
		cout << "dlldiag-helper-loadlibrary.exe MODULE" << endl;
	}
	
	return 0;
}
