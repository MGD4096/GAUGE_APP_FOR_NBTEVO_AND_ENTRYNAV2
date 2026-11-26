# GAUGE APP – installing on NBT Evo

The installation is done by hand: the files reach the head unit from a USB stick or over SSH, followed by a few
commands in the head unit's shell. Nothing in the system is replaced: one folder with the app is added
(`/opt/hmi/ID5/data/ro/Plugins/GaugeApp`) and one folder with its data (`/var/opt/gaugeapp`). The system partition
is writable only while the files are copied.

> [!CAUTION]
> Keep the car parked with the ignition on for the whole installation. Do not switch the ignition off while the
> system is writable (step 3, while `install.sh` runs). When in doubt, restarting the head unit makes the system read-only again.
>
> Any change to the head unit is at your own risk. The app patches nothing and writes only into its own folders.

> [!WARNING]
> The NBT Evo version **has not been run in a car yet**. Everything about the screen was checked on an EntryNav2
> (F40). Not checked on NBT: the size of the app's area (the layout is 1104×460 px), the limit of about 60 images in
> one state, where the row goes in the menu (`OnlineServices` = ConnectedDrive), `vehicle.language` and the gear
> coding. The first start is the test – see [First start](#5-first-start).

## What you need

- An **NBT Evo** head unit (ID5 / ID6) with a **root shell over SSH**. This guide does not cover how to get it.
- One of the codings **A4A, A4A_REMOTE_APPS, REMOTE_HMI, TOUCH_COMMAND** – without it HmiMain3D does not load
  PluginApps (the same as for NbtAad).
- The built app: **`dist\NBT\<resolution>\GaugeApp.tar`** from `build_nbt.bat` (QNX Momentics IDE 4.7 /
  QNX SDP 6.5.0, see [README.md](../README.md#build)): `1280x480` (8.8" screen) or `1440x540` (10.25"),
  whichever the unit has (NBT Evo has no 6.5" screens, so there is no 800x480 version). It unpacks to the folder
  `GaugeApp` (also beside the tar): the 11 files of the app, and `install.sh`, `uninstall.sh` and `FILES` (the list
  `install.sh` checks):

  | File | What it is |
  |---|---|
  | `libGaugeApp.so` | the app |
  | `GaugeApp.manifest` | the manifest for iDrive |
  | `GaugeApp.xml` | the menu row and the screens |
  | `GaugeApp_ALL_Texts.zip`, `GaugeApp_ALL_Images.zip` | texts and the row icon |
  | `GaugeApp_frames.bin`, `GaugeApp_frames_s.bin`, `GaugeApp_frames_c0.bin` … `c3.bin` | the screen frames (engine screen, the other screens and 4 colours) |

- A **USB stick** (FAT32) **or SSH from the computer** to get the tar onto the head unit.
- About **16 MB** of free space on the system partition.

## 1. Get the tar onto the head unit

The aim is `GaugeApp.tar` in `/tmp` of `hu-omap`, unpacked there to `/tmp/GaugeApp` – the same tar, the same place
and the same script as on EntryNav2; only the way there differs ([the install standard](Install_Standard.md), shared
with other apps). `/tmp` is RAM: nothing is written to flash yet, and it is emptied at a restart, so finish the
installation before switching the car off.

### Option A: USB stick (recommended)

On the computer, copy `GaugeApp.tar` (from `dist\NBT\<resolution>`) to the root of the stick and plug the stick into
the car's USB port, with the ignition on. On the head unit it is `/fs/usb0/GaugeApp.tar`; if `ls /fs/usb0` shows
nothing, look at `ls /mnt` – the stick may be in a folder named `umass…`; then use that instead of `/fs/usb0`. The
copy is made in step 2, on `hu-omap`.

### Option B: over SSH, with no stick

The head unit has no `scp` or `sftp`, so the tar goes through `cat` – one login. Replace `root@CAR` with however you
log in; if your SSH client refuses the host key, add `-o HostKeyAlgorithms=+ssh-rsa`. From the
`dist\NBT\<resolution>` folder on the computer (e.g. in Git Bash or WSL):

```sh
ssh root@CAR 'cat > /net/hu-omap/fs/ram5/GaugeApp.tar' < GaugeApp.tar
```

`/net/hu-omap/fs/ram5` is `/tmp` of `hu-omap`. After many logins in a short time the head unit shuts SSH off for about
10 minutes.

## 2. Log in to the right computer of the head unit and unpack

SSH opens a shell on `hu-jacinto`, while iDrive (HmiMain3D) runs on the other computer, `hu-omap`. Switch to it:

```sh
on -f /net/hu-omap/ /bin/sh
```

Type all the following commands in this shell (`install.sh` refuses to run on `hu-jacinto`). With a USB stick, copy
the tar first:

```sh
cp /fs/usb0/GaugeApp.tar /tmp/
```

Then unpack it:

```sh
cd /tmp && rm -rf GaugeApp && tar -xf GaugeApp.tar
```

If the unit says `tar: not found`, use `pax -r -f GaugeApp.tar` instead. (Without any tar the folder itself works too:
copy the `GaugeApp` folder to the stick and `cp -R /fs/usb0/GaugeApp /tmp/`.)

## 3. Install

```sh
cd /tmp/GaugeApp && sh install.sh
```

`install.sh` is the same on NBT Evo and EntryNav2. It:

1. checks the package: every file listed in `FILES` must be there with its size;
2. on EntryNav2, asks the system's loader whether the unit has every library and function the app needs (nothing
   is installed if not);
3. makes the system partition writable, removes the old version, copies the plugin, makes the library executable,
   checks the copied files and makes the partition read-only again;
4. resets the crash guard after an earlier failed version, and keeps the data folder (settings, maxima).

It **does not restart anything** – install every app you want first, then restart the head unit yourself. iDrive
loads its apps only when it starts, so until then the old version (or none) runs. Any error stops it with an
`install: ERROR:` line and the partition goes back to read-only.

It ends with `install: installed 11 files into /opt/hmi/ID5/data/ro/Plugins/GaugeApp`. `/fs/sda0` needs about 16 MB
free (`df -h /fs/sda0`); a full partition stops the copy with an error. The data folder `/var/opt/gaugeapp`
(settings, maxima) is created by the app itself when it first starts.

## 4. Restart

When everything you install is in place: hold the iDrive power button for about 30 s, or switch the car off until
the head unit has shut down and start it again. The head unit cannot flush its writes on demand, so leave it on for
about a minute after installing before switching it off.

## 5. First start

After the restart the **ConnectedDrive** menu should have a **GAUGE APP** row. If it is not there, look in the
**Media** menu and at [Troubleshooting](#troubleshooting).

GAUGE APP opens the screen: coolant and oil on the left, g-meter in the middle with the gear and fuel tiles under
it, power and torque on the right. Until the first data from the car arrives (about 1.5 s), the values show `--`.

As this is the first start of the NBT version, please send:

1. **a photo of the whole GAUGE APP screen** – it shows whether the layout fits the app's area and whether every
   element shows (the g-meter, gears and fuel too – on EntryNav2 the elements above about the 60th stayed empty),
2. **the log** (see [Log](#log)),
3. where the GAUGE APP row appeared (ConnectedDrive, Media, nowhere).

If the screen is too large or shifted, the layout is changed in `make_db.py` (`SCALE`, `--x`, `--y`), with no change
to the code.

### Settings (OPTION button)

On the GAUGE APP screen press **OPTION** and choose **Settings**. Each press of a button switches to the next
value; the change shows at once and is saved in `/var/opt/gaugeapp/settings.txt`:

| Button | Values |
|---|---|
| Gauge colour | blue, red, BMW orange, green |
| Temperature | Celsius, Fahrenheit |
| Power | PS, kW, hp |
| Torque | Nm, lb-ft |
| Fuel | litres, US gallons |

The same file holds `screen=` – the screen shown last (0 Engine … 4 Warm-up). Opening GAUGE APP goes back to
the screen you were on last, also after a restart.

**The language** follows the iDrive language by itself (`vehicle.language`): Polish for Polish, English for any
other language.

**The maxima** of coolant, oil, power and torque start from zero every time the app starts. Those of the last drive
stay in `/var/opt/gaugeapp/max.txt`.

## Log

The NBT version writes to the system log:

```sh
sloginfo | grep GaugeApp
```

Easier: on the computer create an **empty file `gauge-app.log`** in the root folder of a USB stick and plug it into
the car – the log is appended there (up to 4 MB). The app looks for it in `/fs/usb*` and `/mnt/umass*`.

The important lines at start:

- `library loaded …` and `create: app …` – iDrive loaded the app,
- `settings: color=… temp=…` – the settings were read,
- `GaugeApp_frames.bin: … frames` and `GaugeApp_frames_c0.bin: … frames` – the screen frames were loaded,
- `onInit: base onInit -> 1, … images written` – the screen was sent to iDrive,
- `onError …` – an error reported by iDrive (on EntryNav2 `onError 9` meant a too large image DB),
- `CDS <name> = '<value>' -> ok` – raw data from the car, the first 5 readings of every value (`driving.gear`,
  `driving.acceleration`, `vehicle.language`… – needed to check the NBT).

After 25 s with no data at all from the car the log shows `no CDS value arrived…`.

## Updating

Build the new version (`build_nbt.bat`) and repeat steps 1–4: `install.sh` replaces the old version. The settings
in `/var/opt/gaugeapp` stay.

## Switching off and uninstalling

**Switch off without removing** (the app does not start the next time iDrive starts). The head unit has no
`touch`, so:

```sh
mkdir -p /var/opt/gaugeapp
echo off > /var/opt/gaugeapp/app.disable
```

and restart. To switch it on again: `rm /var/opt/gaugeapp/app.disable` and restart.

**Uninstall:** from the package folder (in `/tmp/GaugeApp` as in step 1), on `hu-omap`:

```sh
cd /tmp/GaugeApp && sh uninstall.sh --purge
```

and restart. Without `--purge` the data folder (settings) stays for a later installation. By hand, without the
package:

```sh
/bin/mount -u -o rw /fs/sda0
rm -rf /opt/hmi/ID5/data/ro/Plugins/GaugeApp
/bin/mount -u -o ro /fs/sda0
rm -rf /var/opt/gaugeapp
```

## Troubleshooting

| What you see | What to do |
|---|---|
| No GAUGE APP row in ConnectedDrive | Look in the Media menu and check the coding (A4A / REMOTE_HMI…). Check that `install.sh` ended with `installed 11 files`, and the log: no `library loaded` = iDrive did not load the app. Row in Media instead of ConnectedDrive: on the computer `python3 make_db.py --menu media --layout-only` and a new `GaugeApp.xml` |
| The GAUGE APP screen is empty | Look for `GaugeApp_frames.bin: … frames` in the log – `cannot read …` means the file is missing (run `install.sh` again). Then send the log and a photo |
| Part of the screen is empty, the rest works | The limit of images in a state may differ on NBT from EntryNav2 (about 60). Send a photo – it shows from which element on they are missing |
| The screen is too large, cut off or shifted | The app's area on NBT has another size. Send a photo; the layout is changed in `make_db.py` (`SCALE`, `--x`, `--y`) |
| `--` everywhere | The car sends no data to the app: `no CDS value arrived…` in the log. Send the log |
| Wrong gear in D | On EntryNav2 the car sends the gearbox gear + 4. Send the `CDS driving.gear` lines from the log of a drive in D1 / D2 |
| iDrive does not come back after installing | Switch the app off (`echo off > /var/opt/gaugeapp/app.disable`) and restart. If that does not help, move the app's folder away: `/bin/mount -u -o rw /fs/sda0`, `mv /opt/hmi/ID5/data/ro/Plugins/GaugeApp /opt/GaugeApp.off`, `/bin/mount -u -o ro /fs/sda0`, restart. Send the log |
| The iDrive screen does not respond | Hold the iDrive power button for about 30 s to restart the head unit |
