cmake_minimum_required(VERSION 3.8)
project(dlldiag-helpers)

# Set the C++ standard to C++11
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Build our helper executables
add_executable(dlldiag-helper-loadlibrary dlldiag-helper-loadlibrary.cpp)
