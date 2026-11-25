@echo off
rem SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
rem Builds the EntryNav2 package on Windows with Docker Desktop: dist\gauge-app-entrynav2.tar, ready for the car
rem (install: docs\EntryEvo_Installation.md). The compiler is the image of toolchain\Dockerfile (Ubuntu 12.04, armhf
rem GCC 4.6, eglibc 2.15 - the car's C library); it is built the first time.
rem
rem   build_entryNav2.bat           build the package
rem   build_entryNav2.bat test      run the host tests in WSL first (make check), then build
rem
rem Needs Docker Desktop (started here when it is not running) and the car's libAppFramework.A.so and
rem libCoreFramework.A.so (/opt/hmi/lib) in lib\Entry_Evo_libs. The pictures, the XML and the frame packs are already
rem in the project (python3 make_db.py regenerates them).
setlocal
cd /d "%~dp0"
set IMAGE=gauge-entrynav2-tc

if not exist lib\Entry_Evo_libs\libAppFramework.A.so goto nolibs
if not exist lib\Entry_Evo_libs\libCoreFramework.A.so goto nolibs

if /i not "%~1"=="test" goto notest
echo [TEST] make check in WSL
wsl --cd "%CD%" -e make check
if errorlevel 1 (
    echo [FAILED] host tests failed - nothing built
    exit /b 1
)
:notest

where docker >nul 2>nul
if errorlevel 1 (
    echo docker not found - install Docker Desktop
    exit /b 1
)
docker info >nul 2>nul
if not errorlevel 1 goto dockerready
echo [DOCKER] starting Docker Desktop
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
set /a TRIES=0
:waitdocker
timeout /t 5 /nobreak >nul
docker info >nul 2>nul
if not errorlevel 1 goto dockerready
set /a TRIES+=1
if %TRIES% lss 36 goto waitdocker
echo [FAILED] Docker did not start within 3 minutes - start Docker Desktop and run this again
exit /b 1

:dockerready
docker image inspect %IMAGE% >nul 2>nul
if not errorlevel 1 goto imageready
echo [DOCKER] building the toolchain image %IMAGE% (once, a few minutes)
docker build -t %IMAGE% toolchain
if errorlevel 1 (
    echo [FAILED] docker build
    exit /b 1
)

:imageready
echo [BUILD] libGaugeApp.so for EntryNav2 and dist\gauge-app-entrynav2.tar
docker run --rm -v "%CD%:/work" -w /work %IMAGE% make entrynav2-dist
if errorlevel 1 (
    echo [FAILED] make entrynav2-dist reported an error - see the messages above
    exit /b 1
)

echo.
echo C library versions the library needs (the car has 2.15; only GLIBC_2.4 expected):
docker run --rm -v "%CD%:/work" -w /work %IMAGE% sh -c "arm-linux-gnueabihf-objdump -T build/entrynav2/libGaugeApp.so | grep -o 'GLIBC_[0-9.]*' | sort -u"
echo.
for %%f in (dist\gauge-app-entrynav2.tar) do echo [DONE] %%~ff (%%~zf bytes)
echo Copy it to the car: scp dist\gauge-app-entrynav2.tar root@169.254.1.0:/tmp/   (then docs\EntryEvo_Installation.md)
exit /b 0

:nolibs
echo put libAppFramework.A.so and libCoreFramework.A.so from the car (/opt/hmi/lib) into lib\Entry_Evo_libs
exit /b 1
