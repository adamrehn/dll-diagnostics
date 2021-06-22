#pragma once
#include <string>
#include <Windows.h>

// Retrieves the absolute path to the specified module
std::string GetModuleName(HMODULE module);

// Formats an error code as a human-readable string
std::string FormatError(DWORD error);

// Converts a UTF-16 encoded Unicode string into a UTF-8 encoded string
std::string UnicodeToUTF8(LPCWSTR unicodeStr, int length = -1);
