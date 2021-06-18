#include "environment.h"
using std::string;

string GetEnvVar(const string& key)
{
	// Allocate a buffer to hold the result
	const DWORD bufsize = 2048;
	CHAR buffer[bufsize];
	
	// Attempt to retrieve the value of the specified environment variable
	DWORD length = GetEnvironmentVariableA(key.c_str(), buffer, bufsize);
	if (length > 0) {
		return string(buffer, length);
	}
	
	return string("");
}

uint64_t GetTimestamp()
{
	// Retrieve the current system time
	FILETIME time;
	GetSystemTimeAsFileTime(&time);
	
	// Convert the time structure to an integer timestamp
	ULARGE_INTEGER timestamp;
	timestamp.LowPart = time.dwLowDateTime;
	timestamp.HighPart = time.dwHighDateTime;
	return timestamp.QuadPart;
}
