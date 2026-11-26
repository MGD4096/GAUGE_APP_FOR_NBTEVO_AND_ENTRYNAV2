@echo off
rem SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
rem Builds the NBT Evo version with the QNX SDP 6.5.0 compiler (installed with QNX Momentics IDE 4.7) on Windows and
rem puts everything the head unit needs into one folder per screen resolution:
rem   dist\NBT\1280x480\GaugeApp, dist\NBT\1440x540\GaugeApp   (no 800x480: NBT Evo has no 6.5" screens)
rem each with libGaugeApp.so (the same for all), GaugeApp.manifest, GaugeApp.xml, the two zips, the frame packs,
rem install.sh, uninstall.sh and FILES (the same package folder as EntryNav2's). On the unit, on hu-omap:
rem   cd /tmp/GaugeApp && sh install.sh      (docs\NbtEvo_Installation.md; it does not restart the unit)
rem
rem   build_nbt.bat                     (QNX found in C:\QNX650 or already on the PATH)
rem   build_nbt.bat D:\QNX650           (another QNX folder)
rem
rem Needs the head unit's libAppFramework.A.so and libCoreFramework.A.so (/opt/hmi/ID5/lib) in lib\NBT_evo_libs.
rem The 1280x480 pictures, XML and frame packs are in the project; 1440x540 comes from gen\1440x540
rem (python3 make_db.py --all, or make gen, in WSL) and is skipped when that folder is missing.
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

set LIB=build\nbt\libGaugeApp.so
if not exist build\nbt mkdir build\nbt
if exist "%LIB%" del "%LIB%"

echo [BUILD] libGaugeApp.so for NBT Evo (QNX 6.5, ARMv7, GNU libstdc++ like HmiMain3D)
qcc -Vgcc_ntoarmv7le_gpp -O2 -Wall -Wc,-Wextra -Wc,-std=gnu++98 -D_QNX_SOURCE -fPIC -fvisibility=hidden -I src ^
    -shared -Wl,-soname,libGaugeApp.so -o "%LIB%" ^
    src\engine_data.cpp src\cds.cpp src\render.cpp src\frames.cpp src\storage.cpp src\log.cpp ^
    lib\NBT_evo_libs\libAppFramework.A.so lib\NBT_evo_libs\libCoreFramework.A.so ^
    -Wl,--allow-shlib-undefined -lang-c++
if errorlevel 1 (
    echo [FAILED] qcc reported an error - send the messages above
    exit /b 1
)

echo.
echo BMW functions the library needs (all must exist in lib\NBT_evo_libs):
where ntoarmv7-nm >nul 2>nul && ntoarmv7-nm -D --undefined-only "%LIB%" | findstr bmw
echo.

call :pack 1280x480 plugin
for %%r in (1440x540) do (
    if exist "gen\%%r\GaugeApp_frames.bin" (
        call :pack %%r gen\%%r
    ) else (
        echo [SKIPPED] %%r - gen\%%r is missing: run python3 make_db.py --all ^(or make gen^) in WSL
    )
)
echo Copy the GaugeApp folder of the unit's screen to /tmp on hu-omap and run: cd /tmp/GaugeApp ^&^& sh install.sh
exit /b 0

rem :pack <resolution> <folder with its XML, zips and frame packs> - like toolchain\pack.sh
:pack
set OUT=dist\NBT\%~1\GaugeApp
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%"
copy /y "%LIB%" "%OUT%\" >nul
copy /y plugin\GaugeApp.manifest "%OUT%\" >nul
copy /y "%~2\GaugeApp.xml" "%OUT%\" >nul
copy /y "%~2\GaugeApp_ALL_Texts.zip" "%OUT%\" >nul
copy /y "%~2\GaugeApp_ALL_Images.zip" "%OUT%\" >nul
copy /y "%~2\GaugeApp_frames*.bin" "%OUT%\" >nul
rem FILES: size and name of every plugin file (install.sh checks them; it accepts these CRLF line ends)
if exist "%OUT%\..\FILES.new" del "%OUT%\..\FILES.new"
for %%f in ("%OUT%\*") do >>"%OUT%\..\FILES.new" echo %%~zf %%~nxf
move /y "%OUT%\..\FILES.new" "%OUT%\FILES" >nul
copy /y package\install.sh "%OUT%\" >nul
copy /y package\uninstall.sh "%OUT%\" >nul
echo [DONE] %OUT%
exit /b 0

:nolibs
echo put libAppFramework.A.so and libCoreFramework.A.so from the car (/opt/hmi/ID5/lib) into lib\NBT_evo_libs
exit /b 1
