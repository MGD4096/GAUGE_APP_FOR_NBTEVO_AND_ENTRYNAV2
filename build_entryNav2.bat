@echo off
rem SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
rem Builds the EntryNav2 packages on Windows, one per screen resolution:
rem   dist\EntryNav2\800x480\GaugeApp.tar
rem   dist\EntryNav2\1280x480\GaugeApp.tar   (EntryNav2 F40: car-verified)
rem   dist\EntryNav2\1440x540\GaugeApp.tar
rem ready for the car (install: docs\EntryEvo_Installation.md; pick the folder of the unit's screen). The compiler is
rem the image of toolchain\Dockerfile (Ubuntu 12.04, armhf GCC 4.6, eglibc 2.15 - the car's C library); it is built
rem the first time.
rem
rem   build_entryNav2.bat           build the packages
rem   build_entryNav2.bat test      run the host tests in WSL first (make check), then build
rem
rem Needs Docker Desktop (started here when it is not running), the car's libAppFramework.A.so and
rem libCoreFramework.A.so (/opt/hmi/lib) in lib\Entry_Evo_libs, and for 800x480 / 1440x540 python3 with Pillow in WSL
rem (make gen draws those pictures into gen\<resolution> when the generator changed; 1280x480 is in the project).
setlocal
cd /d "%~dp0"
set IMAGE=gauge-entrynav2-tc
set TARGET=entrynav2-dist-all

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

echo [GEN] pictures of the other screen resolutions in WSL (make gen; only when the generator changed)
wsl --cd "%CD%" -e make gen
if errorlevel 1 (
    echo [WARNING] make gen failed ^(python3 with Pillow in WSL?^) - only the 1280x480 package is built
    set TARGET=entrynav2-dist
)

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
echo [BUILD] libGaugeApp.so for EntryNav2 and the packages (make %TARGET%)
docker run --rm -v "%CD%:/work" -w /work %IMAGE% make %TARGET%
if errorlevel 1 (
    echo [FAILED] make %TARGET% reported an error - see the messages above
    exit /b 1
)

echo.
echo C library versions the library needs (the car has 2.15; only GLIBC_2.4 expected):
docker run --rm -v "%CD%:/work" -w /work %IMAGE% sh -c "arm-linux-gnueabihf-objdump -T build/entrynav2/libGaugeApp.so | grep -o 'GLIBC_[0-9.]*' | sort -u"
echo.
for /d %%d in (dist\EntryNav2\*) do if exist "%%d\GaugeApp.tar" for %%f in ("%%d\GaugeApp.tar") do echo [DONE] %%~ff (%%~zf bytes)
echo Copy the package of the unit's screen to the car, e.g.:
echo   scp dist\EntryNav2\1280x480\GaugeApp.tar root@169.254.1.0:/tmp/   (then docs\EntryEvo_Installation.md)
exit /b 0

:nolibs
echo put libAppFramework.A.so and libCoreFramework.A.so from the car (/opt/hmi/lib) into lib\Entry_Evo_libs
exit /b 1
