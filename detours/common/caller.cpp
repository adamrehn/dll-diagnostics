#include "caller.h"
#include "strings.h"
#include <Windows.h>
using std::string;

// The code related to identifying the calling module is adapted from information found in this forum thread:
// <https://social.msdn.microsoft.com/Forums/vstudio/en-US/ea3120ce-bffc-4a14-87ba-067ba028eb1d/how-to-find-out-the-callers-info-using-win32-api?forum=vcgeneral>

// Attempts to retrieve the path to the module containing the caller function identified by the specified memory address
string GetCallerModule(void* callerAddress)
{
	// Attempt to retrieve a handle to the module that contains the caller's memory address
	HMODULE callerModule = nullptr;
	if (GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT, (LPCWSTR)callerAddress, &callerModule)) {
		return GetModuleName(callerModule);
	}
	
	return string("");
}
