# DLL Diagnostic Tools

The `dlldiag` command-line tool provides functionality to assist in identifying the DLL dependencies of an application or library and diagnosing dependency loading issues. It is primarily intended for use when migrating existing applications to Windows containers, where traditional GUI-based tools are unavailable. Identifying the minimal set of dependencies for an application facilitates a workflow where the required DLL files can be copied from the [mcr.microsoft.com/windows](https://hub.docker.com/_/microsoft-windows) base image into the [mcr.microsoft.com/windows/servercore](https://hub.docker.com/_/microsoft-windows-servercore) base image, thus maximising application compatibility whilst maintaining the minimum possible image size.


## Contents

- [Requirements and installation](#requirements-and-installation)
- [Usage](#usage)
- [Legal](#Legal)


## Requirements and installation

The `dll-diagnostics` Python package requires the following:

- Python 3.6 or newer
- Windows Server 2016 or newer, or Windows 10 version 1607 or newer
- [Microsoft Visual C++ Redistributable for Visual Studio 2015-2019](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads)
- [Debugging Tools for Windows 10 (WinDbg)](https://docs.microsoft.com/en-us/windows-hardware/drivers/debugger/debugger-download-tools) (only needed for running the `dlldiag trace` command)

You can install the package by running the following command:

```
pip install dll-diagnostics
```

If you don't need the package on your host system then you can [download a prebuilt container image from Docker Hub](https://hub.docker.com/r/adamrehn/dll-diagnostics) to start using the `dlldiag` command inside a Windows container.


## Usage

The `dlldiag` command-line tool provides the following subcommands:

- `dlldiag deps`: this subcommand lists the direct dependencies for a module (DLL/EXE) and checks if each one can be loaded. [Delay-loaded dependencies](https://docs.microsoft.com/en-us/cpp/build/reference/linker-support-for-delay-loaded-dlls) are also listed, but indirect dependencies (i.e. dependencies of dependencies) are not.

- `dlldiag docker` this subcommand generates a Dockerfile suitable for using the `dlldiag` command inside a Windows container, allowing the user to optionally specify the base image to be used in the Dockerfile's `FROM` clause. This is handy when you want to extend an existing image of your choice, rather than simply extending the Windows Server Core image as the [prebuilt images from Docker Hub](https://hub.docker.com/r/adamrehn/dll-diagnostics) do.

- `dlldiag graph` this subcommand runs executable modules with an injected DLL that uses [Detours](https://github.com/microsoft/Detours) to instrument calls to [LoadLibrary()](https://docs.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-loadlibraryw) so the call hierarchy can be reconstructed. This is handy when you want to see which indirect dependencies are being loaded by an executable's direct dependencies or want to identify dependencies that are loaded programmatically at runtime.

- `dlldiag trace`: this subcommand uses the Windows debugger to trace a [LoadLibrary()](https://docs.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-loadlibraryw) call for a module (DLL/EXE) and provide detailed reports of the results. The trace makes use of the Windows kernel [loader snaps](https://docs.microsoft.com/en-us/windows-hardware/drivers/debugger/show-loader-snaps) feature to obtain fine-grained information, as discussed in [Junfeng Zhang's blog post "Debugging LoadLibrary Failures"](https://blogs.msdn.microsoft.com/junfeng/2006/11/20/debugging-loadlibrary-failures/). The trace captures information about both indirect dependencies and delay-loaded dependencies.


## Legal

Copyright &copy; 2019-2023, Adam Rehn. Licensed under the MIT License, see the file [LICENSE](https://github.com/adamrehn/dll-diagnostics/blob/master/LICENSE) for details.

Binary distributions of this package include parts of [Detours](https://github.com/microsoft/Detours) in object form. Detours is Copyright (c) Microsoft Corporation and is [licensed under the MIT license](https://github.com/microsoft/Detours/blob/master/LICENSE.md).
