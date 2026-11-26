# Installing plugin apps on NBT Evo and EntryNav2 – a common standard

How a native iDrive plugin app (an HmiMain3D `PluginApp`) is packaged and installed, the same way on **NBT Evo**
(ID5 / ID6, QNX) and **EntryNav2** (EntryEVO, Linux). Only getting the package onto the head unit differs; the
package, the folder it goes to and the script that installs it are the same. GaugeApp follows it; other projects can
copy the scripts and change five lines.

The reference implementation is in this repository:

| File | What |
|---|---|
| [`package/install.sh`](../package/install.sh) | the installer (POSIX `sh`, QNX or Linux by `uname`) |
| [`package/uninstall.sh`](../package/uninstall.sh) | the uninstaller |
| [`toolchain/pack.sh`](../toolchain/pack.sh) | builds the package folder and its tar (Linux / Docker) |
| [`build_nbt.bat`](../build_nbt.bat) (`:pack`) | the same package folder on Windows |
| [`tests/install_test.sh`](../tests/install_test.sh) | host test: both scripts on a fake root, as QNX and as Linux |

## Rules

1. **One package folder per app, named after the app** (`<App>/`, e.g. `GaugeApp/`). It holds the plugin's files,
   `install.sh`, `uninstall.sh` and `FILES`. Nothing else is needed on the unit.
2. **On the unit it goes to `/tmp/<App>`** (NBT Evo: `/tmp` of `hu-omap`). `/tmp` is RAM on both units: nothing is
   written to flash until the installer runs, and it is emptied at the next restart.
3. **Install = `cd /tmp/<App> && sh install.sh`**, on both units. It also works from wherever the folder is (a USB
   stick), because it finds its files next to itself. Run it with `sh`: FAT32 sticks carry no execute bit.
4. **The installer never restarts anything** – no `reboot`, no killing HmiMain3D. iDrive loads plugins only when it
   starts, so the user installs every app first and restarts the head unit **once**, by hand, at the end. Several
   apps installed in a row must not interfere with each other.
5. **It is all or nothing:** the package is checked before anything is written; any error stops with a line
   `install: ERROR: …` and a non-zero exit, and the system partition is made read-only again on every path.
6. **The system partition is writable only while the plugin is copied.**
7. **The app's data folder is never touched by `install.sh`** (settings, learned values survive an update);
   `uninstall.sh --purge` removes it.
8. **Every app has its own names:** plugin folder, data folder, `pluginAppConnector` id and `entryButtonFocusID` in
   the manifest / XML must not clash with other apps (see [the ids in use](#ids-in-use)).

## The package folder

```
<App>/
  FILES              size and name of every plugin file, one per line: "<bytes> <name>"
  install.sh         package/install.sh with the app's five lines
  uninstall.sh       package/uninstall.sh with the same five lines
  lib<App>.so        the plugin library
  <App>.manifest     the manifest HmiMain3D reads
  <App>.xml          the menu row and the states
  <App>_ALL_Texts.zip, <App>_ALL_Images.zip
  …                  any other file of the plugin (GaugeApp: GaugeApp_frames*.bin)
```

- `FILES` lists **exactly the files copied into the plugin folder** – not itself, not the scripts. It may have CRLF
  line ends (written on Windows); `install.sh` accepts both. Sizes rather than MD5 sums: the QNX shell may have no
  `md5sum`, while `wc -c` exists everywhere.
- For EntryNav2 the folder is also shipped as a tar that unpacks to `<App>/`
  (`tar -cf <app>.tar -C <out> <App>`), so one `scp` and one `tar -xf` in `/tmp` give `/tmp/<App>`.
- Per screen resolution (if the app has resolution-specific files): one package folder each, in
  `dist/<Unit>/<resolution>/<App>/` (GaugeApp: `dist/EntryNav2/1280x480/GaugeApp/`, `dist/NBT/1440x540/GaugeApp/`).

## What differs per unit (handled inside the scripts)

| | NBT Evo (QNX) | EntryNav2 (Linux) |
|---|---|---|
| `uname -s` | `QNX` | `Linux` |
| Where to run | `hu-omap` (`on -f /net/hu-omap/ /bin/sh` from the SSH shell on `hu-jacinto`) | the SSH shell |
| HMI folder | `/opt/hmi/ID5` | `/opt/hmi` |
| Plugin folder | `/opt/hmi/ID5/data/ro/Plugins/<App>` | `/opt/hmi/data/ro/Plugins/<App>` |
| Data folder (convention) | `/var/opt/<app>` | `/var/local/data/<App>` (mounted `noexec`: data only) |
| System partition writable | `/bin/mount -u -o rw /fs/sda0` | `mount -o remount,rw /` |
| … read-only again | `/bin/mount -u -o ro /fs/sda0` | `mount -o remount,ro /` |
| Restart (by the user) | hold the iDrive power button ~30 s, or switch off until the unit shuts down | `reboot` |
| Library check | – | the loader: `LD_TRACE_LOADED_OBJECTS=1 … /lib/ld-linux-armhf.so.3 lib<App>.so` must print no `not found` / `undefined symbol` |
| Missing tools | no `scp`, `sftp`, `touch`; maybe no `md5sum` | BusyBox |

The scripts recognise a wrong place by the HMI's `lib` folder (`/opt/hmi/ID5/lib` / `/opt/hmi/lib`): on NBT Evo's
`hu-jacinto` it is missing, and `install.sh` says to switch to `hu-omap`.

## Getting the package to `/tmp/<App>` (the only part that differs)

**EntryNav2** (SSH over the ENET cable; the unit is `169.254.1.0` in the car this was tested on):

```sh
scp <app>.tar root@169.254.1.0:/tmp/          # or: scp -r <App> root@169.254.1.0:/tmp/
ssh root@169.254.1.0
cd /tmp && rm -rf <App> && tar -xf <app>.tar
```

**NBT Evo**, USB stick (copy the `<App>` folder to the stick's root; on the unit it is `/fs/usb0/<App>`, or under
`/mnt/umass…`), in the shell on `hu-omap`:

```sh
rm -rf /tmp/<App> && cp -R /fs/usb0/<App> /tmp/
```

**NBT Evo** over SSH (no `scp`: one `cat` per file; `/net/hu-omap/fs/ram5` is `/tmp` of `hu-omap`). Many logins in a
short time shut SSH off for about 10 minutes:

```sh
ssh root@CAR 'mkdir -p /net/hu-omap/fs/ram5/<App>'
for f in <App>/*; do ssh root@CAR "cat > /net/hu-omap/fs/ram5/$f" < "$f"; done
```

## Installing, then one restart

```sh
cd /tmp/<App> && sh install.sh
# ... the same for every other app ...
reboot                                        # EntryNav2; NBT Evo: hold the power button ~30 s
```

## `install.sh` – what it does, in order

1. Finds the unit by `uname -s` (`GA_SYSTEM` overrides it in tests) and refuses an unknown system.
2. Checks it runs on the right computer: `<HMI>/lib` must exist (NBT Evo: else "run this on hu-omap").
3. Checks the package: `FILES` exists, every file it lists is there with that size, and `FILES` lists the library.
4. EntryNav2 only: the loader check of the library (nothing is installed if it reports a missing library or symbol).
5. Makes the system partition writable; from here a trap makes it read-only again on any exit.
6. Creates the plugin folder, **deletes its old files** (`rm -f <plugin folder>/*`), copies the files of `FILES`.
   Delete-then-copy on purpose: iDrive keeps the old library mapped until it restarts, and a running program's file is
   never overwritten in place.
7. `chmod 755` on the library, `sync` (QNX may have none: ignored).
8. Checks every copied file's size against the package (catches a full partition).
9. Makes the partition read-only again (a failure is reported, not fatal: the restart does it anyway).
10. Optional app hooks: GaugeApp removes its crash-guard file so a new version starts fresh, and mentions an
    `app.disable` file if the user switched the app off.
11. Prints `installed <n> files into <plugin folder>` and the reminder to restart – and stops.

Exit status: `0` installed; `1` and an `install: ERROR:` line otherwise (nothing changed if the error came before
step 5).

## `uninstall.sh`

```sh
sh uninstall.sh            # removes the plugin folder; the data folder stays
sh uninstall.sh --purge    # the data folder too
```

The same unit detection and the same writable-only-meanwhile rule; no restart. It works from any copy of the package
folder (after a restart `/tmp` is empty, so copy the folder there again first).

## Adopting it in another project

1. Copy `package/install.sh` and `package/uninstall.sh`. Change only the block at the top, the same in both:

   ```sh
   APP=MyApp                                     # plugin folder name = package folder name = /tmp/<APP>
   LIB=libMyApp.so                               # the plugin library
   DATA_QNX=/var/opt/myapp                       # the app's data folder on NBT Evo
   DATA_LINUX=/var/local/data/MyApp              # ... on EntryNav2
   GUARD=                                        # crash guard file in the data folder, "" = none
   ```

2. Build the package folder: copy and adapt `toolchain/pack.sh` (the list of plugin files), or on Windows the `:pack`
   routine of `build_nbt.bat`. `FILES` must be written **after** the plugin files are in the folder and **before** the
   scripts are copied in, so it lists only the plugin files.
3. Copy `tests/install_test.sh` and its line in `tests/Makefile`; adjust the paths and the number of files. It runs
   both scripts against a fake root (`GA_ROOT`) as QNX and as Linux (`GA_SYSTEM`): refusal on the wrong unit, a
   damaged package changing nothing, old files removed, the library executable, the data folder kept, CRLF `FILES`,
   uninstall with and without `--purge`, and that nothing restarts.
4. Write the app's install guide as: get the folder to `/tmp/<App>` (the unit's way), `sh install.sh`, restart.

Keep the scripts to POSIX `sh` and the tools both units have (`uname`, `dirname`, `wc`, `tr`, `cp`, `rm`, `mkdir`,
`chmod`, `mount`): NBT Evo runs QNX's `ksh`, EntryNav2 BusyBox `ash`. No `local`, arrays, `[[ ]]`, `md5sum` or
`touch`.

## Ids in use

The `pluginAppConnector` id (manifest) and `entryButtonFocusID` (XML) must differ between installed apps:

| App | connector id | entryButtonFocusID | applicationWeight |
|---|---|---|---|
| entry-aad (Android Auto, EntryNav2) | 210 | 32752 | 200 |
| GaugeApp | 211 | 32751 | 210 |
| CdsScan (diagnostics) | 212 | 32753 | 212 |

## Status

The scripts pass the host test (`make check`, run in `dash`). They have not yet run on a real unit; the first
installation on each unit (QNX `ksh`, BusyBox `ash`) is their real test.
