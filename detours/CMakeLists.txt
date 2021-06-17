cmake_minimum_required(VERSION 3.8)
project(dlldiag-detours)

# Set the C++ standard to C++11
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Retrieve our dependency information from Conan
include("${CMAKE_BINARY_DIR}/conanbuildinfo.cmake")
conan_basic_setup(TARGETS)

# Our common source files
set(COMMON_FILES common/caller.cpp)

# Build our instrumentation DLLs
add_library(dlldiag-detour-loadlibrary SHARED dlldiag-detour-loadlibrary.cpp ${COMMON_FILES})
conan_target_link_libraries(dlldiag-detour-loadlibrary)
