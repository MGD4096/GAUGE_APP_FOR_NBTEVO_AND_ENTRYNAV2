// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Host test: loads a host build of libGaugeApp.so the way ManagedPluginApp does (dlsym "pluginAppInfo"), drives
// create / onInit / the posted Runnables / CDS callbacks / onFinalize / destroy against the fake framework and checks
// which images end up in the models, and that the maxima survive in <data dir>/max.txt.
//   app_host_test <libGaugeApp.so> <data dir the library was built with>
#include <dlfcn.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <string>
#include "fake_appframework.hpp"
#include "gauge_view.hpp"

using namespace eng::ids;

static int g_fail = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); ++g_fail; } } while (0)

struct Info {
    uint16_t a, b;
    const char* name;
    const char* vendor;
    uint32_t rhmi;
    bmw::PluginApp* (*create)(bmw::IDispatcher&, const char*, const bmw::Bundle&, const bmw::Bundle&);
    void (*destroy)(void*);
};

// Runs every Runnable that is queued right now once (what the framework does when the delay is over). Runnables that
// post themselves again land in the queue for the next call.
static int runPosted() {
    std::vector<std::pair<bmw::Runnable*, unsigned> > now;
    now.swap(g_fake.posted);
    for (size_t i = 0; i < now.size(); ++i) {
        void** vptr = *(void***)now[i].first;
        ((void (*)(void*))vptr[2])(now[i].first);      // slot 2 of the vptr array = run(), as in NBT-AAD's test
    }
    return (int)now.size();
}

static void feed(const char* prop, const char* ascii) {
    std::map<std::string, bmw::CdsDelegate>::iterator it = g_fake.cds.find(prop);
    if (it == g_fake.cds.end()) { printf("FAIL: no CDS handler for %s\n", prop); ++g_fail; return; }
    unsigned short buf[256];
    size_t n = 0;
    for (; ascii[n] && n < 255; ++n) buf[n] = (unsigned char)ascii[n];
    buf[n] = 0;
    bmw::BasicString<unsigned short> s(buf);
    it->second.stub(it->second.object, s);
}

static unsigned slot(int s) { return g_fake.modelImage[kFirstModel + (unsigned)s]; }
static int writes(int s) { return g_fake.modelWrites[kFirstModel + (unsigned)s]; }

static std::string readFile(const std::string& p) {
    std::string out;
    FILE* f = fopen(p.c_str(), "r");
    if (!f) return out;
    char b[256];
    size_t n;
    while ((n = fread(b, 1, sizeof(b), f)) > 0) out.append(b, n);
    fclose(f);
    return out;
}

int main(int argc, char** argv) {
    if (argc < 3) { printf("usage: %s libGaugeApp.so data-dir\n", argv[0]); return 2; }
    const std::string maxFile = std::string(argv[2]) + "/max.txt";
    void* h = dlopen(argv[1], RTLD_NOW | RTLD_GLOBAL);
    if (!h) { printf("dlopen: %s\n", dlerror()); return 1; }
    Info* info = (Info*)dlsym(h, "pluginAppInfo");
    if (!info) { printf("no pluginAppInfo\n"); return 1; }
    printf("pluginAppInfo: %u.%u name=%s vendor=%s rhmi=%u\n", info->a, info->b, info->name, info->vendor, info->rhmi);
    CHECK(info->a == 1 && info->b == 0 && info->rhmi == 1);

    char dummy[16];
    bmw::PluginApp* app = info->create(*(bmw::IDispatcher*)dummy, "GaugeApp", *(bmw::Bundle*)dummy, *(bmw::Bundle*)dummy);
    if (!app) { printf("create returned NULL\n"); return 1; }
    CHECK(strcmp(app->name, "GaugeApp") == 0);
    CHECK(info->create(*(bmw::IDispatcher*)dummy, "GaugeApp", *(bmw::Bundle*)dummy, *(bmw::Bundle*)dummy) == NULL);

    // ---- onInit: every slot written once, nothing known yet ----
    CHECK(app->onInit());
    CHECK(g_fake.baseOnInit == 1);
    CHECK((int)g_fake.modelWrites.size() == kSlotCount);
    CHECK(slot(kSlotCoolantArc) == kImgBlank && slot(kSlotCoolantMark) == kImgBlank);
    CHECK(slot(kSlotCoolantBig0) == eng::bigGlyph('-', 1));
    CHECK(slot(kSlotGearP) == kImgGear && slot(kSlotGearD) == kImgGear + 6);
    CHECK(g_fake.posted.size() == 1 && g_fake.posted[0].second == 1500);

    // ---- the subscription: six handlers, then the render loop ----
    runPosted();
    CHECK(g_fake.cds.size() == 6);
    CHECK(g_fake.cds.count("engine.temperature") && g_fake.cds.count("engine.RPMSpeed") &&
          g_fake.cds.count("engine.torque") && g_fake.cds.count("driving.gear") &&
          g_fake.cds.count("driving.acceleration") && g_fake.cds.count("driving.speedActual"));
    CHECK(g_fake.posted.size() == 1 && g_fake.posted[0].second == 200);

    // ---- values arrive, the next tick shows them ----
    feed("engine.temperature", "{\"temperature\":{\"engine\":90,\"oil\":104}}");
    feed("engine.RPMSpeed", "{\"RPMSpeed\":3600}");
    feed("engine.torque", "{\"torque\":380}");
    feed("driving.gear", "{\"gear\":6}");
    feed("driving.acceleration", "{\"acceleration\":{\"lateral\":9.81,\"longitudinal\":65535.00}}");
    CHECK(slot(kSlotCoolantArc) == kImgBlank);                  // nothing before the tick
    runPosted();
    CHECK(slot(kSlotCoolantArc) == kImgArc + 30);               // 90 of 50..130
    CHECK(slot(kSlotCoolantBig0) == eng::bigGlyph('9', 1) && slot(kSlotCoolantBig1) == eng::bigGlyph('0', 1));
    CHECK(slot(kSlotOilBig0) == eng::bigGlyph('1', 0) && slot(kSlotOilBig2) == eng::bigGlyph('4', 0));
    CHECK(slot(kSlotTorqueBig0) == eng::bigGlyph('3', 0) && slot(kSlotTorqueBig1) == eng::bigGlyph('8', 0));
    CHECK(slot(kSlotPowerBig0) == eng::bigGlyph('1', 0) && slot(kSlotPowerBig1) == eng::bigGlyph('9', 0) &&
          slot(kSlotPowerBig2) == eng::bigGlyph('5', 0));      // 380 Nm * 3600 / 7023.5 = 194.8 KM
    CHECK(slot(kSlotGearD) == kImgGear + 13 && slot(kSlotGearP) == kImgGear);
    CHECK(slot(kSlotGBig0) == eng::bigGlyph('1', 0) && slot(kSlotGBig2) == eng::bigGlyph('0', 0));   // "1,00"
    CHECK(slot(kSlotGLon0) == kImgBlank);                       // 65535 = not available, no speed yet
    CHECK(slot(kSlotCoolantMark) == kImgBlank);                 // one sample: no maximum yet
    CHECK(g_fake.posted.size() == 1);

    // ---- a second sample makes the maxima; only changed slots are written ----
    int oilW = writes(kSlotOilBig0);
    feed("engine.temperature", "{\"temperature\":{\"engine\":98,\"oil\":104}}");
    feed("engine.torque", "{\"torque\":400}");
    runPosted();
    CHECK(slot(kSlotCoolantMark) == kImgMark + 30);             // max = min(90, 98)
    CHECK(slot(kSlotCoolantMax0) == eng::smallGlyph('9', 0) && slot(kSlotCoolantMax1) == eng::smallGlyph('0', 0));
    CHECK(slot(kSlotOilMax0) == eng::smallGlyph('1', 0));
    CHECK(slot(kSlotTorqueMax0) == eng::smallGlyph('3', 0) && slot(kSlotTorqueMax1) == eng::smallGlyph('8', 0));
    CHECK(slot(kSlotTorqueScale0) == eng::smallGlyph('4', 0) && slot(kSlotTorqueScale1) == eng::smallGlyph('0', 0));
    CHECK(writes(kSlotOilBig0) == oilW);                        // oil unchanged: not rewritten
    int w = writes(kSlotCoolantArc);
    runPosted();                                                // nothing new: no writes
    CHECK(writes(kSlotCoolantArc) == w);

    // ---- bad values go back to "--", the maxima stay ----
    feed("engine.temperature", "{\"error\":400}");
    runPosted();
    CHECK(slot(kSlotCoolantArc) == kImgBlank && slot(kSlotCoolantBig0) == eng::bigGlyph('-', 1));
    CHECK(slot(kSlotCoolantMark) == kImgMark + 30);

    // ---- finalize writes max.txt; a new onInit reads it back ----
    bmw::BasicString<char> msg("integration error");
    app->onError(7, msg);
    app->onFinalize();
    CHECK(g_fake.baseOnFinalize == 1);
    runPosted();
    CHECK(g_fake.posted.empty());                               // the render loop stopped
    std::string saved = readFile(maxFile);
    printf("max.txt: %s", saved.c_str());
    CHECK(saved.find("coolant=90.0\n") != std::string::npos && saved.find("torque=380.0\n") != std::string::npos);
    FILE* f = fopen(maxFile.c_str(), "w");                      // as if it had been edited by hand
    if (f) { fputs("coolant=130.0\n", f); fclose(f); }
    CHECK(app->onInit());
    CHECK(slot(kSlotCoolantMark) == kImgMark + kArcSteps);      // 130 = the end of the scale
    CHECK(slot(kSlotTorqueMax0) == kImgBlank);                  // not in the file any more
    app->onFinalize();
    runPosted();
    info->destroy(app);

    if (g_fail) { printf("%d check(s) failed\n", g_fail); return 1; }
    printf("app_host_test OK\n");
    return 0;
}
