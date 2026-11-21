# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Build image for the EntryNav2 version: armhf cross GCC against eglibc 2.15, the C library of the EntryNav2 head unit.
# entry-aad's own image (FROM ubuntu:12.10, GCC 4.7) no longer builds: current Docker refuses its schema-1 manifest.
# Ubuntu 12.04 ships the same eglibc 2.15 (GCC 4.6 armhf), which is what matters for the symbols the library links.
#   docker build -t gauge-entrynav2-tc toolchain     (the name toolchain/tc-entrynav2.sh runs)
FROM ubuntu:12.04
RUN sed -i -e 's#http://[a-z.]*ubuntu.com#http://old-releases.ubuntu.com#g' /etc/apt/sources.list \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --force-yes \
      gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf binutils-arm-linux-gnueabihf make file \
 && apt-get clean
WORKDIR /work
