#pragma once
#include <fstream>
#include <mutex>
#include <string>
#include <nlohmann/json.hpp>
using json = nlohmann::json;

// Provides thread-safe functionality for writing to a log file
class ThreadSafeLog
{
	public:
		
		// Attempts to open the specified log file
		ThreadSafeLog(const std::string& logFile);
		
		// Closes the log file
		~ThreadSafeLog();
		
		// Determines whether the log file is open
		bool IsOpen() const;
		
		// Writes a message to the log file
		bool Write(const std::string& message);
		
		// Writes a JSON message to the log file
		bool WriteJson(const json& object);
		
		// Enqueues a message to be written to the log file
		// when the next non-deferred write is performed
		void WriteDeferred(const std::string& message);
		
		// Enqueues a JSON message to be written to the log file
		// when the next non-deferred write is performed
		void WriteJsonDeferred(const json& object);
		
	private:
		
		// The output stream for the log file
		std::ofstream outfile;
		
		// The mutex that prevents concurrent writes to the log file
		std::mutex mutex;
		
		// The buffer of deferred writes
		std::string deferred;
};
