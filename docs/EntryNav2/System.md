# EntryNav2 (EntryEVO) – the head unit's system

What we know about the EntryNav2 head unit of a BMW F40, checked over SSH, from copied files and with tests in the car
(November 2026). The app framework: [PluginApp.md](PluginApp.md); CDS data: [CDS.md](CDS.md).

## Hardware and system

| | |
|---|---|
| Host name | `xse-j6-apn-entryevo` |
| Processor | TI Jacinto 6 (DRA7xx: process `lad_dra7xx`), ARMv7, hard-float, NEON |
| System | Linux with `systemd`, `dbus-daemon`, `udisks-daemon`, DLT logs (`dlt-daemon`); tools from BusyBox (`/bin/busybox.nosuid`) |
| C library | eglibc 2.15. Programs must not need symbols newer than `GLIBC_2.15` (GaugeApp needs only `GLIBC_2.4`) |
| Matching compiler | GCC 4.6 armhf from Ubuntu 12.04 (`toolchain/Dockerfile`), `-march=armv7-a -mfpu=neon -mfloat-abi=hard`, C++98 |
| HMI version | paths in `HmiMain3D` point to the build `EntryEvo_ID5_2211_Release` |

## Access

- SSH: `ssh root@169.254.1.0`, a link-local address, as with entry-aad.
- `/` is read-only. To install: `mount -o remount,rw /`, then `sync` and `mount -o remount,ro /` when done.
- Writable: `/var/local` (data, mounted `noexec`) and `/tmp` (RAM, cleared at restart).
- USB sticks are mounted by `udisks`. The exact mount point is not confirmed, so the apps look in `/media/*`,
  `/mnt/*` and `/run/media/*`.

## Important folders

| Path | Contents |
|---|---|
| `/opt/hmi/bin/HmiMain3D` | the whole HMI (about 69 MB), one process |
| `/opt/hmi/lib` | HMI libraries, among them `libAppFramework.A.so` and `libCoreFramework.A.so` (the plugin framework) and `libhmi*.so` |
| `/opt/hmi/data/ro/Plugins/<Name>/` | plugins (PluginApp): `<Name>.manifest`, library, XML, text and image DBs. GaugeApp and CdsScan live here |
| `/opt/hmi/data/ro/bmw/db/text.db`, `speech.db` | the HMI's text and speech databases |
| `/opt/hmi/data/ro/common/font/` | fonts (`BMWTALG.ttf`, `BMWTARG.ttf`, Chinese, Japanese, Korean) |
| `/opt/app/usr/hmi/data/ro/hmiplugins/` | the HMI's own plugins: `libhmiremoting.so` (remote API and CDS for apps, about 3.3 MB) with `RemotingPlugin.xml`, and `libhmia4a.so` with `A4APlugin.xml` |
| `/opt/app/usr/` | applications: `BTMedia`, `Browser`, `MediaPlayer` (including CarPlay and CarLife), `PIM`, `Portal`, `WLAN`, `Platform` |
| `/opt/aa/` | entry-aad (Android Auto): `aa-supervisor`, `entry-aad` |
| `/opt/navi/` | navigation (`EBNavi/NavStartup`, `Common/MapUpdate`) |
| `/opt/isp/` | speech recognition and TTS (`speechd`, `navigationttsd`, `natp`) |
| `/usr/local/bin/` | system services (list below) |
| `/var/local/data/HMI/` | HMI data: `resprof.txt`, `resource.cache` |
| `/var/local/data/GaugeApp/`, `/var/local/data/CdsScan/` | data and logs of our apps |
| `/var/local/data/AA/` | entry-aad settings |

## Processes

From `/proc/*/exe` of a running unit. The likely role in brackets.

| Group | Processes |
|---|---|
| HMI | `/opt/hmi/bin/HmiMain3D` (PID about 237) |
| System | `systemd`, `systemd-journald`, `systemd-logind`, `systemd-udevd`, `dbus-daemon`, `udisks-daemon`, `sshd`, `dhclient`, `mdnsd`, `hostapd` (Wi-Fi hotspot) |
| Logs | `dlt-daemon`, `dlt-dbus`, `dlt-system`, `a15_dlt_manager`, `winston`, `MONITOR`, `bootwart-daemon` |
| Talking to the car | `vmostd`, `ipcvmost` (virtual MOST to the car communication processor), `ipceventwatcher`, `icecd`, `DiagProxyIC`, `dtcproxy` |
| Management | `SystemManager`, `ResetManager`, `PersistencyManager`, `NORDataHandler`, `TimeServer`, `deletion-manager`, `sd-daemon`, `pia-pom-manager`, `suppliermenu`, `CETrigger` |
| Media | `MediaManagementServer`, `DDPServer`, `vmostAuxInBT`, `vmostAuxInUSB`, `vmostAuxinDiag`, `AuxInUCM`, `CARPLAY`, `CARLIFE`, `HDRadio`, `SDARS`, `SDARSMAIN`, `videoapp`, `micin` |
| Bluetooth / phone | `btmbt`, `btmmo`, `btmtel`, `evo_genivi_bt`, `evo_hli_socket`, `pimmo`, `pimpim`, `nfcd` |
| Online | `browserd`, `IPCEServer_linux-arm`, `lighttpd`, `telexd`, `datacomipd`, `telematicsassistd`, `cisuManager`, `dummd`, `wland` |
| Navigation and GPS | `NavStartup`, `MapUpdate`, `navistarter`, `gnsspmd` |
| Speech | `speechd`, `navigationttsd`, `natp` |
| Android Auto | `aa-supervisor`, `entry-aad` |

## HMI (`HmiMain3D`)

- One process that loads the plugins from `/opt/hmi/data/ro/Plugins` (through `*.manifest`) and from
  `/opt/app/usr/hmi/data/ro/hmiplugins`.
- It has open, among others, `text.db`, `speech.db`, `/var/local/data/HMI/resprof.txt`, `resource.cache` and the
  fonts from `/opt/hmi/data/ro/common/font`.
- `HmiMain3D` itself holds no CDS names of car data. It only holds the `A4A_CDS*` adapters (multimedia, contacts,
  online navigation, seat memory, Wi-Fi, charging) through which the HMI provides some properties itself.
- Restarting the HMI (or `reboot`) loads the plugins again.

## Display

Read on the car (F40 with the original 8.8" CID, November 2026):

| | |
|---|---|
| Display controller | TI OMAP DSS rev 6.1, kernel driver `omapdrm` (`/dev/dri/card0`, framebuffer `fb0`) |
| Panel driver | `panel-entryevo`, a loadable module (`/lib/modules/3.12.25-FR21.0/kernel/drivers/video/omap2/displays-new/panel-entryevo.ko`), device `connector.10` = device tree node `/connector@0` (`compatible = "xse,panel-entryevo"`); logs `Panel Mode: 1280x480` at boot |
| Kernel | 3.12.25-FR21.0 |
| DRM connector | `/sys/class/drm/card0-Unknown-1`: connected, one mode only: **1280x480** |
| HMI drawing | `HmiMain3D`: own 3D engine *Ines* on OpenGL ES 2 (EGL), a Wayland client; layers through GENIVI ILM (`CWal3dEntryEvo`, log tag `[WAL3D]`) |
| Resolutions the HMI code knows | `TEConstDefinitionType_` 800x480, 1280x480, 1280x720, 1440x540, 1920x720; taken from the unit's coding (`CRbCoding::getDisplaySize`); fallbacks 1440x540 / 800x480 when the coding is invalid |
| Plugin state area | about 1250 x 470 px of the 1280 x 480 panel |

The video mode is set by the kernel panel driver, not by the HMI: the HMI knowing 1920x720 does not make the unit send
it.

`panel-entryevo.ko` ("EntryEvo LCD Panel Driver", xse) holds exactly three timing tables (`omap_video_timings`), and no
1920x720:

| Mode | Pixel clock | H sync / front / back | V sync / front / back |
|---|---|---|---|
| 800x480 | 34.0 MHz | 128 / 40 / 88 | 5 / 14 / 26 |
| 1280x480 | 40.5 MHz | 15 / 70 / 1 | 1 / 11 / 2 |
| 1440x540 | 59.259 MHz | 15 / 263 / 2 | 1 / 8 / 25 |

The mode is chosen by the module parameter `panel_option` (string `<x>x<y>`, default `"1280x480"`), compared with
`strcmp` against the table names. On the car:

- `/sys/module/panel_entryevo/parameters/panel_option` = `1280x480`;
- the device tree node `/connector@0` has only `compatible`, `name` and `video-source` (no timings);
- `/etc/modprobe.d/blacklist.conf` blacklists `panel-entryevo` (no automatic load by alias), and
  `/etc/modules-load.d/panel-entryevo.conf` loads it by name at boot;
- no `options panel-entryevo …` line in `/etc/modprobe.d`.

- the kernel command line has no `panel_entryevo.*` or `video=` argument:
  `console=ttyO6,115200 consoleblank=0 root=/dev/mmcblk0p3 ro rootwait rootfstype=ext4 loglevel=4 ibcinfo=0xfff00000
  max_cpu_freq=1500000000 spidev.bufsiz=65536 systemd.setenv=DBUS_SESSION_BUS_ADDRESS=… reboot=c panic=-1
  omap_wdt.kernelpet=3 omap_wdt.nowayout=1 omap_panic_timeout=10 max_loop=2 printk.always_kmsg_dump`.

So the mode is the built-in default 1280x480, whatever the coding says. **`/etc/modprobe.d` options do not reach it**
(car-tested): `modprobe --show-depends panel-entryevo` lists the option, but the driver logs `Panel Mode` at 1.4 s,
before systemd starts (1.6 s, systemd 206). `/sbin/init` is `/usr/bin/earlystarter` (xse, "AEEVO FR21.0 20220718"),
which loads the module itself with `init_module` and an explicit `panel_option=<size>`:

1. if `/etc/panel-1440x540`, `/etc/panel-1280x480` or `/etc/panel-800x480` exists → that size (`Set CID size = %s by
   file`);
2. otherwise the coding `CID_DISPLAY_RES` (read through `/usr/local/lib/libhwinfoperscustom.so`): 1 → 800x480,
   2 → 1280x480, 3 → 1440x540, any other value → 1280x480 (`Set CID size = %s by coding`).

Coding 1920x720 therefore still gives 1280x480, and a default inside the module never applies (the explicit argument
wins). Root is `/dev/mmcblk0p3`, ext4, mounted read-only. The probe loops over the three tables, prints each as `"%dx%d"`, `strcmp`s it with `panel_option`
and falls back to the 1280x480 table. `../HU_Tools/PanelEntryEvo/patch_panel.py` overwrites the unused 800x480 table
with 1920x720 timings (13 bytes of `.rodata`, code unchanged); with `--slot 1280x480` it overwrites the 1280x480
table, which is also the fallback (`.rodata+0`), so `panel_option=1280x480` from earlystarter ends at 1920x720. Car-tested
(`panel-entryevo-1920-v2.ko`): `Set CID size = 1280x480 by coding`, then `Panel Mode: 1920x720`, and the DRM connector
lists only `1920x720`, with no DSS / DPI errors in dmesg. The MGU display, backlight on, still showed its own "No Signal"
text, the same as at 1280x480. So the APIX link itself does not come up; the resolution was only a second obstacle.

APIX on the Linux side:

- Linux I2C devices: bus 0 `adv7182` (analog video decoder, camera input); bus 1 `tca6416` (GPIO expander),
  `tps659038` (PMIC) and two `dummy` PMIC addresses. **No APIX serializer** is visible to Linux, so it is configured
  outside Linux (most likely by the car communication processor, which also reports the display faults) or fixed in
  hardware.
- `SystemManager` holds `/tmp/startup-mgr/APIX2` next to `CVBS1`/`CVBS2`, `Mic_In1`/`Mic_In2` and `USB1`/`USB2`. These are
  hardware-variant flags, so `APIX2` there most likely means a second APIX port, not the APIX generation.
- No debugfs `omapdss` folder, so the real pixel clock could not be read.

Fault memory of HU_ENTRYNAV2 with the MGU display (1920x720 module installed):

| DTC | Text | Meaning here |
|---|---|---|
| B7F8C3 | Headunit power supply to CID: no communication | the "power" fault: the HU gets no answer from the display over the APIX link; not an over-current |
| E1C468 | HU-B, K-CAN2 / K-CAN4: communication error | most likely from the many restarts |
| E1C440 | HU-B reset | the restarts |
| B7F850 | HU-B: microphone 2, open circuit | unrelated (no second microphone) |
| B7F8E5 | HU-B: unauthorised access to the control unit activated | the SSH / root access |

B7F8C3 confirms that the HU and the MGU display do not talk over APIX at all (no link, no back channel). The 800x480-slot variant loaded fine but changed nothing (as explained above). Without a patched module the option
can pick only one of the three built-in modes; a mode the display does not accept means a
black screen and SSH as the only way back. A 1920x720 output would need a rebuilt module with a fourth table, and it is
unknown whether the unit's APIX serializer and the MGU display would then work together. Retrofit test with an MGU CID (APIX3, 1920x720, powered over the APIX cable): coded APIX3 + 1920x720 →
"power supply" fault, "No signal"; coded APIX2 → power supply fault + display controller fault, "No signal". Not solved;
what decides the panel mode (device tree, boot arguments, coding read by the driver) is still open.

## Where the CDS data comes from

```
plugin (libGaugeApp.so)
  └─ bmw::PluginApp::cdsAddPropertyChangedEventHandler("engine.torque", …)       libAppFramework.A.so
       └─ the Etch connection of the manifest (pluginAppConnector, id)             → HmiMain3D
            └─ libhmiremoting.so: class TPCI::CCdsProperty<Name>, JSON from a printf template
                 └─ data from the car through vmostd / ipcvmost
  ←─ a value changes: PluginApp::invokeCDSUpdate(name, UTF-16 value) → our function
```

- The full list of names and formats is in `libhmiremoting.so`. Extract it on a PC: `strings`, searching for
  `CCdsProperty` and for the `{"…":%…}` templates. Result: [CDS.md](CDS.md).
- `grep` and `strings` on the unit are very slow. Better copy the file to a PC (`scp root@169.254.1.0:<file> .`)
  and search there.
- CDS names are stored as plain ASCII in `libhmiremoting.so`. They are neither in `HmiMain3D` nor in
  `/opt/hmi/lib/*.so`, which is why a plain `grep` over `/opt/hmi` finds nothing.

## Useful commands

```sh
df -k /                                                    # free space before installing
ps w                                                       # processes
for p in /proc/[0-9]*; do echo "$(basename $p) $(readlink $p/exe)"; done | sort -k2 -u   # process executables
ls -l /proc/$(pidof HmiMain3D)/fd                          # files the HMI has open
awk '{print $6}' /proc/$(pidof HmiMain3D)/maps | sort -u   # libraries and files mapped by the HMI
grep -l <text> $(awk '{print $6}' /proc/$(pidof HmiMain3D)/maps | grep '\.so' | sort -u)  # quick search
```

Run a long search in the background only once (`nohup sh -c '…' &`). Two identical jobs overwrite each other's result
file, and `kill` does not always stop them (then `reboot` helps).

## Language and units

- `vehicle.language`: 18 = Polish, 3 = US English (full list on the BimmerGestalt site).
- `vehicle.units` gives the car's unit settings (consumption, fuel, distance, temperature, sport power and torque).
- Plugin text DBs: `<language>.txt` in a zip, file names `pl`, `de`, `en-UK`, `en-US`, `es-ES`, `es-US`, `fr-FR`,
  `fr-CA`, `it`, `pt`, `ru`. The HMI picks the file by its language itself.
