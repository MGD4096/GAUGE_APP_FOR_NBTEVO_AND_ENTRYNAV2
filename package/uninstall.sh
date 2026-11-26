#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Removes a plugin app from the head unit (docs/Install_Standard.md; this copy: GaugeApp): NBT Evo (QNX, run it
# on hu-omap) or EntryNav2 (Linux).
#
#     sh uninstall.sh            the app's plugin folder; its data (settings, maxima) stays
#     sh uninstall.sh --purge    the data folder too
#
# It does NOT restart anything: restart the head unit yourself afterwards (iDrive keeps a loaded plugin until then).
# GA_ROOT / GA_SYSTEM are for the host tests (tests/install_test.sh).
# ---- the app: the only lines another app changes (docs/Install_Standard.md) ---------------------------------------
APP=GaugeApp                                  # plugin folder name = package folder name = /tmp/<APP>
LIB=libGaugeApp.so                            # the plugin library (made executable, checked by the EntryNav2 loader)
DATA_QNX=/var/opt/gaugeapp                    # the app's data folder on NBT Evo (kept; --purge removes it)
DATA_LINUX=/var/local/data/GaugeApp           # ... on EntryNav2
GUARD=app-guard                               # crash guard file in the data folder, removed by install ("" = none)
# --------------------------------------------------------------------------------------------------------------------
ROOT=${GA_ROOT:-}
SYSTEM=${GA_SYSTEM:-$(uname -s)}

say() { echo "uninstall: $*"; }
die() { echo "uninstall: ERROR: $*" >&2; exit 1; }

case "$SYSTEM" in
QNX)
    HMI=/opt/hmi/ID5
    DATA=$DATA_QNX
    rw() { /bin/mount -u -o rw /fs/sda0; }
    ro() { /bin/mount -u -o ro /fs/sda0; }
    ;;
Linux)
    HMI=/opt/hmi
    DATA=$DATA_LINUX
    rw() { mount -o remount,rw /; }
    ro() { mount -o remount,ro /; }
    ;;
*)
    die "unknown system '$SYSTEM' (NBT Evo = QNX, EntryNav2 = Linux)"
    ;;
esac
if [ -n "$ROOT" ]; then
    rw() { :; }
    ro() { :; }
fi
DEST=$ROOT$HMI/data/ro/Plugins/$APP
case "${1:-}" in
""|--purge) ;;
*) die "unknown option '$1' (only --purge)" ;;
esac

if [ -d "$DEST" ]; then
    rw || die "cannot make the system partition writable"
    trap 'ro' 0
    rm -rf "$DEST" || die "cannot remove $DEST"
    sync 2>/dev/null
    trap - 0
    ro || say "could not make the system partition read-only again: the restart will"
    say "removed $HMI/data/ro/Plugins/$APP"
else
    say "$HMI/data/ro/Plugins/$APP is not there"
fi
if [ "${1:-}" = --purge ]; then
    rm -rf "$ROOT$DATA" && say "removed the data folder $DATA"
else
    say "the data folder $DATA stays (sh uninstall.sh --purge removes it)"
fi
say "restart the head unit when you are done"
