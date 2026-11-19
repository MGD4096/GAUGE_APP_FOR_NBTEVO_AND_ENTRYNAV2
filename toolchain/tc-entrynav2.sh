#!/bin/bash
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Runs a command in the EntryNav2 build image (toolchain/Dockerfile: armhf GCC against eglibc 2.15), with this
# project on /work. The BMW libraries come from lib/Entry_Evo_libs; a copy of the car's system is mounted on /sysroot
# (read-only) only if HU_ROOTFS (default ~/entrynav2/rootfs) exists. Neither goes into git.
# The image is built once: docker build -t gauge-entrynav2-tc toolchain
#   bash toolchain/tc-entrynav2.sh make entrynav2-dist
project="$(cd "$(dirname "$0")/.." && pwd)"
rootfs="${HU_ROOTFS:-$HOME/entrynav2/rootfs}"
sysroot=()
if [ -d "$rootfs" ]; then
    sysroot=(-v "$rootfs:/sysroot:ro")
fi
exec docker run --rm -u "$(id -u):$(id -g)" -v "$project:/work" "${sysroot[@]}" -w /work gauge-entrynav2-tc "$@"
