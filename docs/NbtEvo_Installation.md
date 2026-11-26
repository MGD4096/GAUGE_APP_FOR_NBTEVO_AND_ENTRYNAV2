# GAUGE APP – installing on NBT Evo

The installation is done by hand: the files reach the head unit from a USB stick or over SSH, followed by a few
commands in the head unit's shell. Nothing in the system is replaced: one folder with the app is added
(`/opt/hmi/ID5/data/ro/Plugins/GaugeApp`) and one folder with its data (`/var/opt/gaugeapp`). The system partition
is writable only while the files are copied.

> [!CAUTION]
> Keep the car parked with the ignition on for the whole installation. Do not switch the ignition off while the
> system is writable (step 4). When in doubt, restarting the head unit makes the system read-only again.
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
- The built app: the folder **`dist\NBT\<resolution>\GaugeApp`** from `build_nbt.bat` (QNX Momentics IDE 4.7 /
  QNX SDP 6.5.0, see [README.md](../README.md#build)): `1280x480` (8.8" screen) or `1440x540` (10.25"),
  whichever the unit has (NBT Evo has no 6.5" screens, so there is no 800x480 version). It should hold 11 files:

  | File | What it is |
  |---|---|
  | `libGaugeApp.so` | the app |
  | `GaugeApp.manifest` | the manifest for iDrive |
  | `GaugeApp.xml` | the menu row and the screens |
  | `GaugeApp_ALL_Texts.zip`, `GaugeApp_ALL_Images.zip` | texts and the row icon |
  | `GaugeApp_frames.bin`, `GaugeApp_frames_s.bin`, `GaugeApp_frames_c0.bin` … `c3.bin` | the screen frames (engine screen, the other screens and 4 colours) |

- A **USB stick** (FAT32) **or SSH from the computer** to get the files onto the head unit.
- About **16 MB** of free space on the system partition.

## 1. Get the files onto the head unit

### Option A: USB stick (recommended)

1. On the computer, copy the `GaugeApp` folder (from `dist\NBT\<resolution>`) to the root of the stick.
2. Plug the stick into the car's USB port, with the ignition on.

The files will be in `/fs/usb0/GaugeApp`. If `ls /fs/usb0` shows nothing, look at `ls /mnt` – the stick may be in a
folder named `umass…`; then use that instead of `/fs/usb0` in the commands below.

### Option B: over SSH, with no stick

The head unit has no `scp` or `sftp`, so each file goes through `cat`. Replace `root@CAR` with however you log in;
if your SSH client refuses the host key, add `-o HostKeyAlgorithms=+ssh-rsa`. From the `dist\NBT\<resolution>` folder on the
computer (e.g. in Git Bash or WSL):

```sh
ssh root@CAR 'mkdir -p /net/hu-omap/fs/ram5/GaugeApp'
for f in GaugeApp/*; do
  ssh root@CAR "cat > /net/hu-omap/fs/ram5/$f" < "$f"
done
```

That is 11 logins. After many logins in a short time the head unit shuts SSH off for about 10 minutes, so do not
run the loop over and over. The files land in `/tmp/GaugeApp` on `hu-omap` – RAM, emptied at a restart, so finish
the installation before switching the car off.

## 2. Log in to the right computer of the head unit

SSH opens a shell on `hu-jacinto`, while iDrive (HmiMain3D) runs on the other computer, `hu-omap`. Switch to it:

```sh
on -f /net/hu-omap/ /bin/sh
```

Type all the following commands in this shell. Set where the files come from:

```sh
SRC=/fs/usb0/GaugeApp        # USB stick
SRC=/tmp/GaugeApp            # or: over SSH
```

(type only one of these lines).

## 3. Check the files and the free space

Nothing is changed in this step.

```sh
ls -l $SRC
df -h /fs/sda0
```

- `$SRC` must hold the 10 files from the table above; `libGaugeApp.so` is a few tens of KB, `GaugeApp_frames.bin`
  about 6 MB.
- `/fs/sda0` must have at least about 16 MB free.

## 4. Install

```sh
/bin/mount -u -o rw /fs/sda0
mkdir -p /opt/hmi/ID5/data/ro/Plugins/GaugeApp
rm -f /opt/hmi/ID5/data/ro/Plugins/GaugeApp/*
cp $SRC/* /opt/hmi/ID5/data/ro/Plugins/GaugeApp/
chmod 755 /opt/hmi/ID5/data/ro/Plugins/GaugeApp/libGaugeApp.so
ls -l /opt/hmi/ID5/data/ro/Plugins/GaugeApp
/bin/mount -u -o ro /fs/sda0
```

- The `rm -f` before copying is on purpose: iDrive keeps the old library in memory until it restarts, and a file
  that is deleted and copied anew is never overwritten under a running program.
- `ls -l` after copying must show the same 10 files with the same sizes as in step 3.
- The head unit cannot flush its writes on demand: leave it on for about a minute more before switching off.
- The data folder `/var/opt/gaugeapp` (settings, maxima) is created by the app itself when it first starts.

Then restart the head unit: hold the iDrive power button for about 30 s, or switch the car off until the head unit
has shut down and start it again. iDrive reads its apps only when it starts.

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

Build the new version (`build_nbt.bat`) and repeat steps 1–4. The settings in `/var/opt/gaugeapp` stay.

## Switching off and uninstalling

**Switch off without removing** (the app does not start the next time iDrive starts). The head unit has no
`touch`, so:

```sh
mkdir -p /var/opt/gaugeapp
echo off > /var/opt/gaugeapp/app.disable
```

and restart. To switch it on again: `rm /var/opt/gaugeapp/app.disable` and restart.

**Uninstall:**

```sh
/bin/mount -u -o rw /fs/sda0
rm -rf /opt/hmi/ID5/data/ro/Plugins/GaugeApp
/bin/mount -u -o ro /fs/sda0
rm -rf /var/opt/gaugeapp
```

and restart. Without the last `rm -rf /var/opt/gaugeapp` the settings stay for a later installation.

## Troubleshooting

| What you see | What to do |
|---|---|
| No GAUGE APP row in ConnectedDrive | Look in the Media menu and check the coding (A4A / REMOTE_HMI…). Check step 4 (`ls -l`) and the log: no `library loaded` = iDrive did not load the app. Row in Media instead of ConnectedDrive: on the computer `python3 make_db.py --menu media --layout-only` and a new `GaugeApp.xml` |
| The GAUGE APP screen is empty | Look for `GaugeApp_frames.bin: … frames` in the log – `cannot read …` means the file is missing (step 4). Then send the log and a photo |
| Part of the screen is empty, the rest works | The limit of images in a state may differ on NBT from EntryNav2 (about 60). Send a photo – it shows from which element on they are missing |
| The screen is too large, cut off or shifted | The app's area on NBT has another size. Send a photo; the layout is changed in `make_db.py` (`SCALE`, `--x`, `--y`) |
| `--` everywhere | The car sends no data to the app: `no CDS value arrived…` in the log. Send the log |
| Wrong gear in D | On EntryNav2 the car sends the gearbox gear + 4. Send the `CDS driving.gear` lines from the log of a drive in D1 / D2 |
| iDrive does not come back after installing | Switch the app off (`echo off > /var/opt/gaugeapp/app.disable`) and restart. If that does not help, move the app's folder away: `/bin/mount -u -o rw /fs/sda0`, `mv /opt/hmi/ID5/data/ro/Plugins/GaugeApp /opt/GaugeApp.off`, `/bin/mount -u -o ro /fs/sda0`, restart. Send the log |
| The iDrive screen does not respond | Hold the iDrive power button for about 30 s to restart the head unit |
