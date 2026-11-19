# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Host tests (Linux g++). From the project root: `make check`.
#   test_cds_values   parsing and display rows (src/cds_values.hpp)
#   app_host_test     host build of src/engine_data.cpp, loaded with dlopen against fake_appframework.cpp; run on the
#                     NBT Evo build and on the EntryNav2 build (-DGAUGE_ENTRYNAV2), the latter with its data folder
#                     moved into build/ and its crash guard checked (the 4th start without uptime is refused)
OUT := build
CXX ?= g++
WARN := -Wall -Wextra
EN2_DATA := $(abspath $(OUT))/entrynav2-data

.PHONY: check clean
check: $(OUT)/test_cds_values $(OUT)/app_host_test $(OUT)/libGaugeApp.so $(OUT)/libGaugeApp-entrynav2.so
	$(OUT)/test_cds_values
	$(OUT)/app_host_test $(OUT)/libGaugeApp.so
	rm -rf $(EN2_DATA)
	$(OUT)/app_host_test $(OUT)/libGaugeApp-entrynav2.so
	test -s $(EN2_DATA)/gauge-app.log
	grep -q "text model API: .* -> ok" $(EN2_DATA)/gauge-app.log
	$(OUT)/app_host_test $(OUT)/libGaugeApp-entrynav2.so > /dev/null
	$(OUT)/app_host_test $(OUT)/libGaugeApp-entrynav2.so > /dev/null
	! $(OUT)/app_host_test $(OUT)/libGaugeApp-entrynav2.so > /dev/null
	grep -q "crash guard: the HMI restarted 3 times" $(EN2_DATA)/gauge-app.log
	@echo "entrynav2 crash guard OK"

$(OUT):
	mkdir -p $(OUT)

# The app is C++98 (QNX SDP 6.5 / GCC 4.4); keep the host build in the same dialect.
$(OUT)/test_cds_values: test_cds_values.cpp ../src/cds_values.hpp | $(OUT)
	$(CXX) -std=gnu++98 $(WARN) -I../src -o $@ test_cds_values.cpp

$(OUT)/libGaugeApp.so: ../src/engine_data.cpp ../src/cds_values.hpp | $(OUT)
	$(CXX) -std=gnu++98 $(WARN) -fPIC -shared -I../src -o $@ ../src/engine_data.cpp -ldl -lpthread

$(OUT)/libGaugeApp-entrynav2.so: ../src/engine_data.cpp ../src/cds_values.hpp | $(OUT)
	$(CXX) -std=gnu++98 $(WARN) -fPIC -shared -I../src -DGAUGE_ENTRYNAV2 -DGAUGE_DATA_DIR='"$(EN2_DATA)"' \
	    -o $@ ../src/engine_data.cpp -ldl -lpthread

# -rdynamic: the library looks up bmw::Runnable's vtable (and, for EntryNav2, the text model API) with
# dlsym(RTLD_DEFAULT) and needs the fake's symbols.
$(OUT)/app_host_test: app_host_test.cpp fake_appframework.cpp fake_appframework.hpp | $(OUT)
	$(CXX) -std=gnu++11 $(WARN) -rdynamic -o $@ app_host_test.cpp fake_appframework.cpp -ldl

clean:
	rm -rf $(OUT)
