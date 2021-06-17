#pragma once
#include <string>

// Use the _ReturnAddress intrinsic to identify the calling function from a callee
extern "C" void* _ReturnAddress(void);
#pragma intrinsic(_ReturnAddress)

// Attempts to retrieve the path to the module containing the caller function identified by the specified memory address
std::string GetCallerModule(void* callerAddress);
