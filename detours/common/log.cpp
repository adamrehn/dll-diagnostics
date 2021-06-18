#include "log.h"
using std::string;

ThreadSafeLog::ThreadSafeLog(const string& logFile) {
	this->outfile.open(logFile.c_str(), std::ios::binary);
}

ThreadSafeLog::~ThreadSafeLog()
{
	// Close the log file if it is open
	if (this->IsOpen()) {
		this->outfile.close();
	}
}

bool ThreadSafeLog::IsOpen() const {
	return this->outfile.is_open();
}

bool ThreadSafeLog::Write(const std::string& message)
{
	// Lock the mutex
	std::lock_guard<std::mutex> lock(this->mutex);
	
	// Attempt to perform the write
	this->outfile.write(message.c_str(), message.length());
	this->outfile.flush();
	return this->outfile.good();
}

bool ThreadSafeLog::WriteJson(const json& object) {
	return this->Write(object.dump() + "\n");
}
