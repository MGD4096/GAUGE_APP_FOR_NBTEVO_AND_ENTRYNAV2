#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Host test of the package and its scripts: toolchain/pack.sh builds a package folder, then package/install.sh and
# package/uninstall.sh run against a fake root folder (GA_ROOT) as QNX (NBT Evo) and as Linux (EntryNav2).
#   install_test.sh <work folder>          (run from the project folder)
set -u
mkdir -p "$1"
work=$(cd "$1" && pwd)
fail=0
check() { if eval "$2"; then :; else echo "FAIL install_test: $1"; fail=1; fi; }

rm -rf "$work"
mkdir -p "$work/lib"
printf 'fake library' > "$work/lib/libGaugeApp.so"
sh toolchain/pack.sh "$work/lib/libGaugeApp.so" plugin "$work/out" test.tar > /dev/null || { echo "FAIL: pack.sh"; exit 1; }
pkg=$work/out/GaugeApp
check "the package has FILES, install.sh, uninstall.sh" '[ -f $pkg/FILES ] && [ -x $pkg/install.sh ] && [ -x $pkg/uninstall.sh ]'
check "FILES lists the 11 plugin files" '[ $(wc -l < $pkg/FILES) -eq 11 ]'
check "the tar unpacks to GaugeApp/" 'tar -tf $work/out/test.tar | grep -qx "GaugeApp/install.sh"'

for sys in Linux QNX; do
    root=$work/root-$sys
    if [ $sys = QNX ]; then hmi=$root/opt/hmi/ID5; data=$root/var/opt/gaugeapp; else hmi=$root/opt/hmi; data=$root/var/local/data/GaugeApp; fi
    dest=$hmi/data/ro/Plugins/GaugeApp
    # not the head unit: nothing installed
    mkdir -p "$root"
    GA_ROOT=$root GA_SYSTEM=$sys sh "$pkg/install.sh" > "$work/log" 2>&1
    check "$sys: refuses without $hmi/lib" '[ $? -ne 0 ] && [ ! -d $dest ] && grep -q "lib is missing" $work/log'
    mkdir -p "$hmi/lib" "$data"
    # an old version, the crash guard tripped, a stray file
    mkdir -p "$dest" && echo old > "$dest/libGaugeApp.so" && echo x > "$dest/stale.bin"
    printf '1\n2\n3\n' > "$data/app-guard"
    echo "color=1" > "$data/settings.txt"
    (cd /tmp && GA_ROOT=$root GA_SYSTEM=$sys sh "$pkg/install.sh") > "$work/log" 2>&1
    check "$sys: installs (run from another folder)" '[ $? -eq 0 ]'
    check "$sys: every plugin file copied, same size" 'while read s n; do [ "$(wc -c < $dest/$n | tr -d " ")" = "$s" ] || exit 1; done < $pkg/FILES'
    check "$sys: the library is executable" '[ -x $dest/libGaugeApp.so ]'
    check "$sys: old files removed, scripts not copied" '[ ! -f $dest/stale.bin ] && [ ! -f $dest/install.sh ] && [ ! -f $dest/FILES ]'
    check "$sys: crash guard reset, settings kept" '[ ! -f $data/app-guard ] && [ -f $data/settings.txt ]'
    check "$sys: no restart, says to restart" 'grep -q "nothing was restarted" $work/log && ! grep -q -E "^(reboot|shutdown)" $pkg/install.sh'
    # a damaged package: nothing touched
    cp -R "$pkg" "$work/bad-$sys"
    printf 'x' >> "$work/bad-$sys/GaugeApp.xml"
    GA_ROOT=$root GA_SYSTEM=$sys sh "$work/bad-$sys/install.sh" > "$work/log" 2>&1
    check "$sys: a damaged package is refused" '[ $? -ne 0 ] && grep -q "GaugeApp.xml has" $work/log'
    check "$sys: and the installed app stays" 'cmp -s $dest/GaugeApp.xml $pkg/GaugeApp.xml'
    # FILES written on Windows (CRLF, build_nbt.bat)
    tr -d '\r' < "$pkg/FILES" | sed 's/$/\r/' > "$work/bad-$sys/FILES"
    cp "$pkg/GaugeApp.xml" "$work/bad-$sys/GaugeApp.xml"
    GA_ROOT=$root GA_SYSTEM=$sys sh "$work/bad-$sys/install.sh" > "$work/log" 2>&1
    check "$sys: FILES with CRLF line ends" '[ $? -eq 0 ]'
    # uninstall: the plugin goes, the data stays; --purge removes the data too
    GA_ROOT=$root GA_SYSTEM=$sys sh "$pkg/uninstall.sh" > "$work/log" 2>&1
    check "$sys: uninstall removes the plugin, keeps the data" '[ ! -d $dest ] && [ -f $data/settings.txt ]'
    GA_ROOT=$root GA_SYSTEM=$sys sh "$pkg/uninstall.sh" --purge > "$work/log" 2>&1
    check "$sys: uninstall --purge removes the data" '[ ! -d $data ]'
done
# NBT Evo's hu-omap: no dirname, tr, wc, grep, sync (car-verified) - only these tools on the PATH, run as
# "cd /tmp/GaugeApp && sh install.sh" (no folder in $0), FILES with CRLF
sh_bin=$(command -v sh)
mkdir -p "$work/bin"
for t in ls cp rm mkdir chmod; do ln -s "$(command -v $t)" "$work/bin/$t"; done
root=$work/root-min
mkdir -p "$root/opt/hmi/ID5/lib"
sed 's/$/\r/' "$pkg/FILES" > "$work/FILES.crlf" && cp "$work/FILES.crlf" "$pkg/FILES"
(cd "$pkg" && PATH=$work/bin GA_ROOT=$root GA_SYSTEM=QNX "$sh_bin" install.sh) > "$work/log" 2>&1
check "QNX with only ls/cp/rm/mkdir/chmod: installs" '[ $? -eq 0 ] && ! grep -q "cannot execute\|not found" $work/log'
check "QNX with only ls/cp/rm/mkdir/chmod: every file there" '[ $(ls $root/opt/hmi/ID5/data/ro/Plugins/GaugeApp | wc -l) -eq 11 ]'
rm "$work/bin/chmod"
(cd "$pkg" && PATH=$work/bin GA_ROOT=$root GA_SYSTEM=QNX "$sh_bin" install.sh) > "$work/log" 2>&1
check "a missing tool is named before anything is written" '[ $? -ne 0 ] && grep -q "no .chmod. command" $work/log'
(cd "$pkg" && PATH=$work/bin GA_ROOT=$root GA_SYSTEM=QNX "$sh_bin" uninstall.sh) > "$work/log" 2>&1
check "uninstall with the same tools" '[ $? -eq 0 ] && [ ! -d $root/opt/hmi/ID5/data/ro/Plugins/GaugeApp ]'

GA_ROOT=$work/root-Linux GA_SYSTEM=Darwin sh "$pkg/install.sh" > "$work/log" 2>&1
check "an unknown system is refused" '[ $? -ne 0 ] && grep -q "unknown system" $work/log'

[ $fail -eq 0 ] && echo "install_test OK"
exit $fail
