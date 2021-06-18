#include "strings.h"
using std::string;
using std::wstring;

std::string GetModuleName(HMODULE module)
{
	// Don't attempt to process the module if a null pointer was supplied
	if (module == nullptr) {
		return string("NULL");
	}
	
	// Create a buffer to hold the path
	const DWORD bufsize = 2048;
	CHAR buffer[bufsize];
	
	// Attempt to retrieve the module path
	DWORD length = GetModuleFileNameA(module, buffer, bufsize);
	if (length > 0) {
		return string(buffer, length);
	}
	
	return string("");
}

string FormatError(DWORD error)
{
	// Attempt to allocate a new buffer and fill it with the error message
	LPSTR buffer = nullptr;
	DWORD bufsize = FormatMessageA(
		FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
		nullptr,
		error,
		MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
		(LPSTR)&buffer,
		0,
		nullptr
	);
	
	// Copy the formatted message into a new string
	string result = string(buffer, bufsize);
	
	// Free the allocated buffer
	LocalFree(buffer);
	
	return result;
}

string UnicodeToUTF8(LPCWSTR unicodeStr)
{
	// Determine the required buffer size to store the converted string
	int bufsize = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, unicodeStr, -1, nullptr, 0, nullptr, nullptr);
	if (bufsize > 0)
	{
		// Allocate the buffer and attempt to perform the conversion
		string buffer = string(bufsize, 0);
		if (WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, unicodeStr, -1, (LPSTR)(buffer.data()), bufsize, nullptr, nullptr) != 0)
		{
			// Remove the trailing null terminating character from the result
			buffer.pop_back();
			return buffer;
		}
	}
	
	return string("");
}
