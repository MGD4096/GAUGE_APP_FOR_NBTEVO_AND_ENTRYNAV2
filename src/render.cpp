// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Rendering: which frame every slot shows (the pure *_view.hpp headers decide), and only the slots whose frame changed
// go out. GaugeApp.xml (make_db.py) binds slot i of screen k to raImageModel 1000k + 100 + i (the engine screen:
// kFirstModel + i) and its background to 1000k + 99. Only the screen on display is written (hmi.graphicalContext).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "app.hpp"

namespace ga {
namespace {

GA_STATIC_ASSERT(eng::ids::kDrvSlotCount <= kScreenSlotsMax && eng::ids::kFuelSlotCount <= kScreenSlotsMax &&
                 eng::ids::kPerfSlotCount <= kScreenSlotsMax && eng::ids::kWarmSlotCount <= kScreenSlotsMax,
                 screen_slots_fit);
GA_STATIC_ASSERT((int)eng::kLangCount == (int)eng::ids::kUiLangCount, ui_langs_match_make_db);

// What each slot shows now (render thread only), to skip unchanged ones.
unsigned g_shown[eng::ids::kSlotCount];      // the engine screen
bool     g_shownValid = false;
unsigned g_shownBg = 0;                      // its background frame (the language)
struct ScreenCache { unsigned shown[kScreenSlotsMax]; bool valid; unsigned bg; };
ScreenCache g_cache[eng::ids::kScreenCount];   // screens 1..4 (index 0 unused)

// Diagnostics (make_db.py --diag-out): pictures in the plugin folder sent as data to the raImageModels of the
// diagnostic XML. onInit sends each file of kDiagFiles that exists; anim0.png .. anim9.png, when present, are sent in
// turn to kDiagAnimModel on every render tick (an animation at the refresh rate).
struct DiagFile { const char* name; unsigned models[3]; };
const DiagFile kDiagFiles[] = {
    { "test.png", { 560, 561, 0 } },         // 549x484 card
    { "icon.png", { 564, 565, 0 } },         // 63x54 icon
    { "wide.png", { 562, 0, 0 } },           // the whole content area
};
const unsigned kDiagAnimModel = 563;
const int      kDiagAnimFrames = 10;
const long     kDiagPngMax = 4L * 1024L * 1024L;
unsigned char* g_anim[kDiagAnimFrames];      // animation frames, loaded once
unsigned       g_animSize[kDiagAnimFrames];
int            g_animCount = 0, g_animNext = 0;
long           g_animStartMs = 0, g_animSent = 0;

} // namespace

// Picks the frame of every slot of the engine screen and sends each one that differs from what is shown.
int renderView(const FrameSink& out, RenderMode mode) {
    eng::Metrics m;
    eng::Maxima mx;
    eng::Settings st;
    {
        MutexLock lock(g_dataMutex);
        m = g_state.metrics;
        mx = g_state.maxima;
        st = g_state.settings;
        g_state.dirty = false;
    }
    if (!framesLoaded()) return 0;
    const bool all = mode == kEverything || !g_shownValid;
    unsigned view[eng::ids::kSlotCount];
    eng::computeView(m, mx, st, view);
    int written = 0;
    const unsigned bg = eng::backgroundFrame(m);         // follows vehicle.language
    if (all || bg != g_shownBg) {
        if (sendFrame(out, eng::ids::kBackgroundModel, bg)) ++written;
        g_shownBg = bg;
    }
    for (int i = 0; i < eng::ids::kSlotCount; ++i) {
        if (!all && g_shown[i] == view[i]) continue;
        if (sendFrame(out, eng::ids::kFirstModel + (unsigned)i, view[i])) ++written;
        g_shown[i] = view[i];
    }
    g_shownValid = true;
    return written;
}

// Screen s (1..4): its row of eng::kScreenDescs computes the slots; each one that changed goes out.
int renderScreen(const FrameSink& out, int s, RenderMode mode) {
    const eng::ScreenDesc* desc = eng::screenDesc(s);
    if (!desc) return 0;
    eng::ScreenInputs in;
    {
        MutexLock lock(g_dataMutex);
        in.m = g_state.metrics;
        in.gmax = g_state.gmax;
        in.env = g_state.env;
        in.cal = g_state.cal;
        in.trip = g_state.trip;
        in.perf = g_state.perf;
        in.warm = g_state.warm;
        in.st = g_state.settings;
        in.brakeFull = g_state.brakeFull;
    }
    unsigned view[kScreenSlotsMax];
    desc->compute(in, monoMs(), view);
    if (!framesLoaded() || !loadScreens()) return 0;
    ScreenCache& c = g_cache[s];
    const bool all = mode == kEverything || !c.valid;
    int written = 0;
    const unsigned base = 1000u * (unsigned)s;
    const unsigned bg = eng::screenBackground(s, in.m.uiLang());
    if (all || bg != c.bg) {
        if (sendFrame(out, base + 99, bg)) ++written;
        c.bg = bg;
    }
    for (int i = 0; i < desc->slotCount; ++i) {
        if (!all && c.shown[i] == view[i]) continue;
        if (sendFrame(out, base + 100 + (unsigned)i, view[i])) ++written;
        c.shown[i] = view[i];
    }
    c.valid = true;
    return written;
}

// Only the screen on display is written; all of them while that is not known. Screens 1..4 (and their frame pack)
// are not touched while only the engine screen is used.
void renderVisible(const FrameSink& out) {
    bool dirty;
    int visible;
    {
        MutexLock lock(g_dataMutex);
        dirty = g_state.dirty;
        visible = g_state.visible;
    }
    const bool all = visible == kVisUnknown || visible == kVisSomeApp;
    if (dirty && (all || visible == eng::kScreenEngine)) renderView(out, kOnlyChanged);
    for (int s = 1; s < eng::ids::kScreenCount; ++s)
        if (all || visible == s) renderScreen(out, s, kOnlyChanged);
}

void invalidateScreens() {
    g_shownValid = false;
    for (int s = 0; s < eng::ids::kScreenCount; ++s) g_cache[s].valid = false;
}

// menuTitle of hmi.graphicalContext is the title of the state on display (the text DB's, in any UI language; the
// table is generated by make_db.py from the same texts as the XML).
int screenForTitle(const char* t) {
    for (int s = 0; s < eng::ids::kScreenCount; ++s)
        for (int l = 0; l < eng::kLangCount; ++l)
            if (strcmp(t, eng::ids::kScreenTitles[s][l]) == 0) return s;
    return -1;
}

// Diagnostics: the pictures of kDiagFiles into their raImageModels, and the animation frames loaded.
void sendDiagPictures(const FrameSink& out) {
    for (size_t i = 0; i < GA_COUNT(kDiagFiles); ++i) {
        unsigned size = 0;
        unsigned char* buf = readPluginFile(kDiagFiles[i].name, &size, kDiagPngMax);
        if (!buf) continue;
        for (int k = 0; k < 3 && kDiagFiles[i].models[k]; ++k) out.send(out.ctx, kDiagFiles[i].models[k], buf, size);
        elog("diag: %s (%u bytes) sent to raImageModel %u%s", kDiagFiles[i].name, size, kDiagFiles[i].models[0],
             kDiagFiles[i].models[1] ? " and more" : "");
        free(buf);
    }
    if (g_animCount == 0) {
        for (int k = 0; k < kDiagAnimFrames; ++k) {
            char name[32];
            snprintf(name, sizeof(name), "anim%d.png", k);
            g_anim[g_animCount] = readPluginFile(name, &g_animSize[g_animCount], kDiagPngMax);
            if (!g_anim[g_animCount]) break;
            ++g_animCount;
        }
        if (g_animCount) elog("diag: %d animation frames, sent to raImageModel %u every %u ms", g_animCount,
                              kDiagAnimModel, kRenderMs);
    }
    g_animStartMs = monoMs();
    g_animSent = 0;
}

// Diagnostics: the next animation frame (called on every render tick); the achieved rate is logged every 50 frames.
void diagAnimTick(const FrameSink& out) {
    if (!g_animCount) return;
    out.send(out.ctx, kDiagAnimModel, g_anim[g_animNext], g_animSize[g_animNext]);
    g_animNext = (g_animNext + 1) % g_animCount;
    if (++g_animSent % 50 == 0) elog("diag: %ld animation frames in %ld ms", g_animSent, monoMs() - g_animStartMs);
}

} // namespace ga
