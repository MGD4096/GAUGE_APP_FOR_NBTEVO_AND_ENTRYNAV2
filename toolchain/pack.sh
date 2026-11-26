#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# One installable package: <out>/GaugeApp/ with the plugin (library, manifest, XML, both zips, the frame packs or the
# diagnostic pictures), package/install.sh, package/uninstall.sh and FILES (size and name of every plugin file, which
# install.sh checks), and optionally the same folder as <out>/<tar> (tar -xf in /tmp gives /tmp/GaugeApp).
#   pack.sh <libGaugeApp.so> <data folder> <out folder> [<tar name>]
# The data folder is plugin/ (1280x480), gen/<resolution> or diag (make_db.py --diag-out).
set -eu
lib=$1
data=$2
out=$3
tarname=${4:-}
app=GaugeApp
for f in GaugeApp.xml GaugeApp_ALL_Texts.zip GaugeApp_ALL_Images.zip; do
    [ -f "$data/$f" ] || { echo "$data/$f is missing: run python3 make_db.py --all (or make gen) first"; exit 1; }
done
pictures=$(ls "$data"/GaugeApp_frames*.bin "$data"/*.png 2>/dev/null || true)
[ -n "$pictures" ] || { echo "$data has no frame packs or pictures"; exit 1; }
dir=$out/$app
rm -rf "$dir"
mkdir -p "$dir"
cp "$lib" plugin/GaugeApp.manifest "$data/GaugeApp.xml" "$data/GaugeApp_ALL_Texts.zip" "$data/GaugeApp_ALL_Images.zip" \
    $pictures "$dir/"
chmod 755 "$dir/libGaugeApp.so"
files=$(cd "$dir" && ls)                            # the plugin files only (before FILES and the scripts exist)
(cd "$dir" && for f in $files; do echo "$(wc -c < "$f" | tr -d ' ') $f"; done) > "$dir/FILES"
cp package/install.sh package/uninstall.sh "$dir/"
chmod 755 "$dir/install.sh" "$dir/uninstall.sh"
if [ -n "$tarname" ]; then
    tar -cf "$out/$tarname" -C "$out" "$app"
    echo "[DONE] $dir/ and $out/$tarname ($(wc -c < "$out/$tarname") bytes, $(wc -l < "$dir/FILES") plugin files)"
else
    echo "[DONE] $dir/ ($(wc -l < "$dir/FILES") plugin files)"
fi
