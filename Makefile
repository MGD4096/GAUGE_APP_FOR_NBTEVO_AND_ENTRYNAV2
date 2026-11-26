# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Engine data PluginApp for two BMW head units, from the same sources:
#   NBT Evo    QNX Neutrino 6.5, ARMv7 little endian, GNU libstdc++ variant to match HmiMain3D (qcc)
#   EntryNav2  EntryEVO, Linux ARMv7 hard-float, glibc 2.15 (arm-linux-gnueabihf-g++ built against eglibc 2.15)
#
#   make                 NBT Evo: libGaugeApp.so and the text/image DBs          (needs qcc, see below)
#   make entrynav2       EntryNav2: build/entrynav2/libGaugeApp.so               (needs the armhf GCC 4.7, see below)
#   make entrynav2-dist  EntryNav2: dist/EntryNav2/$(RES)/gauge-app-entrynav2.tar (RES=1280x480 by default)
#   make entrynav2-dist-all  the same for every resolution (800x480, 1280x480, 1440x540)
#   make db              plugin/GaugeApp.xml, src/gauge_ids.hpp and the image / text DBs (python3 + Pillow, make_db.py) for
#                        1280x480; the same files serve both head units. They are kept in git, so a build needs no
#                        Pillow.
#   make gen             the other resolutions into gen/<resolution> (python3 + Pillow; only when make_db.py or
#                        gaugegen/ changed since). Run it outside Docker (the toolchain image has no Pillow).
#   make check           host tests with the Linux g++ (no QNX / ARM compiler needed), both targets
#   make clean           build outputs only (not the generated files kept in git)
#
# NBT Evo: RHMI_LIBDIR must hold copies of the car's libAppFramework.A.so and libCoreFramework.A.so (opt/hmi/ID5/lib in
# a firmware dump; lib/NBT_evo_libs by default). They are BMW's files and are not part of this project.
#
# EntryNav2: EN2_LIBDIR must hold the EntryNav2 copies of the same two libraries (/opt/hmi/lib on that head unit;
# NOT the NBT Evo ones from ./lib); lib/Entry_Evo_libs is used when it holds them. The compiler must match the car's
# glibc 2.15 (a newer armhf GCC/glibc links e.g. clock_gettime@GLIBC_2.17, which the car lacks): use the image of
# toolchain/Dockerfile (Ubuntu 12.04, armhf GCC 4.6, eglibc 2.15):
#   docker build -t gauge-entrynav2-tc toolchain
#   bash toolchain/tc-entrynav2.sh make entrynav2-dist

QCC ?= qcc
RHMI_LIBDIR ?= ./lib/NBT_evo_libs
RHMI_LIBS = $(wildcard $(RHMI_LIBDIR)/libAppFramework.A.so $(RHMI_LIBDIR)/libCoreFramework.A.so)

PLUGIN_CXX      = $(QCC) -Vgcc_ntoarmv7le_gpp
# -Wc,<option> hands an option to qcc's gcc 4.4 unchanged: the same language level and warnings as the EntryNav2 build.
PLUGIN_CXXFLAGS = -O2 -Wall -Wc,-Wextra -Wc,-std=gnu++98 -D_QNX_SOURCE -march=armv7-a -mfpu=vfpv3 -mfloat-abi=softfp \
                  -fPIC -fvisibility=hidden -I./src

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
# Screen resolutions (gaugegen/layout.py SCREEN_PRESETS). 1280x480 uses the committed files in the project folder,
# the others gen/<resolution>. The library is the same for all of them.
RESOLUTIONS   = 800x480 1280x480 1440x540
RES          ?= 1280x480
GEN_RES       = $(filter-out 1280x480,$(RESOLUTIONS))

# The plugin's modules (src/app.hpp lists what each one does) and the headers they share.
PLUGIN_SRC = src/engine_data.cpp src/cds.cpp src/render.cpp src/frames.cpp src/storage.cpp src/log.cpp
SRC = $(PLUGIN_SRC) $(wildcard src/*.hpp)

.PHONY: all lib db gen check clean entrynav2 entrynav2-dist entrynav2-dist-all entrynav2-diag-dist
all: lib

lib: libGaugeApp.so

libGaugeApp.so: $(SRC)
	@test -n "$(RHMI_LIBS)" || { echo "put libAppFramework.A.so and libCoreFramework.A.so from the car into $(RHMI_LIBDIR) (or set RHMI_LIBDIR)"; exit 1; }
	@echo [BUILD] $@
	$(PLUGIN_CXX) $(PLUGIN_CXXFLAGS) -shared -Wl,-soname,libGaugeApp.so -o $@ $(PLUGIN_SRC) $(RHMI_LIBS) -Wl,--allow-shlib-undefined -lang-c++
	@echo [DONE] $@ - install with plugin/ (manifest, XML, zips, frame packs) into Plugins/GaugeApp

entrynav2: $(EN2_OUT)/libGaugeApp.so

$(EN2_OUT)/libGaugeApp.so: $(SRC)
	@test -n "$(EN2_LIBS)" || { echo "put the EntryNav2 libAppFramework.A.so and libCoreFramework.A.so (/opt/hmi/lib of the car) into $(EN2_LIBDIR) (or set EN2_LIBDIR / SYSROOT)"; exit 1; }
	@mkdir -p $(EN2_OUT)
	@echo [BUILD] $@ for EntryNav2
	$(EN2_CXX) $(EN2_CXXFLAGS) -shared -Wl,-soname,libGaugeApp.so -o $@ $(PLUGIN_SRC) \
	    $(EN2_LDFLAGS) -l:libAppFramework.A.so -l:libCoreFramework.A.so -lpthread -ldl
	@echo [DONE] $@ - make entrynav2-dist packs it with the manifest, the XML and the two zips

# dist/EntryNav2/<resolution>/: the package folder GaugeApp/ (plugin, install.sh, uninstall.sh, FILES) and the same as
# gauge-app-entrynav2.tar (toolchain/pack.sh). On the car: tar -xf in /tmp, then cd /tmp/GaugeApp && sh install.sh
# (docs/EntryEvo_Installation.md). 1280x480 comes from plugin/, the others from gen/<resolution>.
res_data = $(if $(filter 1280x480,$(1)),plugin,gen/$(1))
entrynav2-dist: $(EN2_OUT)/libGaugeApp.so
	sh toolchain/pack.sh $(EN2_OUT)/libGaugeApp.so $(call res_data,$(RES)) dist/EntryNav2/$(RES) gauge-app-entrynav2.tar

entrynav2-dist-all: $(EN2_OUT)/libGaugeApp.so
	set -e; for r in $(RESOLUTIONS); do \
	    if [ $$r = 1280x480 ]; then d=plugin; else d=gen/$$r; fi; \
	    sh toolchain/pack.sh $(EN2_OUT)/libGaugeApp.so $$d dist/EntryNav2/$$r gauge-app-entrynav2.tar; \
	done

# Diagnostic package: the same library with the test pages of `python3 make_db.py --diag-out diag` (run that first,
# it needs Pillow): XML, a 3-image DB, the texts and the test pictures. Installed the same way (install.sh).
EN2_DIAG = diag
entrynav2-diag-dist: $(EN2_OUT)/libGaugeApp.so
	@test -f $(EN2_DIAG)/GaugeApp.xml || { echo "run python3 make_db.py --diag-out $(EN2_DIAG) first"; exit 1; }
	sh toolchain/pack.sh $(EN2_OUT)/libGaugeApp.so $(EN2_DIAG) dist/EntryNav2/diag gauge-app-entrynav2-diag.tar

db:
	python3 make_db.py

GEN_SRC = make_db.py $(wildcard gaugegen/*.py)
gen: $(foreach r,$(GEN_RES),gen/$(r)/GaugeApp_frames.bin)
gen/%/GaugeApp_frames.bin: $(GEN_SRC)
	python3 make_db.py --screen $*

check:
	$(MAKE) -C tests check

clean:
	rm -f libGaugeApp.so
	rm -rf build dist
	$(MAKE) -C tests clean
