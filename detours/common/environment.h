#pragma once
#include <stdint.h>
#include <string>
#include <Windows.h>

// Attempts to retrieve the value of the specified environment variable
std::string GetEnvVar(const std::string& key);

// Retrieves the current system time in UTC format
uint64_t GetTimestamp();
