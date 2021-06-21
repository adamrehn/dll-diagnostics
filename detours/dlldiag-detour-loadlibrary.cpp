#include "common/caller.h"
#include "common/environment.h"
#include "common/log.h"
#include "common/strings.h"
#include <Windows.h>
#include <detours.h>
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

// Helper macros to reduce logging boilerplate
#define COMMON_LOG_FIELDS \
	{"timestamp_start", GetTimestamp()}, \
	{"module",          GetCallerModule(_ReturnAddress())}, \
	{"thread",          GetCurrentThreadId()}

#define LOG_FUNCTION_ENTRY() if (outputLog) \
{ \
	log["type"] = "enter"; \
	outputLog->WriteJson(log); \
}

#define LOG_FUNCTION_RESULT(transform) if (outputLog) \
{ \
	log["type"] = "return"; \
	log["timestamp_end"] = GetTimestamp(); \
	log["result"] = ##transform(result); \
	log["error"] = { \
		{"code",    error}, \
		{"message", FormatError(error)} \
	}; \
	outputLog->WriteJson(log); \
}

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
	HMODULE result = Real_LoadLibraryA(lpLibFileName);
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
	HMODULE result = Real_LoadLibraryW(lpLibFileName);
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
	HMODULE result = Real_LoadLibraryExA(lpLibFileName, hFile, dwFlags);
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
	HMODULE result = Real_LoadLibraryExW(lpLibFileName, hFile, dwFlags);
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
	BOOL result = Real_SetDefaultDllDirectories(DirectoryFlags);
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
	BOOL result = Real_SetDllDirectoryA(lpPathName);
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
	BOOL result = Real_SetDllDirectoryW(lpPathName);
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
	DLL_DIRECTORY_COOKIE result = Real_AddDllDirectory(NewDirectory);
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
	BOOL result = Real_RemoveDllDirectory(Cookie);
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
		string module = GetModuleName(hModule);
		if (module == "C:\\WINDOWS\\System32\\KERNEL32.DLL" || module == "C:\\WINDOWS\\System32\\KERNELBASE.dll")
		{
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
	}
	
	// Invoke the real GetProcAddress
	return Real_GetProcAddress(hModule, lpProcName);
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
		DetourTransactionCommit();
	}
	else if (dwReason == DLL_PROCESS_DETACH)
	{
		// Close our log file
		outputLog.reset(nullptr);
		
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
		DetourTransactionCommit();
	}
	
	return TRUE;
}
