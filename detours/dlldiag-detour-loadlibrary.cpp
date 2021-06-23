#include "common/caller.h"
#include "common/environment.h"
#include "common/log.h"
#include "common/strings.h"

#include <Windows.h>
#include <WinNT.h>
#include <subauth.h>

#include <detours.h>

#include <stdlib.h>
#include <time.h>
#include <algorithm>
#include <memory>
#include <string>
#include <vector>
using std::string;
using std::vector;

namespace
{
	// Our global logger object
	// (which is still local to each process that loads the DLL, see: <https://docs.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-data>)
	static std::unique_ptr<ThreadSafeLog> outputLog;
}

// The real versions of the Windows API functions that we interpose
extern "C"
{
	// LoadLibrary family
	HMODULE (WINAPI *Real_LoadLibraryA)(LPCSTR lpLibFileName) = LoadLibraryA;
	HMODULE (WINAPI *Real_LoadLibraryW)(LPCWSTR lpLibFileName) = LoadLibraryW;
	HMODULE (WINAPI *Real_LoadLibraryExA)(LPCSTR lpLibFileName, HANDLE hFile, DWORD dwFlags) = LoadLibraryExA;
	HMODULE (WINAPI *Real_LoadLibraryExW)(LPCWSTR lpLibFileName, HANDLE hFile, DWORD dwFlags) = LoadLibraryExW;
	
	// Functions that influence DLL search directories
	BOOL (WINAPI *Real_SetDefaultDllDirectories)(DWORD DirectoryFlags) = SetDefaultDllDirectories;
	BOOL (WINAPI *Real_SetDllDirectoryA)(LPCSTR lpPathName) = SetDllDirectoryA;
	BOOL (WINAPI *Real_SetDllDirectoryW)(LPCWSTR lpPathName) = SetDllDirectoryW;
	DLL_DIRECTORY_COOKIE (WINAPI *Real_AddDllDirectory)(PCWSTR NewDirectory) = AddDllDirectory;
	BOOL (WINAPI *Real_RemoveDllDirectory)(DLL_DIRECTORY_COOKIE Cookie) = RemoveDllDirectory;
	
	// We instrument GetProcAddress() as well since AddDllDirectory and RemoveDllDirectory are typically
	// retrieved programmatically by code that maintains compatibility with older versions of Windows
	FARPROC (WINAPI *Real_GetProcAddress)(HMODULE hModule, LPCSTR lpProcName) = GetProcAddress;
}

// Function pointer type and function pointer for the undocumented LdrLoadDll() function
typedef NTSTATUS (NTAPI *Ptr_LdrLoadDll)(PWSTR SearchPath, PULONG DllCharacteristics, PUNICODE_STRING DllName, PVOID* BaseAddress);
static Ptr_LdrLoadDll Real_LdrLoadDll = nullptr;
HMODULE ntdll = nullptr;

// Helper macro for wrapping code in a __try/__except block for catching structured exceptions
#define SEH_GUARD(code) [&]() { __try { ##code } __except(EXCEPTION_EXECUTE_HANDLER) {} }();

// Helper macros to reduce logging boilerplate
#define COMMON_LOG_FIELDS \
	{"random",          rand()}, \
	{"timestamp_start", GetTimestamp()}, \
	{"module",          GetCallerModule(_ReturnAddress())}, \
	{"thread",          GetCurrentThreadId()}

#define LOG_FUNCTION_ENTRY_IMP(writeCall) if (outputLog) \
{ \
	log["type"] = "enter"; \
	outputLog->##writeCall(log); \
}

#define LOG_FUNCTION_RESULT_IMP(transform, writeCall) if (outputLog) \
{ \
	log["type"] = "return"; \
	log["timestamp_end"] = GetTimestamp(); \
	log["result"] = ##transform(result); \
	log["error"] = { \
		{"code",    error}, \
		{"message", FormatError(error)} \
	}; \
	outputLog->##writeCall(log); \
}

#define LOG_FUNCTION_ENTRY() LOG_FUNCTION_ENTRY_IMP(WriteJson)
#define LOG_FUNCTION_RESULT(transform) LOG_FUNCTION_RESULT_IMP(transform, WriteJson)
#define LOG_FUNCTION_ENTRY_DEFERRED() LOG_FUNCTION_ENTRY_IMP(WriteJsonDeferred)
#define LOG_FUNCTION_RESULT_DEFERRED(transform) LOG_FUNCTION_RESULT_IMP(transform, WriteJsonDeferred)

// Helper macro for the flag parsing functions below
#define IDENTIFY_FLAG(flag) if (dwFlags & flag) { flags.push_back(#flag); }

// Parses the flags for a LoadLibraryEx call and returns the list of flags as strings
vector<string> LoadLibraryExFlags(DWORD dwFlags)
{
	vector<string> flags;
	IDENTIFY_FLAG(DONT_RESOLVE_DLL_REFERENCES)
	IDENTIFY_FLAG(LOAD_IGNORE_CODE_AUTHZ_LEVEL)
	IDENTIFY_FLAG(LOAD_LIBRARY_AS_DATAFILE)
	IDENTIFY_FLAG(LOAD_LIBRARY_AS_DATAFILE_EXCLUSIVE)
	IDENTIFY_FLAG(LOAD_LIBRARY_AS_IMAGE_RESOURCE)
	IDENTIFY_FLAG(LOAD_LIBRARY_SEARCH_APPLICATION_DIR)
	IDENTIFY_FLAG(LOAD_LIBRARY_SEARCH_DEFAULT_DIRS)
	IDENTIFY_FLAG(LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR)
	IDENTIFY_FLAG(LOAD_LIBRARY_SEARCH_SYSTEM32)
	IDENTIFY_FLAG(LOAD_LIBRARY_SEARCH_USER_DIRS)
	IDENTIFY_FLAG(LOAD_WITH_ALTERED_SEARCH_PATH)
	IDENTIFY_FLAG(LOAD_LIBRARY_REQUIRE_SIGNED_TARGET)
	IDENTIFY_FLAG(LOAD_LIBRARY_SAFE_CURRENT_DIRS)
	return flags;
}

// Parses the flags for a SetDefaultDllDirectories call and returns the list of flags as strings
vector<string> SetDefaultDllDirectoriesFlags(DWORD dwFlags)
{
	vector<string> flags;
	IDENTIFY_FLAG(LOAD_LIBRARY_SEARCH_APPLICATION_DIR)
	IDENTIFY_FLAG(LOAD_LIBRARY_SEARCH_DEFAULT_DIRS)
	IDENTIFY_FLAG(LOAD_LIBRARY_SEARCH_SYSTEM32)
	IDENTIFY_FLAG(LOAD_LIBRARY_SEARCH_USER_DIRS)
	return flags;
}

// The interposed version of LoadLibraryA
HMODULE WINAPI Interposed_LoadLibraryA(LPCSTR lpLibFileName)
{
	// Identify the calling module and construct a JSON object for logging
	json log = {
		COMMON_LOG_FIELDS,
		{"function",  "LoadLibraryA"},
		{"arguments", { string(lpLibFileName) }}
	};
	
	// Log the start of the call
	LOG_FUNCTION_ENTRY();
	
	// Invoke the real LoadLibraryA
	HMODULE result = nullptr;
	SetLastError(0);
	SEH_GUARD(
		result = Real_LoadLibraryA(lpLibFileName);
	)
	DWORD error = GetLastError();
	
	// Log the result of the call
	LOG_FUNCTION_RESULT(GetModuleName);
	
	return result;
}

// The interposed version of LoadLibraryW
HMODULE WINAPI Interposed_LoadLibraryW(LPCWSTR lpLibFileName)
{
	// Identify the calling module and construct a JSON object for logging
	json log = {
		COMMON_LOG_FIELDS,
		{"function",  "LoadLibraryW"},
		{"arguments", { UnicodeToUTF8(lpLibFileName) }}
	};
	
	// Log the start of the call
	LOG_FUNCTION_ENTRY();
	
	// Invoke the real LoadLibraryW
	HMODULE result = nullptr;
	SetLastError(0);
	SEH_GUARD(
		result = Real_LoadLibraryW(lpLibFileName);
	)
	DWORD error = GetLastError();
	
	// Log the result of the call
	LOG_FUNCTION_RESULT(GetModuleName);
	
	return result;
}

// The interposed version of LoadLibraryExA
HMODULE WINAPI Interposed_LoadLibraryExA(LPCSTR lpLibFileName, HANDLE hFile, DWORD dwFlags)
{
	// Identify the calling module and construct a JSON object for logging
	json log = {
		COMMON_LOG_FIELDS,
		{"function",  "LoadLibraryExA"},
		{"arguments", { string(lpLibFileName), (uintptr_t)(hFile), LoadLibraryExFlags(dwFlags) }}
	};
	
	// Log the start of the call
	LOG_FUNCTION_ENTRY();
	
	// Invoke the real LoadLibraryExA
	HMODULE result = nullptr;
	SetLastError(0);
	SEH_GUARD(
		result = Real_LoadLibraryExA(lpLibFileName, hFile, dwFlags);
	)
	DWORD error = GetLastError();
	
	// Log the result of the call
	LOG_FUNCTION_RESULT(GetModuleName);
	
	return result;
}

// The interposed version of LoadLibraryExW
HMODULE WINAPI Interposed_LoadLibraryExW(LPCWSTR lpLibFileName, HANDLE hFile, DWORD dwFlags)
{
	// Identify the calling module and construct a JSON object for logging
	json log = {
		COMMON_LOG_FIELDS,
		{"function",  "LoadLibraryExW"},
		{"arguments", { UnicodeToUTF8(lpLibFileName), (uintptr_t)(hFile), LoadLibraryExFlags(dwFlags) }}
	};
	
	// Log the start of the call
	LOG_FUNCTION_ENTRY();
	
	// Invoke the real LoadLibraryExW
	HMODULE result = nullptr;
	SetLastError(0);
	SEH_GUARD(
		result = Real_LoadLibraryExW(lpLibFileName, hFile, dwFlags);
	)
	DWORD error = GetLastError();
	
	// Log the result of the call
	LOG_FUNCTION_RESULT(GetModuleName);
	
	return result;
}

// The interposed version of SetDefaultDllDirectories
BOOL WINAPI Interposed_SetDefaultDllDirectories(DWORD DirectoryFlags)
{
	// Identify the calling module and construct a JSON object for logging
	json log = {
		COMMON_LOG_FIELDS,
		{"function",  "SetDefaultDllDirectories"},
		{"arguments", { SetDefaultDllDirectoriesFlags(DirectoryFlags) }}
	};
	
	// Log the start of the call
	LOG_FUNCTION_ENTRY();
	
	// Invoke the real SetDefaultDllDirectories
	BOOL result = FALSE;
	SetLastError(0);
	SEH_GUARD(
		result = Real_SetDefaultDllDirectories(DirectoryFlags);
	)
	DWORD error = GetLastError();
	
	// Log the result of the call
	LOG_FUNCTION_RESULT(bool);
	
	return result;
}

// The interposed version of SetDllDirectoryA
BOOL WINAPI Interposed_SetDllDirectoryA(LPCSTR lpPathName)
{
	// Identify the calling module and construct a JSON object for logging
	json log = {
		COMMON_LOG_FIELDS,
		{"function",  "SetDllDirectoryA"},
		{"arguments", { string(lpPathName) }}
	};
	
	// Log the start of the call
	LOG_FUNCTION_ENTRY();
	
	// Invoke the real SetDllDirectoryA
	BOOL result = FALSE;
	SetLastError(0);
	SEH_GUARD(
		result = Real_SetDllDirectoryA(lpPathName);
	)
	DWORD error = GetLastError();
	
	// Log the result of the call
	LOG_FUNCTION_RESULT(bool);
	
	return result;
}

// The interposed version of SetDllDirectoryW
BOOL WINAPI Interposed_SetDllDirectoryW(LPCWSTR lpPathName)
{
	// Identify the calling module and construct a JSON object for logging
	json log = {
		COMMON_LOG_FIELDS,
		{"function",  "SetDllDirectoryW"},
		{"arguments", { UnicodeToUTF8(lpPathName) }}
	};
	
	// Log the start of the call
	LOG_FUNCTION_ENTRY();
	
	// Invoke the real SetDllDirectoryW
	BOOL result = FALSE;
	SetLastError(0);
	SEH_GUARD(
		result = Real_SetDllDirectoryW(lpPathName);
	)
	DWORD error = GetLastError();
	
	// Log the result of the call
	LOG_FUNCTION_RESULT(bool);
	
	return result;
}

// The interposed version of AddDllDirectory
DLL_DIRECTORY_COOKIE WINAPI Interposed_AddDllDirectory(PCWSTR NewDirectory)
{
	// Identify the calling module and construct a JSON object for logging
	json log = {
		COMMON_LOG_FIELDS,
		{"function",  "AddDllDirectory"},
		{"arguments", { UnicodeToUTF8(NewDirectory) }}
	};
	
	// Log the start of the call
	LOG_FUNCTION_ENTRY();
	
	// Invoke the real AddDllDirectory
	DLL_DIRECTORY_COOKIE result = nullptr;
	SetLastError(0);
	SEH_GUARD(
		result = Real_AddDllDirectory(NewDirectory);
	)
	DWORD error = GetLastError();
	
	// Log the result of the call
	LOG_FUNCTION_RESULT(uint64_t);
	
	return result;
}

// The interposed version of RemoveDllDirectory
BOOL WINAPI Interposed_RemoveDllDirectory(DLL_DIRECTORY_COOKIE Cookie)
{
	// Identify the calling module and construct a JSON object for logging
	json log = {
		COMMON_LOG_FIELDS,
		{"function",  "RemoveDllDirectory"},
		{"arguments", { uint64_t(Cookie) }}
	};
	
	// Log the start of the call
	LOG_FUNCTION_ENTRY();
	
	// Invoke the real RemoveDllDirectory
	BOOL result = FALSE;
	SetLastError(0);
	SEH_GUARD(
		result = Real_RemoveDllDirectory(Cookie);
	)
	DWORD error = GetLastError();
	
	// Log the result of the call
	LOG_FUNCTION_RESULT(bool);
	
	return result;
}

// The interposed version of GetProcAddress
FARPROC WINAPI Interposed_GetProcAddress(HMODULE hModule, LPCSTR lpProcName)
{
	// Determine whether the specified symbol name is a string or an ordinal value
	// (HIWORD() logic adapted from: <https://stackoverflow.com/a/16884408>)
	if (HIWORD(lpProcName))
	{
		// If any of our instrumented functions are being requested then redirect to the instrumented version
		string symbol = string(lpProcName);
		#define REDIRECT(f) if (symbol == #f) { return (FARPROC)(&Interposed_##f);}
		REDIRECT(LoadLibraryA);
		REDIRECT(LoadLibraryW);
		REDIRECT(LoadLibraryExA);
		REDIRECT(LoadLibraryExW);
		REDIRECT(SetDefaultDllDirectories);
		REDIRECT(SetDllDirectoryA);
		REDIRECT(SetDllDirectoryW);
		REDIRECT(AddDllDirectory);
		REDIRECT(RemoveDllDirectory);
		#undef REDIRECT
	}
	
	// Invoke the real GetProcAddress
	return Real_GetProcAddress(hModule, lpProcName);
}

// The interposed version of LdrLoadDll
NTSTATUS NTAPI Interposed_LdrLoadDll(PWSTR SearchPath, PULONG DllCharacteristics, PUNICODE_STRING DllName, PVOID* BaseAddress)
{
	// Invoke the real LdrLoadDll
	NTSTATUS result = 0;
	SetLastError(0);
	SEH_GUARD(
		result = Real_LdrLoadDll(SearchPath, DllCharacteristics, DllName, BaseAddress);
	)
	DWORD error = GetLastError();
	
	// Capture a stack strace
	const ULONG maxFrames = 63;
	void* frames[maxFrames];
	USHORT numFrames = CaptureStackBackTrace(1, maxFrames, frames, nullptr);
	
	// Retrieve the module for each frame in the stack trace
	vector<string> modules;
	for (USHORT index = 0; index < numFrames; ++index) {
		modules.push_back(GetCallerModule(frames[index]));
	}
	
	// If we have instrumented the parent function that called LdrLoadDll() then we don't need to log anything
	string module = GetCallerModule(&Interposed_LdrLoadDll);
	if (std::find(modules.begin(), modules.end(), module) != modules.end()) {
		return result;
	}
	
	// Construct a JSON object for logging
	json log = {
		COMMON_LOG_FIELDS,
		{"function",  "LdrLoadDll"},
		{"arguments", { UnicodeToUTF8(DllName->Buffer) }},
		{"resolved",  GetCallerModule(BaseAddress)},
		{"stack",     modules}
	};
	
	// Log the start of the call and the result of the call
	LOG_FUNCTION_ENTRY_DEFERRED();
	LOG_FUNCTION_RESULT_DEFERRED(uint64_t);
	
	return result;
}

// Helper macros for attaching and detaching Windows API functions
#define ATTACH(f) DetourAttach(&(PVOID&)Real_##f,Interposed_##f)
#define DETACH(f) DetourDetach(&(PVOID&)Real_##f,Interposed_##f)

// Our DLL entrypoint
BOOL APIENTRY DllMain(HINSTANCE hModule, DWORD dwReason, PVOID lpReserved)
{
	if (DetourIsHelperProcess()) {
		return TRUE;
	}
	
	if (dwReason == DLL_PROCESS_ATTACH)
	{
		DetourRestoreAfterWith();
		
		// Attempt to load ntdll.dll
		if (ntdll == nullptr) {
			ntdll = Real_LoadLibraryExW(L"ntdll.dll", nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
		}
		
		// Attempt to retrieve the function pointer for the LdrLoadDll() function
		if (ntdll != nullptr && Real_LdrLoadDll == nullptr) {
			Real_LdrLoadDll = (Ptr_LdrLoadDll)(GetProcAddress(ntdll, "LdrLoadDll"));
		}
		
		// Seed the random number generator
		srand((unsigned int)(time(nullptr)));
		
		// Attempt to retrieve the path to our log file from the environment
		string logFile = GetEnvVar("DLLDIAG_DETOUR_LOADLIBRARY_LOGFILE");
		if (logFile.length() > 0)
		{
			// Attempt to open our log file
			outputLog.reset(new ThreadSafeLog(logFile));
		}
		
		DetourTransactionBegin();
		DetourUpdateThread(GetCurrentThread());
		ATTACH(LoadLibraryA);
		ATTACH(LoadLibraryW);
		ATTACH(LoadLibraryExA);
		ATTACH(LoadLibraryExW);
		ATTACH(SetDefaultDllDirectories);
		ATTACH(SetDllDirectoryA);
		ATTACH(SetDllDirectoryW);
		ATTACH(AddDllDirectory);
		ATTACH(RemoveDllDirectory);
		ATTACH(GetProcAddress);
		if (Real_LdrLoadDll != nullptr) {
			ATTACH(LdrLoadDll);
		}
		DetourTransactionCommit();
	}
	else if (dwReason == DLL_PROCESS_DETACH)
	{
		DetourTransactionBegin();
		DetourUpdateThread(GetCurrentThread());
		DETACH(LoadLibraryA);
		DETACH(LoadLibraryW);
		DETACH(LoadLibraryExA);
		DETACH(LoadLibraryExW);
		DETACH(SetDefaultDllDirectories);
		DETACH(SetDllDirectoryA);
		DETACH(SetDllDirectoryW);
		DETACH(AddDllDirectory);
		DETACH(RemoveDllDirectory);
		DETACH(GetProcAddress);
		if (Real_LdrLoadDll != nullptr) {
			DETACH(LdrLoadDll);
		}
		DetourTransactionCommit();
		
		// Close our log file, flushing any remaining buffered messages
		outputLog->Write("");
		outputLog.reset(nullptr);
		
		// Unload ntdll.dll
		if (ntdll != nullptr)
		{
			FreeLibrary(ntdll);
			ntdll = nullptr;
			
			// Reset the function pointer for the LdrLoadDll() function
			if (Real_LdrLoadDll != nullptr) {
				Real_LdrLoadDll = nullptr;
			}
		}
	}
	
	return TRUE;
}
