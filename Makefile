# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Engine data PluginApp for two BMW head units, from the same sources:
#   NBT Evo    QNX Neutrino 6.5, ARMv7 little endian, GNU libstdc++ variant to match HmiMain3D (qcc)
#   EntryNav2  EntryEVO, Linux ARMv7 hard-float, glibc 2.15 (arm-linux-gnueabihf-g++ built against eglibc 2.15)
#
#   make                 NBT Evo: libGaugeApp.so and the text/image DBs          (needs qcc, see below)
#   make entrynav2       EntryNav2: build/entrynav2/libGaugeApp.so               (needs the armhf GCC 4.7, see below)
#   make entrynav2-dist  EntryNav2: dist/gauge-app-entrynav2.tar, ready to copy to the car
#   make db              only the DBs (python3 + Pillow); the same files serve both head units
#   make check           host tests with the Linux g++ (no QNX / ARM compiler needed), both targets
#   make clean
#
# NBT Evo: RHMI_LIBDIR must hold copies of the car's libAppFramework.A.so and libCoreFramework.A.so (opt/hmi/ID5/lib in
# a firmware dump). They are BMW's files and are not part of this project; copy them from your own head unit.
#
# EntryNav2: EN2_LIBDIR must hold the EntryNav2 copies of the same two libraries (/opt/hmi/lib on that head unit;
# NOT the NBT Evo ones from ./lib); lib/Entry_Evo_libs is used when it holds them. The compiler must match the car's
# glibc 2.15 (a newer armhf GCC/glibc links e.g. clock_gettime@GLIBC_2.17, which the car lacks): use the image of
# toolchain/Dockerfile (Ubuntu 12.04, armhf GCC 4.6, eglibc 2.15):
#   docker build -t gauge-entrynav2-tc toolchain
#   bash toolchain/tc-entrynav2.sh make entrynav2-dist

QCC ?= qcc
RHMI_LIBDIR ?= ./lib
RHMI_LIBS = $(wildcard $(RHMI_LIBDIR)/libAppFramework.A.so $(RHMI_LIBDIR)/libCoreFramework.A.so)

PLUGIN_CXX      = $(QCC) -Vgcc_ntoarmv7le_gpp
PLUGIN_CXXFLAGS = -O2 -Wall -D_QNX_SOURCE -march=armv7-a -mfpu=vfpv3 -mfloat-abi=softfp -fPIC -I./src

# ---- EntryNav2 ----------------------------------------------------------------------------------------------------
EN2_CXX      ?= arm-linux-gnueabihf-g++
SYSROOT      ?= /sysroot
# Copies of the car's /opt/hmi/lib in lib/Entry_Evo_libs (preferred when present), else the sysroot. Their own
# dependencies (libhmibase, libdlt, boost) are not needed to link: HmiMain3D has them loaded already.
EN2_LIBDIR   ?= $(if $(wildcard lib/Entry_Evo_libs/libAppFramework.A.so),lib/Entry_Evo_libs,$(SYSROOT)/opt/hmi/lib)
EN2_LIBS      = $(wildcard $(EN2_LIBDIR)/libAppFramework.A.so $(EN2_LIBDIR)/libCoreFramework.A.so)
# Flags of entry-aad's hmiapp (car-verified): ARMv7 + NEON hard-float, position independent, only pluginAppInfo exported.
EN2_CXXFLAGS  = -std=gnu++98 -O2 -Wall -Wextra -march=armv7-a -mfpu=neon -mfloat-abi=hard -fPIC \
                -fvisibility=hidden -fvisibility-inlines-hidden -DGAUGE_ENTRYNAV2 -I./src
EN2_LDFLAGS   = -Wl,--allow-shlib-undefined -L$(EN2_LIBDIR) -Wl,-rpath-link,$(EN2_LIBDIR) \
                -Wl,-rpath-link,$(SYSROOT)/usr/lib:$(SYSROOT)/lib:$(SYSROOT)/usr/local/lib
EN2_OUT       = build/entrynav2
EN2_PLUGIN    = opt/hmi/data/ro/Plugins/GaugeApp
EN2_STAGE     = dist/entrynav2

.PHONY: all lib db check clean entrynav2 entrynav2-dist
all: lib db

lib: libGaugeApp.so

libGaugeApp.so: src/engine_data.cpp src/cds_values.hpp
	@test -n "$(RHMI_LIBS)" || { echo "put libAppFramework.A.so and libCoreFramework.A.so from the car into $(RHMI_LIBDIR) (or set RHMI_LIBDIR)"; exit 1; }
	@echo [BUILD] $@
	$(PLUGIN_CXX) $(PLUGIN_CXXFLAGS) -shared -Wl,-soname,libGaugeApp.so -o $@ src/engine_data.cpp $(RHMI_LIBS) -Wl,--allow-shlib-undefined -lang-c++
	@echo [DONE] $@ - install with GaugeApp.manifest, GaugeApp.xml and the two zips into Plugins/GaugeApp

entrynav2: $(EN2_OUT)/libGaugeApp.so

$(EN2_OUT)/libGaugeApp.so: src/engine_data.cpp src/cds_values.hpp
	@test -n "$(EN2_LIBS)" || { echo "put the EntryNav2 libAppFramework.A.so and libCoreFramework.A.so (/opt/hmi/lib of the car) into $(EN2_LIBDIR) (or set EN2_LIBDIR / SYSROOT)"; exit 1; }
	@mkdir -p $(EN2_OUT)
	@echo [BUILD] $@ for EntryNav2
	$(EN2_CXX) $(EN2_CXXFLAGS) -shared -Wl,-soname,libGaugeApp.so -o $@ src/engine_data.cpp \
	    $(EN2_LDFLAGS) -l:libAppFramework.A.so -l:libCoreFramework.A.so -lpthread -ldl
	@echo [DONE] $@ - make entrynav2-dist packs it with the manifest, the XML and the two zips

# The archive mirrors the car's file system: unpack it in /tmp on the car and copy opt/ over / (README, EntryNav2).
entrynav2-dist: $(EN2_OUT)/libGaugeApp.so GaugeApp_ALL_Texts.zip GaugeApp_ALL_Images.zip
	rm -rf $(EN2_STAGE)
	mkdir -p $(EN2_STAGE)/$(EN2_PLUGIN)
	cp $(EN2_OUT)/libGaugeApp.so GaugeApp.manifest GaugeApp.xml GaugeApp_ALL_Texts.zip GaugeApp_ALL_Images.zip \
	    $(EN2_STAGE)/$(EN2_PLUGIN)/
	chmod 755 $(EN2_STAGE)/$(EN2_PLUGIN)/libGaugeApp.so
	cd $(EN2_STAGE) && md5sum $(EN2_PLUGIN)/* > MD5SUMS
	tar -cf $(CURDIR)/dist/gauge-app-entrynav2.tar -C $(EN2_STAGE) MD5SUMS opt
	@echo [DONE] dist/gauge-app-entrynav2.tar

GaugeApp_ALL_Texts.zip GaugeApp_ALL_Images.zip:
	python3 make_db.py

db:
	python3 make_db.py

check:
	$(MAKE) -C tests check

clean:
	rm -f libGaugeApp.so GaugeApp_ALL_Texts.zip GaugeApp_ALL_Images.zip
	rm -rf build dist
	$(MAKE) -C tests clean
