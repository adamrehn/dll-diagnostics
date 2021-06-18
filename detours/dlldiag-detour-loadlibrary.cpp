#include "common/caller.h"
#include "common/environment.h"
#include "common/log.h"
#include "common/strings.h"
#include <Windows.h>
#include <detours.h>
#include <memory>
#include <string>
using std::string;

namespace
{
	// Our global logger object
	// (which is still local to each process that loads the DLL, see: <https://docs.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-data>)
	static std::unique_ptr<ThreadSafeLog> outputLog;
}

// The real versions of the Windows API functions that we interpose
extern "C"
{
	HMODULE (WINAPI *Real_LoadLibraryA)(LPCSTR lpLibFileName) = LoadLibraryA;
	HMODULE (WINAPI *Real_LoadLibraryW)(LPCWSTR lpLibFileName) = LoadLibraryW;
	HMODULE (WINAPI *Real_LoadLibraryExA)(LPCSTR lpLibFileName, HANDLE hFile, DWORD dwFlags) = LoadLibraryExA;
	HMODULE (WINAPI *Real_LoadLibraryExW)(LPCWSTR lpLibFileName, HANDLE hFile, DWORD dwFlags) = LoadLibraryExW;
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

#define LOG_FUNCTION_RESULT() if (outputLog) \
{ \
	log["type"] = "return"; \
	log["timestamp_end"] = GetTimestamp(); \
	log["result"] = GetModuleName(result); \
	log["error"] = { \
		{"code",    error}, \
		{"message", FormatError(error)} \
	}; \
	outputLog->WriteJson(log); \
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
	LOG_FUNCTION_RESULT();
	
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
	LOG_FUNCTION_RESULT();
	
	return result;
}

// The interposed version of LoadLibraryExA
HMODULE WINAPI Interposed_LoadLibraryExA(LPCSTR lpLibFileName, HANDLE hFile, DWORD dwFlags)
{
	// Identify the calling module and construct a JSON object for logging
	json log = {
		COMMON_LOG_FIELDS,
		{"function",  "LoadLibraryExA"},
		{"arguments", { string(lpLibFileName), (uintptr_t)(hFile), dwFlags }}
	};
	
	// Log the start of the call
	LOG_FUNCTION_ENTRY();
	
	// Invoke the real LoadLibraryExA
	HMODULE result = Real_LoadLibraryExA(lpLibFileName, hFile, dwFlags);
	DWORD error = GetLastError();
	
	// Log the result of the call
	LOG_FUNCTION_RESULT();
	
	return result;
}

// The interposed version of LoadLibraryExW
HMODULE WINAPI Interposed_LoadLibraryExW(LPCWSTR lpLibFileName, HANDLE hFile, DWORD dwFlags)
{
	// Identify the calling module and construct a JSON object for logging
	json log = {
		COMMON_LOG_FIELDS,
		{"function",  "LoadLibraryExW"},
		{"arguments", { UnicodeToUTF8(lpLibFileName), (uintptr_t)(hFile), dwFlags }}
	};
	
	// Log the start of the call
	LOG_FUNCTION_ENTRY();
	
	// Invoke the real LoadLibraryExW
	HMODULE result = Real_LoadLibraryExW(lpLibFileName, hFile, dwFlags);
	DWORD error = GetLastError();
	
	// Log the result of the call
	LOG_FUNCTION_RESULT();
	
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
		DetourTransactionBegin();
		DetourUpdateThread(GetCurrentThread());
		ATTACH(LoadLibraryA);
		ATTACH(LoadLibraryW);
		ATTACH(LoadLibraryExA);
		ATTACH(LoadLibraryExW);
		DetourTransactionCommit();
		
		// Attempt to retrieve the path to our log file from the environment
		string logFile = GetEnvVar("DLLDIAG_DETOUR_LOADLIBRARY_LOGFILE");
		if (logFile.length() > 0)
		{
			// Attempt to open our log file
			outputLog.reset(new ThreadSafeLog(logFile));
		}
	}
	else if (dwReason == DLL_PROCESS_DETACH)
	{
		DetourTransactionBegin();
		DetourUpdateThread(GetCurrentThread());
		DETACH(LoadLibraryA);
		DETACH(LoadLibraryW);
		DETACH(LoadLibraryExA);
		DETACH(LoadLibraryExW);
		DetourTransactionCommit();
		
		// Close our log file
		outputLog.reset(nullptr);
	}
	
	return TRUE;
}
