#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# The EntryNav2 package of one screen resolution: dist/EntryNav2/<resolution>/gauge-app-entrynav2.tar. The library is
# the same for every resolution; the XML, the frame packs and the two zips come from the project folder (1280x480,
# committed) or gen/<resolution> (python3 make_db.py --all, or make gen). The archive mirrors the car's file system:
# unpack it in /tmp on the car and copy opt/ over / (docs/EntryEvo_Installation.md).
#   pack-entrynav2.sh <libGaugeApp.so> <resolution>
set -eu
lib=$1
res=$2
plugin=opt/hmi/data/ro/Plugins/GaugeApp
if [ "$res" = "1280x480" ]; then data=.; else data=gen/$res; fi
for f in GaugeApp.xml GaugeApp_ALL_Texts.zip GaugeApp_ALL_Images.zip GaugeApp_frames.bin GaugeApp_frames_s.bin; do
    [ -f "$data/$f" ] || { echo "$data/$f is missing: run python3 make_db.py --all (or make gen) first"; exit 1; }
done
stage=build/entrynav2/stage-$res
out=dist/EntryNav2/$res
rm -rf "$stage"
mkdir -p "$stage/$plugin" "$out"
cp "$lib" GaugeApp.manifest "$data/GaugeApp.xml" "$data/GaugeApp_ALL_Texts.zip" "$data/GaugeApp_ALL_Images.zip" \
    "$data"/GaugeApp_frames*.bin "$stage/$plugin/"
chmod 755 "$stage/$plugin/libGaugeApp.so"
(cd "$stage" && md5sum $plugin/* > MD5SUMS)
tar -cf "$out/gauge-app-entrynav2.tar" -C "$stage" MD5SUMS opt
echo "[DONE] $out/gauge-app-entrynav2.tar ($(wc -c < "$out/gauge-app-entrynav2.tar") bytes)"
