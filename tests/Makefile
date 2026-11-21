# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Host tests (Linux g++). From the project root: `make check`.
#   test_cds_values   parsing, derived values, maxima and image selection (src/cds_values.hpp, src/gauge_view.hpp)
#   app_host_test     host build of src/engine_data.cpp, loaded with dlopen against fake_appframework.cpp; run on the
#                     NBT Evo build and on the EntryNav2 build (-DGAUGE_ENTRYNAV2), each with its data folder moved
#                     into build/; for EntryNav2 also the log and the crash guard (the 4th start without uptime is
#                     refused)
OUT := build
CXX ?= g++
WARN := -Wall -Wextra
NBT_DATA := $(abspath $(OUT))/nbt-data
EN2_DATA := $(abspath $(OUT))/entrynav2-data
SRC := ../src/engine_data.cpp ../src/cds_values.hpp ../src/gauge_view.hpp ../src/gauge_ids.hpp

.PHONY: check clean
check: $(OUT)/test_cds_values $(OUT)/app_host_test $(OUT)/libGaugeApp.so $(OUT)/libGaugeApp-entrynav2.so
	$(OUT)/test_cds_values
	rm -rf $(NBT_DATA)
	$(OUT)/app_host_test $(OUT)/libGaugeApp.so $(NBT_DATA)
	rm -rf $(EN2_DATA)
	$(OUT)/app_host_test $(OUT)/libGaugeApp-entrynav2.so $(EN2_DATA)
	test -s $(EN2_DATA)/gauge-app.log
	grep -q "images written" $(EN2_DATA)/gauge-app.log
	rm -f $(EN2_DATA)/max.txt
	$(OUT)/app_host_test $(OUT)/libGaugeApp-entrynav2.so $(EN2_DATA) > /dev/null
	rm -f $(EN2_DATA)/max.txt
	$(OUT)/app_host_test $(OUT)/libGaugeApp-entrynav2.so $(EN2_DATA) > /dev/null
	rm -f $(EN2_DATA)/max.txt
	! $(OUT)/app_host_test $(OUT)/libGaugeApp-entrynav2.so $(EN2_DATA) > /dev/null
	grep -q "crash guard: the HMI restarted 3 times" $(EN2_DATA)/gauge-app.log
	@echo "entrynav2 crash guard OK"

$(OUT):
	mkdir -p $(OUT)

# The app is C++98 (QNX SDP 6.5 / GCC 4.4); keep the host build in the same dialect.
$(OUT)/test_cds_values: test_cds_values.cpp ../src/cds_values.hpp ../src/gauge_view.hpp ../src/gauge_ids.hpp | $(OUT)
	$(CXX) -std=gnu++98 $(WARN) -I../src -o $@ test_cds_values.cpp

$(OUT)/libGaugeApp.so: $(SRC) | $(OUT)
	$(CXX) -std=gnu++98 $(WARN) -fPIC -shared -I../src -DGAUGE_DATA_DIR='"$(NBT_DATA)"' -DGAUGE_PLUGIN_DIR='"$(NBT_DATA)"' \
	    -o $@ ../src/engine_data.cpp -ldl -lpthread

$(OUT)/libGaugeApp-entrynav2.so: $(SRC) | $(OUT)
	$(CXX) -std=gnu++98 $(WARN) -fPIC -shared -I../src -DGAUGE_ENTRYNAV2 -DGAUGE_DATA_DIR='"$(EN2_DATA)"' \
	    -DGAUGE_PLUGIN_DIR='"$(EN2_DATA)"' \
	    -o $@ ../src/engine_data.cpp -ldl -lpthread

# -rdynamic: the library looks up bmw::Runnable's vtable with dlsym(RTLD_DEFAULT) and needs the fake's symbols.
$(OUT)/app_host_test: app_host_test.cpp fake_appframework.cpp fake_appframework.hpp ../src/gauge_view.hpp | $(OUT)
	$(CXX) -std=gnu++11 $(WARN) -rdynamic -I../src -o $@ app_host_test.cpp fake_appframework.cpp -ldl

clean:
	rm -rf $(OUT)
