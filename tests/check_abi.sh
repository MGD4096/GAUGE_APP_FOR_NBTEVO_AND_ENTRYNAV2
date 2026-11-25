#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Every bmw:: symbol the plugin imports must be exported by the framework libraries of each head unit. The host build
# of the plugin has the same (Itanium) mangled names as the ARM builds, so its imports are compared with nm -D of the
# cars' libAppFramework.A.so / libCoreFramework.A.so. A folder without the libraries (they are BMW's files, not in git)
# is skipped with a note.
#   check_abi.sh <plugin.so> <lib folder>...
set -eu
plugin=$1
shift
imports=$(nm -D -u "$plugin" | awk '{print $NF}' | grep '^_ZN3bmw' | sort -u)
[ -n "$imports" ] || { echo "check_abi: no bmw:: imports in $plugin"; exit 1; }
fail=0
for dir in "$@"; do
    if [ ! -f "$dir/libAppFramework.A.so" ] || [ ! -f "$dir/libCoreFramework.A.so" ]; then
        echo "check_abi: $dir has no framework libraries - skipped"
        continue
    fi
    exports=$(nm -D --defined-only "$dir/libAppFramework.A.so" "$dir/libCoreFramework.A.so" | awk '{print $NF}')
    for sym in $imports; do
        if ! printf '%s\n' "$exports" | grep -qx "$sym"; then
            echo "check_abi: $dir does not export $(echo "$sym" | c++filt) ($sym)"
            fail=1
        fi
    done
    [ $fail -ne 0 ] || echo "check_abi: all $(echo "$imports" | wc -l) bmw:: imports exported by $dir"
done
exit $fail
