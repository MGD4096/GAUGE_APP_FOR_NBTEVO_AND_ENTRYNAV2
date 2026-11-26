# GAUGE APP – installing on EntryNav2 (EntryEVO)

The installation is done by hand, over SSH, with a few commands. Nothing in the system is replaced: one folder with
the app is added (`/opt/hmi/data/ro/Plugins/GaugeApp`) and one folder with its data (`/var/local/data/GaugeApp`).
The system partition is writable only while the files are copied.

> [!CAUTION]
> Keep the car parked with the ignition on for the whole installation. Do not switch the ignition off while the
> system is writable (step 2, while install.sh runs). When in doubt, restarting the head unit makes the system read-only again.
>
> Any change to the head unit is at your own risk. The app patches nothing and writes only into its own folders.

## What you need

- An **EntryNav2** head unit with **root access over SSH**.
- A computer with an SSH client (Windows 10/11 has OpenSSH built in, Linux, macOS).
- An **ENET cable** between the car's OBD socket and the computer. The computer's network card stays on automatic
  addressing.
- One of the packages from this project's `dist/EntryNav2/<resolution>/` folder (`build_entryNav2.bat`). Each
  holds the package folder `GaugeApp/` (the app, `install.sh`, `uninstall.sh` and `FILES`) and the same folder as a
  tar:

| Package | When |
|---|---|
| `gauge-app-entrynav2.tar` | **The normal version** – GAUGE APP shows the gauge screen at once. |
| `gauge-app-entrynav2-diag.tar` | Diagnostics only (`dist/EntryNav2/diag/`): a menu of test pages (see [below](#diagnostic-version)). |

**Screen resolution.** There are three packages, one per resolution: `800x480` (6.5" screens), `1280x480`
(8.8", e.g. F40 – car-verified) and `1440x540` (10.25"). On an EntryNav2, `cat /sys/class/drm/card0-*/modes`
(over SSH) shows it. 800x480 and 1440x540 are the same look at another scale; not yet tried in a car.

Both packages install the same way, and the same way as on NBT Evo: the package folder goes to `/tmp/GaugeApp` and
`install.sh` runs there ([the install standard](Install_Standard.md), shared with other apps).

`169.254.1.0` is the head unit's address on the ENET cable in the car this was tested on. If yours differs, change
it in the commands.

## 1. Copy the package to the car

On the computer, in the project folder (pick the folder of the screen's resolution):

```sh
scp dist/EntryNav2/1280x480/gauge-app-entrynav2.tar root@169.254.1.0:/tmp/
ssh root@169.254.1.0
```

Type the following commands in this SSH session, on the head unit:

```sh
cd /tmp && rm -rf GaugeApp && tar -xf gauge-app-entrynav2.tar
```

(Or copy the folder itself: `scp -r dist/EntryNav2/1280x480/GaugeApp root@169.254.1.0:/tmp/`.) `/tmp` is in RAM:
nothing is written to flash yet, and it is emptied at the next restart.

## 2. Install

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

It ends with `install: installed 11 files into /opt/hmi/data/ro/Plugins/GaugeApp`. The system partition needs about
16 MB free (`df -k /`); a full partition stops the copy with an error. The library goes to the system partition
because `/var/local/data` is mounted `noexec`; the app creates its data folder itself when it first starts.

## 3. Restart

When everything you install is in place:

```sh
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

Repeat steps 1–3 with the new package (e.g. `gauge-app-entrynav2.tar` after the diagnostics): `install.sh` replaces
the old version. The data folder stays, so the settings are kept.

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

**Uninstall:** from the package folder (copied to `/tmp/GaugeApp` as in step 1):

```sh
cd /tmp/GaugeApp && sh uninstall.sh --purge
reboot
```

Without `--purge` the data folder (settings) stays for a later installation. By hand, without the package:

```sh
mount -o remount,rw /
rm -rf /opt/hmi/data/ro/Plugins/GaugeApp
sync
mount -o remount,ro /
rm -rf /var/local/data/GaugeApp
reboot
```

## Troubleshooting

| What you see | What to do |
|---|---|
| No GAUGE APP row in ConnectedDrive | Check that `install.sh` ended with `installed 11 files` and that the head unit was restarted afterwards. Then look at the log: if it is empty, iDrive did not load the library. |
| iDrive restarts several times right after starting | The crash-loop guard switches the app off after 3 iDrive restarts within 2 minutes of loading it, and iDrive carries on without it. After checking the log: `rm -f /var/local/data/GaugeApp/app-guard`, restart. |
| The GAUGE APP screen is empty | Look for the line `GaugeApp_frames.bin: … frames` in the log – `cannot read …GaugeApp_frames.bin` means the file was not copied (run `install.sh` again). Then send the log and a photo. |
| Part of the screen is empty, the rest works | iDrive shows at most about 60 images in a state. Send a photo – it shows from which element on they are missing. |
| `--` everywhere | The car sends no data to the app: after 25 s the log shows `no CDS value arrived…`. Send the log. |
| The system was left writable | `mount -o remount,ro /` or restart the head unit. |
| The iDrive screen does not respond | Hold the iDrive power button for about 30 s to restart the head unit. |
