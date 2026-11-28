#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Installs a plugin app on the head unit (the install standard of docs/Install_Standard.md; this copy: GaugeApp):
# NBT Evo (QNX, run it on hu-omap) or EntryNav2 (Linux). The same script and the same package folder for both; only
# getting the folder onto the unit differs. Run it from the package folder, wherever that is (/tmp/GaugeApp, or a USB
# stick):
#
#     cd /tmp/GaugeApp && sh install.sh
#
# It checks the package (FILES: the size and name of every file of the plugin), makes the system partition writable,
# copies the plugin into the HMI's plugin folder, checks the copy and makes the partition read-only again.
# It does NOT restart anything: iDrive loads its plugins only when it starts, so restart the head unit yourself once
# everything you install is in place. The app's data folder (settings, maxima, learned files) is kept.
#
# GA_ROOT (a folder standing in for /) and GA_SYSTEM (QNX / Linux) are for the host tests (tests/install_test.sh).
# ---- the app: the only lines another app changes (docs/Install_Standard.md) ---------------------------------------
APP=GaugeApp                                  # plugin folder name = package folder name = /tmp/<APP>
LIB=libGaugeApp.so                            # the plugin library (made executable, checked by the EntryNav2 loader)
DATA_QNX=/var/opt/gaugeapp                    # the app's data folder on NBT Evo (kept; --purge removes it)
DATA_LINUX=/var/local/data/GaugeApp           # ... on EntryNav2
GUARD=app-guard                               # crash guard file in the data folder, removed by install ("" = none)
# --------------------------------------------------------------------------------------------------------------------
ROOT=${GA_ROOT:-}
SYSTEM=${GA_SYSTEM:-$(uname -s)}

say() { echo "install: $*"; }
die() { echo "install: ERROR: $*" >&2; exit 1; }

# Only shell built-ins and ls, cp, rm, mkdir, chmod, mount: NBT Evo's hu-omap has no dirname, tr or wc (car-verified).
for tool in ls cp rm mkdir chmod; do
    command -v $tool > /dev/null 2>&1 || die "this unit has no '$tool' command (nothing installed)"
done
case "$0" in
*/*) here=${0%/*} ;;
*) here=. ;;
esac
here=$(cd "$here" && pwd)

# fsize <file>: its size in bytes (field 5 of ls -l), empty when it is not there
fsize() {
    set -- $(ls -l "$1" 2>/dev/null)
    echo "${5:-}"
}

case "$SYSTEM" in
QNX)
    HMI=/opt/hmi/ID5
    DATA=$DATA_QNX
    RESTART="hold the iDrive power button for about 30 s, or switch the car off until the unit shuts down"
    rw() { /bin/mount -u -o rw /fs/sda0; }
    ro() { /bin/mount -u -o ro /fs/sda0; }
    ;;
Linux)
    HMI=/opt/hmi
    DATA=$DATA_LINUX
    RESTART="reboot"
    rw() { mount -o remount,rw /; }
    ro() { mount -o remount,ro /; }
    ;;
*)
    die "unknown system '$SYSTEM' (NBT Evo = QNX, EntryNav2 = Linux)"
    ;;
esac
if [ -n "$ROOT" ]; then                              # host test: no mounts
    rw() { :; }
    ro() { :; }
fi
DEST=$ROOT$HMI/data/ro/Plugins/$APP

if [ ! -d "$ROOT$HMI/lib" ]; then
    [ "$SYSTEM" = QNX ] && die "$HMI/lib is missing: run this on hu-omap (on -f /net/hu-omap/ /bin/sh first)"
    die "$HMI/lib is missing: is this an EntryNav2 head unit?"
fi

# ---- the package: every file of FILES there with its size (FILES may have CRLF line ends: written on Windows) ----
[ -f "$here/FILES" ] || die "$here/FILES is missing: copy the whole $APP folder"
names=""
n=0
while read -r size name rest; do
    case "$name" in *[!A-Za-z0-9._-]) name=${name%?} ;; esac   # a CR at the end (FILES written on Windows)
    [ -n "$name" ] || continue
    [ -f "$here/$name" ] || die "$name is missing from the package: copy the whole $APP folder again"
    got=$(fsize "$here/$name")
    [ "$got" = "$size" ] || die "$name has $got bytes instead of $size: copy the package again"
    names="$names $name"
    n=$((n + 1))
done < "$here/FILES"
case " $names " in *" $LIB "*) ;; *) die "FILES does not list $LIB" ;; esac
say "package OK: $n files"

# ---- EntryNav2: the system's loader checks every library and function the app needs, without running it ----------
if [ "$SYSTEM" = Linux ] && [ -z "$ROOT" ] && [ -x /lib/ld-linux-armhf.so.3 ]; then
    missing=$(LD_TRACE_LOADED_OBJECTS=1 LD_WARN=yes LD_BIND_NOW=yes \
        LD_LIBRARY_PATH=/usr/local/lib:/opt/hmi/lib:/usr/lib:/lib \
        /lib/ld-linux-armhf.so.3 "$here/$LIB" 2>&1 | grep -E 'not found|undefined symbol')
    [ -z "$missing" ] || die "this head unit lacks what the app needs (nothing installed):
$missing"
    say "libraries OK"
fi

# ---- install: the system partition is writable only meanwhile ---------------------------------------------------
rw || die "cannot make the system partition writable"
trap 'ro' 0
mkdir -p "$DEST" || die "cannot create $DEST"
# Deleted, then copied anew: iDrive keeps the old library in memory until it restarts, and a running program's file
# is never overwritten in place.
rm -f "$DEST"/*
for name in $names; do
    cp "$here/$name" "$DEST/$name" || die "cannot copy $name to $DEST (full?)"
done
chmod 755 "$DEST/$LIB" || die "cannot make $LIB executable"
command -v sync > /dev/null 2>&1 && sync
for name in $names; do
    want=$(fsize "$here/$name")
    got=$(fsize "$DEST/$name")
    [ "$got" = "$want" ] || die "$DEST/$name has ${got:-no} bytes instead of $want (full?)"
done
trap - 0
ro || say "could not make the system partition read-only again: the restart will"

# A new version gets a fresh start from the crash guard (GaugeApp on EntryNav2: 3 HMI restarts within 2 min turn the
# app off).
if [ -n "$GUARD" ] && [ -f "$ROOT$DATA/$GUARD" ]; then
    rm -f "$ROOT$DATA/$GUARD" && say "crash guard reset ($DATA/$GUARD removed)"
fi
[ -f "$ROOT$DATA/app.disable" ] && say "note: $DATA/app.disable exists - the app stays off until you delete it"

say "installed $n files into $HMI/data/ro/Plugins/$APP"
say "nothing was restarted: once everything you install is in place, restart the head unit to load it"
say "  ($RESTART)"
