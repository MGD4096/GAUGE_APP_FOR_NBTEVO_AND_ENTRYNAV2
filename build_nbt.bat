@echo off
rem SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
rem Builds the NBT Evo version with the QNX SDP 6.5.0 compiler (installed with QNX Momentics IDE 4.7) on Windows and
rem puts everything the head unit needs into dist\nbt\GaugeApp:
rem   libGaugeApp.so, GaugeApp.manifest, GaugeApp.xml, the two zips and the frame packs.
rem
rem   build_nbt.bat                     (QNX found in C:\QNX650 or already on the PATH)
rem   build_nbt.bat D:\QNX650           (another QNX folder)
rem
rem Needs the head unit's libAppFramework.A.so and libCoreFramework.A.so (/opt/hmi/ID5/lib) in lib\NBT_evo_libs.
rem The pictures, the XML and the frame packs are shared with the EntryNav2 version and are already in the project.
setlocal
cd /d "%~dp0"

set QNXDIR=%~1
if "%QNXDIR%"=="" set QNXDIR=C:\QNX650

where qcc >nul 2>nul
if errorlevel 1 (
    if exist "%QNXDIR%\qnx650-env.bat" (
        call "%QNXDIR%\qnx650-env.bat"
    ) else (
        echo qcc not found and no %QNXDIR%\qnx650-env.bat - pass the QNX folder: build_nbt.bat D:\QNX650
        exit /b 1
    )
)
where qcc >nul 2>nul
if errorlevel 1 (
    echo qcc still not found after %QNXDIR%\qnx650-env.bat
    exit /b 1
)

if not exist lib\NBT_evo_libs\libAppFramework.A.so goto nolibs
if not exist lib\NBT_evo_libs\libCoreFramework.A.so goto nolibs

set OUT=dist\nbt\GaugeApp
if not exist "%OUT%" mkdir "%OUT%"
if exist "%OUT%\libGaugeApp.so" del "%OUT%\libGaugeApp.so"

echo [BUILD] libGaugeApp.so for NBT Evo (QNX 6.5, ARMv7, GNU libstdc++ like HmiMain3D)
qcc -Vgcc_ntoarmv7le_gpp -O2 -Wall -Wc,-Wextra -Wc,-std=gnu++98 -D_QNX_SOURCE -fPIC -fvisibility=hidden -I src ^
    -shared -Wl,-soname,libGaugeApp.so -o "%OUT%\libGaugeApp.so" ^
    src\engine_data.cpp src\cds.cpp src\render.cpp src\frames.cpp src\storage.cpp src\log.cpp ^
    lib\NBT_evo_libs\libAppFramework.A.so lib\NBT_evo_libs\libCoreFramework.A.so ^
    -Wl,--allow-shlib-undefined -lang-c++
if errorlevel 1 (
    echo [FAILED] qcc reported an error - send the messages above
    exit /b 1
)

copy /y GaugeApp.manifest "%OUT%\" >nul
copy /y GaugeApp.xml "%OUT%\" >nul
copy /y GaugeApp_ALL_Texts.zip "%OUT%\" >nul
copy /y GaugeApp_ALL_Images.zip "%OUT%\" >nul
copy /y GaugeApp_frames*.bin "%OUT%\" >nul

echo.
echo BMW functions the library needs (all must exist in lib\NBT_evo_libs):
where ntoarmv7-nm >nul 2>nul && ntoarmv7-nm -D --undefined-only "%OUT%\libGaugeApp.so" | findstr bmw
echo.
echo [DONE] %OUT% - copy this folder's files to /opt/hmi/ID5/data/ro/Plugins/GaugeApp on the head unit
exit /b 0

:nolibs
echo put libAppFramework.A.so and libCoreFramework.A.so from the car (/opt/hmi/ID5/lib) into lib\NBT_evo_libs
exit /b 1
