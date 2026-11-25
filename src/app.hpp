// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// The plugin's internal interface: constants, the shared state and what each module offers the others. Not exported
// from libGaugeApp.so (built with -fvisibility=hidden; only pluginAppInfo is visible). Modules:
//   log.cpp          log file / USB stick / slog, monotonic time
//   storage.cpp      max.txt, settings.txt, torque-env.txt, fuel-cal.txt, crash guard
//   frames.cpp       frame packs (mmap), PNG data into raImageModels (FrameSink)
//   render.cpp       which frame each slot shows -> only the changed ones out; what is on display; diagnostics
//   cds.cpp          CDS values in: parsing into the shared state, one stub per property
//   engine_data.cpp  the PluginApp itself: vtable, onInit / onError / onFinalize, actions, render tick, entry point
// Two targets from the same sources: NBT Evo (default; QNX 6.5, qcc / GCC 4.4) and EntryNav2 (-DGAUGE_ENTRYNAV2;
// Linux ARMv7 hard-float, glibc 2.15).
#ifndef GAUGE_APP_HPP
#define GAUGE_APP_HPP
#include <pthread.h>
#include <stddef.h>
#include "compat.hpp"
#include "bmw_framework.hpp"
#include "cds_values.hpp"
#include "gauge_view.hpp"
#include "screens_view.hpp"

#ifdef GAUGE_ENTRYNAV2
#define ENGINE_APP_TARGET "EntryNav2"
#else
#define ENGINE_APP_TARGET "NBT Evo"
#endif
#define ENGINE_APP_VERSION "engine-data-0.3.0 " ENGINE_APP_TARGET " (" __DATE__ " " __TIME__ ")"

#ifndef GAUGE_DATA_DIR
#ifdef GAUGE_ENTRYNAV2
// EntryEVO: /var/local is the writable data partition (mounted noexec: data only, as entry-aad keeps its settings in
// /var/local/data/AA).
#define GAUGE_DATA_DIR "/var/local/data/GaugeApp"
#else
#define GAUGE_DATA_DIR "/var/opt/gaugeapp"   // NBT Evo: /opt is often read-only
#endif
#endif
#ifndef GAUGE_PLUGIN_DIR
#ifdef GAUGE_ENTRYNAV2
#define GAUGE_PLUGIN_DIR "/opt/hmi/data/ro/Plugins/GaugeApp"
#else
#define GAUGE_PLUGIN_DIR "/opt/hmi/ID5/data/ro/Plugins/GaugeApp"
#endif
#endif

namespace ga {

// ---- constants (const at namespace scope: the same value in every module, no symbol) -----------------------------
const unsigned    kSubscribeDelayMs = 1500;  // CDS handlers are registered ~1.5 s after onInit, like NBT-AAD / SecurityMenu
const unsigned    kRenderMs = 200;           // image refresh period (only changed images are written)
const long        kNoDataWarnS = 25;         // log once when no CDS value arrived this long after subscribing
const long        kSaveEveryS = 30;          // a changed maximum is written to max.txt at most this often
const char* const kDataDir = GAUGE_DATA_DIR;  // host tests point it into their build folder
const char* const kPluginDir = GAUGE_PLUGIN_DIR;
const char* const kDisableA = GAUGE_DATA_DIR "/app.disable";
const char* const kMaxFile = GAUGE_DATA_DIR "/max.txt";
const char* const kSettingsFile = GAUGE_DATA_DIR "/settings.txt";
const char* const kEnvFile = GAUGE_DATA_DIR "/torque-env.txt";     // engine load: largest torque per rpm (kept)
const char* const kCalFile = GAUGE_DATA_DIR "/fuel-cal.txt";       // litres per engine.consumption step (kept)
#ifdef GAUGE_ENTRYNAV2
const char* const kDisableB = "/opt/hmi/data/ro/Plugins/GaugeApp/app.disable";
const char* const kAppLog = GAUGE_DATA_DIR "/gauge-app.log";
const char* const kAppLogOld = GAUGE_DATA_DIR "/gauge-app.old.log";
const long        kAppLogMaxBytes = 512L * 1024L;
const char* const kAppGuard = GAUGE_DATA_DIR "/app-guard";   // crash guard, see crashGuardAllows()
const int         kCrashGuardMax = 3;        // HMI starts without kStableAfterS of uptime before the app turns off
const long        kStableAfterS = 120;
#else
const char* const kDisableB = "/opt/gaugeapp/app.disable";
#endif
const char* const kUsbLogName = "gauge-app.log";
const long        kUsbLogMaxBytes = 4L * 1024L * 1024L;
const int         kScreenSlotsMax = 64;      // slots of the largest screen 1..4 (also bounded by ~60 images per state)

// ---- locking ------------------------------------------------------------------------------------------------------
// Holds a mutex for the rest of the scope, released on every path.
class MutexLock {
public:
    explicit MutexLock(pthread_mutex_t& m) : m_(m) { pthread_mutex_lock(&m_); }
    ~MutexLock() { pthread_mutex_unlock(&m_); }
private:
    MutexLock(const MutexLock&);             // not copyable (declared, never defined)
    MutexLock& operator=(const MutexLock&);
    pthread_mutex_t& m_;
};

// ---- the shared state (engine_data.cpp) ---------------------------------------------------------------------------
// What hmi.graphicalContext says is on display: one of our screens (0..4), or
enum { kVisUnknown = -1,                     // no context yet (or the car never sends it): every screen is written
       kVisOther = -2,                       // something else (radio, a menu, our settings): nothing is written
       kVisSomeApp = -3 };                   // a plugin app's state (appType "4") whose title we do not know: all

// Written by the CDS callbacks and the action handlers, read by the render tick: every member is guarded by
// g_dataMutex. Copy what you need under the lock, then do the slow work (files, updateModel) without it.
struct AppState {
    eng::Metrics   metrics;
    eng::Maxima    maxima;
    eng::Settings  settings;                 // colour, units, last screen (settings.txt)
    bool           dirty;                    // the engine screen needs a redraw
    bool           maxDirty;                 // a maximum changed since max.txt was written
    bool           settingsDirty;            // settings changed since settings.txt was written
    eng::GMax      gmax;                     // g per direction of this run
    eng::TorqueEnv env;                      // kept in torque-env.txt
    eng::FuelCal   cal;                      // kept in fuel-cal.txt
    eng::Trip      trip;                     // since onInit
    eng::Perf      perf;
    eng::WarmUp    warm;
    double         brakeFull;                // the largest brakeContact seen
    int            visible;                  // screen on display, or kVisUnknown / kVisOther / kVisSomeApp
    // CDS statistics (logging)
    int            seen[eng::kPropCount];    // values that arrived per property
    bool           lastOk[eng::kPropCount];  // whether the last value of a property was usable
    int            totalSeen;
    long           subscribedAt;             // monotonic s of the subscription, -1 before
    bool           noDataLogged;

    AppState();
    // A new run (onInit): what lives only for one run starts over; settings, metrics and the kept files stay.
    void startRun(long nowMs);
};
extern pthread_mutex_t g_dataMutex;
extern AppState g_state;

// ---- log.cpp ------------------------------------------------------------------------------------------------------
void elog(const char* fmt, ...) __attribute__((format(printf, 1, 2)));
bool fileExists(const char* path);
long monoSec();
long monoMs();

// ---- storage.cpp --------------------------------------------------------------------------------------------------
void resetMaxima();                          // onInit: the maxima start from nothing (the last run's are logged)
void saveMaxima();
void loadKept();                             // torque-env.txt, fuel-cal.txt
void saveKept();                             // only what changed
void loadSettings();
void saveSettingsIfDirty();                  // render tick and onFinalize, never from a callback (fsync)
void saveDueFiles();                         // render tick: settings, and every kSaveEveryS the maxima / kept files
void storageStartRun();                      // onInit: save timer and crash guard uptime start here
bool crashGuardAllows();                     // create(): EntryNav2 crash guard (NBT Evo: always true)
void markStableWhenDue();                    // render tick

// ---- frames.cpp ---------------------------------------------------------------------------------------------------
// Where pictures go: the PluginApp's raImageModels on the car, anything else in a test.
struct FrameSink {
    void* ctx;
    bool (*send)(void* ctx, unsigned model, const unsigned char* png, unsigned size);
};
FrameSink pluginSink(bmw::PluginApp* app);   // PluginApp::updateModel(model, bmw::Image)
unsigned char* readPluginFile(const char* name, unsigned* size, long maxSize);   // malloc'ed, NULL if missing
bool loadFrames();                           // the common pack (once)
bool loadScreens();                          // the screens pack, on first use
bool loadColor(int color);                   // the pack of a gauge colour
bool framesLoaded();
void framesStartRun();                       // onInit: a missing screens pack is looked for again
bool sendFrame(const FrameSink& out, unsigned model, unsigned frameId);

// ---- render.cpp ---------------------------------------------------------------------------------------------------
enum RenderMode { kOnlyChanged, kEverything };   // kEverything: every slot and the background, e.g. after onInit
int  renderView(const FrameSink& out, RenderMode mode);          // the engine screen; images written
int  renderScreen(const FrameSink& out, int s, RenderMode mode); // screen 1..4
void renderVisible(const FrameSink& out);    // render tick: only what is on display
void invalidateScreens();                    // same frame ids, other pictures (colour change): send everything again
int  screenForTitle(const char* menuTitle);  // 0..4, -1: not one of ours
void sendDiagPictures(const FrameSink& out);
void diagAnimTick(const FrameSink& out);

// ---- cds.cpp ------------------------------------------------------------------------------------------------------
void subscribeAll(bmw::PluginApp* app);      // one handler per eng::Prop

} // namespace ga

#endif
