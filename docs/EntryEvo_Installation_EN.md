# GAUGE APP – installing on EntryNav2 (EntryEVO)

[Polish version](EntryEvo_Installation.md)

The installation is done by hand, over SSH, with a few commands. Nothing in the system is replaced: one folder with
the app is added (`/opt/hmi/data/ro/Plugins/GaugeApp`) and one folder with its data (`/var/local/data/GaugeApp`).
The system partition is writable only while the files are copied.

> [!CAUTION]
> Keep the car parked with the ignition on for the whole installation. Do not switch the ignition off while the
> system is writable (step 3). When in doubt, restarting the head unit makes the system read-only again.
>
> Any change to the head unit is at your own risk. The app patches nothing and writes only into its own folders.

## What you need

- An **EntryNav2** head unit with **root access over SSH**.
- A computer with an SSH client (Windows 10/11 has OpenSSH built in, Linux, macOS).
- An **ENET cable** between the car's OBD socket and the computer. The computer's network card stays on automatic
  addressing.
- One of the packages from this project's `dist/` folder:

| Package | When |
|---|---|
| `gauge-app-entrynav2.tar` | **The normal version** – GAUGE APP shows the gauge screen at once. |
| `gauge-app-entrynav2-diag.tar` | Diagnostics only: a menu of test pages (see [below](#diagnostic-version)). |

Both packages install the same way. In the commands below the package name is in the variable `P` – use the one you
install (the examples use the normal version).

`169.254.1.0` is the head unit's address on the ENET cable in the car this was tested on. If yours differs, change
it in the commands.

## 1. Copy the package to the car

On the computer, in the project folder:

```sh
scp dist/gauge-app-entrynav2.tar root@169.254.1.0:/tmp/
ssh root@169.254.1.0
```

Type all the following commands in this SSH session, on the head unit. `/tmp` is in RAM: nothing is written to
flash yet.

## 2. Check the package and the head unit

Nothing is changed in this step.

```sh
P=gauge-app-entrynav2.tar
cd /tmp && rm -rf gauge && mkdir gauge && tar -xf $P -C gauge && cd gauge
md5sum -c MD5SUMS
df -k /
```

- Every file must answer `OK`.
- The `Available` column must show at least about 16000 (KB) of free space (the package is about 12.5 MB: the
  screen frames in four colours and ready-made pictures of numbers).

Now the system's loader checks that the head unit has every library and function the app needs, without running
anything:

```sh
LD_TRACE_LOADED_OBJECTS=1 LD_WARN=yes LD_BIND_NOW=yes LD_LIBRARY_PATH=/usr/local/lib:/opt/hmi/lib:/usr/lib:/lib \
    /lib/ld-linux-armhf.so.3 ./opt/hmi/data/ro/Plugins/GaugeApp/libGaugeApp.so 2>&1 | grep -E 'not found|undefined symbol'
```

**This command must print nothing.** Every line is a library or function this head unit lacks – in that case do
not install, and send that line.

## 3. Install

```sh
mount -o remount,rw /
mkdir -p /opt/hmi/data/ro/Plugins/GaugeApp
rm -f /opt/hmi/data/ro/Plugins/GaugeApp/*
cp opt/hmi/data/ro/Plugins/GaugeApp/* /opt/hmi/data/ro/Plugins/GaugeApp/
chmod 755 /opt/hmi/data/ro/Plugins/GaugeApp/libGaugeApp.so
sync
mount -o remount,ro /
cd / && md5sum -c /tmp/gauge/MD5SUMS
```

- The `rm -f` before copying is on purpose: iDrive keeps the old library in memory until it restarts, and a file
  that is deleted and copied anew is never overwritten under a running program.
- The last `md5sum -c` reads the installed files: each must answer `OK`.
- If `mount -o remount,ro /` fails, the restart in the next step makes the system read-only anyway.
- The library must be on the system partition: `/var/local/data` is mounted `noexec`, so iDrive could not load it
  from there. The app creates its data folder itself when it first starts.

Clean up and restart the head unit:

```sh
rm -rf /tmp/gauge /tmp/gauge-app-entrynav2*.tar
reboot
```

## 4. First start

After the restart the **ConnectedDrive** menu should have a **GAUGE APP** row (`applicationType="OnlineServices"`
in `GaugeApp.xml`). iDrive reads its apps only when it starts, so without a restart there is no row.

To have the row back in the **Media** menu (after Bluetooth audio, as in older versions): on the computer
`python3 make_db.py --menu media --layout-only` and a new package, or straight on the car:

```sh
mount -o remount,rw /
sed -i 's/applicationType="OnlineServices"/applicationType="Custom"/' /opt/hmi/data/ro/Plugins/GaugeApp/GaugeApp.xml
sync
mount -o remount,ro /
reboot
```

### Normal version

GAUGE APP opens the screen: coolant and oil on the left, g-meter in the middle with the gear and fuel tiles under
it, power and torque on the right, each with its maximum. Until the first data from the car arrives (about 1.5 s),
the values show `--`.

At start the log should have these lines:
- `settings: color=… temp=…` – the settings were read,
- `GaugeApp_frames.bin: … frames, … bytes` and `GaugeApp_frames_c0.bin: … frames` – the app loaded the screen frames
  (common ones and those in the chosen colour),
- `onInit: base onInit -> 1, 47 images written` – the screen was sent to iDrive,
- **no** `onError 9` (that error came from a too large image DB in older versions).

### Settings (OPTION button)

On the GAUGE APP screen press **OPTION** on the iDrive controller and choose **Settings**. Each press of a button
switches to the next value; the change shows on the screen at once and is saved in
`/var/local/data/GaugeApp/settings.txt`:

| Button | Values |
|---|---|
| Gauge colour | blue, red, BMW orange, green |
| Temperature | Celsius, Fahrenheit |
| Power | PS, kW, hp |
| Torque | Nm, lb-ft |
| Fuel | litres, US gallons |

The same file holds `screen=` – the screen shown last (0 Engine … 4 Warm-up). Opening GAUGE APP goes back to
the screen you were on last, also after a restart.

The maxima are kept in base units (°C, PS, Nm), so changing a unit does not spoil them – they are only shown
differently. The fuel (amount in the tank) has its own tile next to the gears.

**The language** follows the iDrive language by itself: Polish for Polish, English for any other language (titles,
"PS" instead of "KM", decimal point). The log shows it as `CDS vehicle.language = '{"language":18}'` (18 = Polish).

**If the GAUGE APP row disappears after installing** (iDrive did not accept the OPTION menu): remove the OPTION
menu from the XML and restart. Everything else (screen, fuel, saved settings) keeps working:

```sh
mount -o remount,rw /
sed -i '/<optionComponents>/,/<\/optionComponents>/d' /opt/hmi/data/ro/Plugins/GaugeApp/GaugeApp.xml
sync
mount -o remount,ro /
reboot
```

### Diagnostic version

Results of the diagnostics on the car (EntryNav2, F40):
- **diagnostics 1** (T1–T5): labels work, images do not – with a 635-image DB (`onError 9`);
- **diagnostics 2** (D1–D6): with a small DB everything works – an image from the DB, an icon on a button, a picture
  sent by the app as data (raImage) and labels. The size of the image DB was the problem;
- **diagnostics 3** (E1–E4): x/y positions and stacking work, the visible area is about 1250 × 470 px, refreshing
  at about 4.9 frames/s runs smoothly, `onError 9` is gone.

That is why the normal version keeps its frames in `GaugeApp_frames.bin` and sends them as data, and the image DB
only holds the icon. A later finding: iDrive shows at most about 60 images in one state, so the screen uses 47.

The package `gauge-app-entrynav2-diag.tar` (built on demand: `python3 make_db.py --diag-out diag`,
`make entrynav2-diag-dist`) is **diagnostics 3**. GAUGE APP opens a menu with four buttons. Open each and take a
photo of the **whole screen**:

| Button | What you should see | What it checks |
|---|---|---|
| **E1** | a "549 x 484" card with a gauge icon in its top left corner, a second icon further right (about 150 px below the top of the card) | whether x/y positions and stacking of images (from the DB) work |
| **E2** | the same as E1 | the same for pictures sent as data |
| **E3** | a grid with numbers every 100 px and a red frame, "1280 x 560" written on it | how large a picture fits on the screen – the numbers at the edges show how many pixels are visible |
| **E4** | a card with a digit 0–9 and a blue square that change 5 times a second | whether iDrive keeps up with smooth refreshing (best: record a few seconds of video) |

Send:
1. photos of pages E1–E4 (for E3 so that the numbers at the right and bottom edges of the screen can be read), a
   short video of E4,
2. the app's log (see [below](#log)) – the `diag: …` lines matter, especially `diag: 50 animation frames in … ms`
   (they appear once page E4 has been open for at least 10 s).

## Log

```sh
cat /var/local/data/GaugeApp/gauge-app.log
```

The log is always on and limited to 512 KB (the older part goes to `gauge-app.old.log`). The important lines:

- `onInit: base onInit -> 1, 47 images written` – the app started and set up its images;
- `onError …` – an error reported by iDrive (e.g. `onError 9`);
- `CDS <name> = '<value>' -> ok` – raw data from the car, the first 5 readings of every value.

The log can also go to a USB stick: on the computer create an empty file `gauge-app.log` in the stick's root folder
and plug it into the car. The app looks for that file in the folders under `/media`, `/mnt` and `/run/media`.

## Updating and switching versions

Repeat steps 1–3 with the new package (e.g. `gauge-app-entrynav2.tar` after the diagnostics). The data folder stays,
so the settings are kept.

## Maxima

The maxima of coolant, oil, power and torque start from zero every time the app starts (that is, every time iDrive
starts). Those of the last drive stay in `/var/local/data/GaugeApp/max.txt` to look at, e.g.:

```
coolant=98.0
oil=93.0
power=277.6
torque=419.0
```

They are also written to the log at start: `maxima reset (last run: coolant=98.0 oil=93.0 …)`.

## Switching off and uninstalling

**Switch off without removing** (the app does not start the next time iDrive starts):

```sh
touch /var/local/data/GaugeApp/app.disable
reboot
```

To switch it on again: `rm -f /var/local/data/GaugeApp/app.disable` and restart.

**Uninstall:**

```sh
mount -o remount,rw /
rm -rf /opt/hmi/data/ro/Plugins/GaugeApp
sync
mount -o remount,ro /
rm -rf /var/local/data/GaugeApp
reboot
```

Without the last `rm -rf /var/local/data/GaugeApp` the settings stay for a later installation.

## Troubleshooting

| What you see | What to do |
|---|---|
| No GAUGE APP row in ConnectedDrive | Check step 3 (`md5sum -c`) and restart the head unit. Then look at the log: if it is empty, iDrive did not load the library. |
| iDrive restarts several times right after starting | The crash-loop guard switches the app off after 3 iDrive restarts within 2 minutes of loading it, and iDrive carries on without it. After checking the log: `rm -f /var/local/data/GaugeApp/app-guard`, restart. |
| The GAUGE APP screen is empty | Look for the line `GaugeApp_frames.bin: … frames` in the log – `cannot read …GaugeApp_frames.bin` means the file was not copied (step 3). Then send the log and a photo. |
| Part of the screen is empty, the rest works | iDrive shows at most about 60 images in a state. Send a photo – it shows from which element on they are missing. |
| `--` everywhere | The car sends no data to the app: after 25 s the log shows `no CDS value arrived…`. Send the log. |
| The system was left writable | `mount -o remount,ro /` or restart the head unit. |
| The iDrive screen does not respond | Hold the iDrive power button for about 30 s to restart the head unit. |
