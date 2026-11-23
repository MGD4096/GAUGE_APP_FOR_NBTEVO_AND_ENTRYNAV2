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
