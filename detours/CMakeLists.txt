cmake_minimum_required(VERSION 3.15)
project(dlldiag-detours)

# Set the C++ standard to C++11
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Retrieve our dependency information from Conan
include("${CMAKE_BINARY_DIR}/conanbuildinfo.cmake")
conan_basic_setup(TARGETS)

# Our common source files
add_library(common OBJECT
	common/caller.cpp
	common/environment.cpp
	common/log.cpp
	common/strings.cpp
)
conan_target_link_libraries(common)
set_property(TARGET common PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded")

# Build our instrumentation DLLs
add_library(dlldiag-detour-loadlibrary SHARED dlldiag-detour-loadlibrary.cpp $<TARGET_OBJECTS:common>)
conan_target_link_libraries(dlldiag-detour-loadlibrary)
target_link_options(dlldiag-detour-loadlibrary PRIVATE "/export:DetourFinishHelperProcess,@1,NONAME")
set_property(TARGET dlldiag-detour-loadlibrary PROPERTY MSVC_RUNTIME_LIBRARY "MultiThreaded")
