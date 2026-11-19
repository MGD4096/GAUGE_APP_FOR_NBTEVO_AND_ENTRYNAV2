// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// libGaugeApp.so - live engine data (coolant / oil temperature, RPM, speed, gear, fuel, outside temperature) as a
// native iDrive "PluginApp" for BMW NBT Evo head units (ID5 / ID6).
//
// How it works: HmiMain3D loads Plugins/GaugeApp/GaugeApp.manifest at boot. GaugeApp.xml adds a menu row and one
// screen (hmiState 10) with seven labels, each bound to a raDataModel (text). This library subscribes to the car's
// CDS properties (the same call NBT-AAD uses for driving.gear / sensors.PDCStatus), keeps the latest values and, twice
// a second, writes changed rows into the label models with PluginApp::updateModel(model, text).
//
// The framework glue (PluginApp constructor, own vtable, Runnable stand-in, pluginAppInfo) is the pattern car-verified
// by NBT-AAD's rhmiapp/nbt_aad_app.cpp (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto); only the declarations
// that are needed here are repeated, there are no BMW headers. Not built or run against a real head unit yet - see
// README.md.
//
// Logs: slog (code 0x4e47) always; plus <usb stick>/gauge-app.log if that file already exists on a stick
// (create an empty one on a PC to switch it on).
//
// Two targets are built from this one file:
//   NBT Evo (default)     QNX 6.5, qcc / GCC 4.4, installed in /opt/hmi/ID5/data/ro/Plugins/GaugeApp
//   EntryNav2 (-DGAUGE_ENTRYNAV2)  EntryEVO, Linux ARMv7 hard-float, glibc 2.15, GCC 4.7, installed in
//                         /opt/hmi/data/ro/Plugins/GaugeApp. The framework glue there is the one car-verified by
//                         entry-aad (hmiapp/bmw_framework.cpp); its differences are in the "platform" block below.
#include <stdio.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <fcntl.h>
#include <new>
#include <dirent.h>
#include <sys/stat.h>
#include <dlfcn.h>
#ifndef RTLD_DEFAULT
#define RTLD_DEFAULT ((void*)-2)   // QNX value
#endif
#include <pthread.h>
#ifdef __QNX__
#include <sys/slog.h>
#include <sys/slogcodes.h>
#endif
#include "cds_values.hpp"

#ifdef GAUGE_ENTRYNAV2
#define ENGINE_APP_TARGET "EntryNav2"
#else
#define ENGINE_APP_TARGET "NBT Evo"
#endif
#define ENGINE_APP_VERSION "engine-data-0.1.0 " ENGINE_APP_TARGET " (" __DATE__ " " __TIME__ ")"

// ---- minimal declarations of BMW's RHMI app framework (libAppFramework.A.so / libCoreFramework.A.so) ----------------
// Names and parameter types only (they produce the exported, mangled symbols); nothing here is defined. All of these
// symbols are exported by the libraries (checked with nm -D on the copies from the car).
namespace bmw {
class IDispatcher;
class Bundle;
class Runnable;
enum RHMIInterfaceVersion { RHMI_INTERFACE_VERSION_1 = 1 };

template <typename T> class BasicString {
public:
    BasicString(const T* s);                 // _ZN3bmw11BasicStringIcEC1EPKc / ...ItEC1EPKt (UTF-16)
    BasicString(const BasicString& other);   // char only is exported; never used for UTF-16
    ~BasicString();
    const T* raw() const { return m_data; }  // the data pointer is the only member
private:
    T* m_data;
};

template <typename R, typename A1, typename A2, typename A3, typename A4> struct Delegate {
    void* object;
    R (*stub)(void* object, A1 a1);
};
typedef Delegate<bool, const BasicString<unsigned short>&, void, void, void> CdsDelegate;

const size_t kPluginAppStorage = 0x200;      // SecurityMenu's own members start at 0x160

class PluginApp {
public:
    PluginApp(IDispatcher& dispatcher, BasicString<char> name, unsigned major, unsigned minor,
              RHMIInterfaceVersion rhmi, const Bundle& params, const Bundle& config);
    void post(Runnable* runnable, unsigned delayMs);                       // runs runnable->run() on the app thread
    void updateModel(unsigned modelId, const BasicString<unsigned short>& text);   // raDataModel text (UTF-16)
    void cdsAddPropertyChangedEventHandler(BasicString<char>& property, unsigned id, const CdsDelegate& handler);
    bool onInit();                           // base implementations, called from our overrides
    void onFinalize();
private:
    unsigned char m_storage[kPluginAppStorage];
};
} // namespace bmw

namespace {

// ---- constants --------------------------------------------------------------------------------------------------
const unsigned    kFirstRowModel = 21;       // raDataModel ids 21..27 in GaugeApp.xml, one per row
const unsigned    kSubscribeDelayMs = 1500;  // CDS handlers are registered ~1.5 s after onInit, like NBT-AAD / SecurityMenu
const unsigned    kRenderMs = 500;           // label refresh period (only changed rows are written)
const long        kNoDataWarnS = 25;         // log once when no CDS value arrived this long after subscribing
#ifdef GAUGE_ENTRYNAV2
// EntryEVO: /var/local is the writable data partition (mounted noexec: data only, as entry-aad keeps its settings in
// /var/local/data/AA). Nothing is written outside this folder.
#ifndef GAUGE_DATA_DIR
#define GAUGE_DATA_DIR "/var/local/data/GaugeApp"   // host tests point it into their build folder
#endif
const char* const kDataDir = GAUGE_DATA_DIR;
const char* const kDisableA = GAUGE_DATA_DIR "/app.disable";
const char* const kDisableB = "/opt/hmi/data/ro/Plugins/GaugeApp/app.disable";
const char* const kAppLog = GAUGE_DATA_DIR "/gauge-app.log";
const char* const kAppLogOld = GAUGE_DATA_DIR "/gauge-app.old.log";
const long        kAppLogMaxBytes = 512L * 1024L;
const char* const kAppGuard = GAUGE_DATA_DIR "/app-guard";   // crash guard, see crashGuardAllows()
const int         kCrashGuardMax = 3;        // HMI starts without kStableAfterS of uptime before the app turns off
const long        kStableAfterS = 120;
#else
const char* const kDisableA = "/opt/gaugeapp/app.disable";
const char* const kDisableB = "/var/opt/gaugeapp/app.disable";
#endif
const char* const kUsbLogName = "gauge-app.log";
const long        kUsbLogMaxBytes = 4L * 1024L * 1024L;
enum { kSlotOnError = 21, kSlotOnInit = 22, kSlotOnFinalize = 23, kVtblSlots = 34 };   // PluginApp vtable layout

// ---- logging ---------------------------------------------------------------------------------------------------
pthread_mutex_t g_logMutex = PTHREAD_MUTEX_INITIALIZER;
char   g_logPath[320] = "";
time_t g_logChecked = 0;

bool fileExists(const char* p) {
    struct stat st;
    return stat(p, &st) == 0;
}

// Folders a USB stick is mounted under, and the prefix of its mount point ("" = any). NBT Evo (QNX): /mnt/umass*.
// EntryNav2 (Linux): the mount point is not known for sure, so every folder directly under /media and /mnt is tried.
struct UsbRoot { const char* dir; const char* prefix; };
#ifdef GAUGE_ENTRYNAV2
const UsbRoot kUsbRoots[] = { { "/media", "" }, { "/mnt", "" }, { "/run/media", "" } };
#else
const UsbRoot kUsbRoots[] = { { "/mnt", "umass" } };
#endif

// <stick>/gauge-app.log of the first stick that already holds that file (an empty file made on a PC switches the
// log on). Looked up at most every 5 s.
bool usbLogPath(char* out, size_t n) {
    pthread_mutex_lock(&g_logMutex);
    time_t now = time(NULL);
    if (!g_logChecked || now - g_logChecked >= 5 || now < g_logChecked) {
        g_logChecked = now;
        g_logPath[0] = 0;
        for (size_t r = 0; r < sizeof(kUsbRoots) / sizeof(kUsbRoots[0]) && !g_logPath[0]; ++r) {
            DIR* d = opendir(kUsbRoots[r].dir);
            if (!d) continue;
            size_t plen = strlen(kUsbRoots[r].prefix);
            struct dirent* e;
            while ((e = readdir(d)) != NULL) {
                if (e->d_name[0] == '.') continue;
                if (strncmp(e->d_name, kUsbRoots[r].prefix, plen) != 0) continue;
                char p[320];
                snprintf(p, sizeof(p), "%s/%.200s/%s", kUsbRoots[r].dir, e->d_name, kUsbLogName);
                struct stat st;
                if (stat(p, &st) == 0 && (long)st.st_size < kUsbLogMaxBytes && access(p, W_OK) == 0) {
                    snprintf(g_logPath, sizeof(g_logPath), "%s", p);
                    break;
                }
            }
            closedir(d);
        }
    }
    bool ok = g_logPath[0] != 0;
    if (ok) snprintf(out, n, "%s", g_logPath);
    pthread_mutex_unlock(&g_logMutex);
    return ok;
}

void elog(const char* fmt, ...) {
    char msg[320];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(msg, sizeof(msg), fmt, ap);
    va_end(ap);
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    char line[400];
    int n = snprintf(line, sizeof(line), "[%5ld.%03ld] [GaugeApp] %s\n", (long)ts.tv_sec,
                     (long)(ts.tv_nsec / 1000000), msg);
    if (n < 0) return;
    if (n >= (int)sizeof(line)) n = (int)sizeof(line) - 1;
    char path[320];
    if (usbLogPath(path, sizeof(path))) {
        int fd = open(path, O_WRONLY | O_APPEND);
        if (fd >= 0) {
            ssize_t w = write(fd, line, (size_t)n);
            (void)w;
            close(fd);
        }
    }
#ifdef GAUGE_ENTRYNAV2
    // EntryEVO has no slog: a bounded log on the data partition, always on (read it over SSH).
    pthread_mutex_lock(&g_logMutex);
    struct stat st;
    if (stat(kAppLog, &st) == 0 && (long)st.st_size > kAppLogMaxBytes) rename(kAppLog, kAppLogOld);
    int fd = open(kAppLog, O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (fd >= 0) {
        ssize_t w = write(fd, line, (size_t)n);
        (void)w;
        close(fd);
    }
    pthread_mutex_unlock(&g_logMutex);
#endif
#ifdef __QNX__
    slogf(_SLOG_SETCODE(0x4e47, 1), _SLOG_INFO, "[GaugeApp] %s", msg);
#else
    fputs(line, stderr);                                  // host tests
#endif
}

// ---- state ----------------------------------------------------------------------------------------------------
bmw::PluginApp* g_app = NULL;                // set in create, cleared in finalize / destroy
pthread_mutex_t g_dataMutex = PTHREAD_MUTEX_INITIALIZER;
eng::Metrics    g_metrics;
bool            g_dirty = true;
char            g_shown[eng::kRowCount][eng::kRowLen];   // what each label currently holds (to skip unchanged rows)
bool            g_shownValid = false;
int             g_seen[eng::kPropCount];     // how many values arrived per property
bool            g_lastOk[eng::kPropCount];   // whether the last value of a property was usable
long            g_subscribedAt = -1;         // monotonic s of the subscription, -1 before
bool            g_noDataLogged = false;
int             g_totalSeen = 0;

long monoSec() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long)ts.tv_sec;
}

// ---- crash guard (EntryNav2) ---------------------------------------------------------------------------------------
// create() appends a line to app-guard; once the HMI has run kStableAfterS with the app, the render loop deletes the
// file. kCrashGuardMax lines = HmiMain3D went down that many times shortly after loading this app: create() refuses
// and iDrive starts without it (the scheme entry-aad uses on the same head unit). NBT Evo: no-op.
long g_initAt = -1;                          // monotonic s of onInit, -1 before
#ifdef GAUGE_ENTRYNAV2
bool g_stableMarked = false;
bool crashGuardAllows() {
    int lines = 0;
    FILE* f = fopen(kAppGuard, "r");
    if (f) {
        char b[64];
        while (fgets(b, sizeof(b), f)) ++lines;
        fclose(f);
    }
    if (lines >= kCrashGuardMax) {
        elog("crash guard: the HMI restarted %d times shortly after loading this app: app turned off. Check the log, "
             "then remove %s and restart the unit.", lines, kAppGuard);
        return false;
    }
    f = fopen(kAppGuard, "a");
    if (f) {
        fprintf(f, "%ld\n", (long)time(NULL));
        fflush(f);
        fsync(fileno(f));
        fclose(f);
    }
    return true;
}
void markStableWhenDue() {
    if (g_stableMarked || g_initAt < 0 || monoSec() - g_initAt < kStableAfterS) return;
    g_stableMarked = true;
    unlink(kAppGuard);
    elog("stable for %ld s: crash guard reset", kStableAfterS);
}
#else
bool crashGuardAllows() { return true; }
void markStableWhenDue() {}
#endif

// ---- bmw::Runnable stand-in (vtable: offset-to-top, typeinfo, ~D1, ~D0, run), copied from libCoreFramework's own
// vtable so the type info is right. Static objects, so the destructor slots are no-ops. Same technique as NBT-AAD.
struct StandInRunnable { void** vptr; };
void runnableNoop(void*) {}

void initRunnable(StandInRunnable& r, void** vtbl /* 5 slots */, void (*run)(void*)) {
    void** base = reinterpret_cast<void**>(dlsym(RTLD_DEFAULT, "_ZTVN3bmw8RunnableE"));
    if (base) memcpy(vtbl, base, 5 * sizeof(void*));
    else { vtbl[0] = NULL; vtbl[1] = NULL; }
    vtbl[2] = reinterpret_cast<void*>(&runnableNoop);
    vtbl[3] = reinterpret_cast<void*>(&runnableNoop);
    vtbl[4] = reinterpret_cast<void*>(run);
    r.vptr = vtbl + 2;
}

StandInRunnable g_subRunnable;
StandInRunnable g_renderRunnable;
void* g_subVtbl[5];
void* g_renderVtbl[5];

// ---- display -----------------------------------------------------------------------------------------------------
#ifdef GAUGE_ENTRYNAV2
// On EntryEVO, entry-aad (the car-verified reference) only ever writes TextID / ImageID / bool models; nobody has
// checked yet that this HU's libAppFramework exports the UTF-16 text overload of updateModel or the
// BasicString<unsigned short> constructor. A direct call would make HmiMain3D's dlopen (or, with lazy binding, the
// first call) fail, so the three symbols are looked up at run time instead: if one is missing the rows stay empty and
// the log says so, iDrive itself keeps running. Same ABI as the member calls (ARM EABI: this = first argument).
typedef void (*WideCtorFn)(void* self, const unsigned short* s);   // bmw::BasicString<unsigned short>::BasicString
typedef void (*WideDtorFn)(void* self);                            // bmw::BasicString<unsigned short>::~BasicString
typedef void (*UpdateTextFn)(bmw::PluginApp* self, unsigned modelId, const void* text);   // PluginApp::updateModel
WideCtorFn   g_wideCtor = NULL;
WideDtorFn   g_wideDtor = NULL;
UpdateTextFn g_updateText = NULL;
int          g_textApi = -1;                 // -1 not looked up, 0 missing, 1 available

bool textApi() {
    if (g_textApi < 0) {
        g_wideCtor = reinterpret_cast<WideCtorFn>(dlsym(RTLD_DEFAULT, "_ZN3bmw11BasicStringItEC1EPKt"));
        g_wideDtor = reinterpret_cast<WideDtorFn>(dlsym(RTLD_DEFAULT, "_ZN3bmw11BasicStringItED1Ev"));
        g_updateText = reinterpret_cast<UpdateTextFn>(
            dlsym(RTLD_DEFAULT, "_ZN3bmw9PluginApp11updateModelEjRKNS_11BasicStringItEE"));
        g_textApi = (g_wideCtor && g_wideDtor && g_updateText) ? 1 : 0;
        elog("text model API: BasicString<ushort>() %p, ~BasicString<ushort>() %p, updateModel(text) %p -> %s",
             reinterpret_cast<void*>(g_wideCtor), reinterpret_cast<void*>(g_wideDtor),
             reinterpret_cast<void*>(g_updateText),
             g_textApi ? "ok" : "MISSING: rows cannot be written on this head unit (see README, EntryNav2)");
    }
    return g_textApi == 1;
}

void writeRow(bmw::PluginApp* app, int row, const char* utf8) {
    if (!textApi()) return;
    unsigned short wide[eng::kRowLen];
    eng::utf8to16(utf8, wide, eng::kRowLen);
    void* text[4];                           // a BasicString holds one data pointer; spare room just in case
    memset(text, 0, sizeof(text));
    g_wideCtor(text, wide);
    g_updateText(app, kFirstRowModel + (unsigned)row, text);
    g_wideDtor(text);
}
#else
void writeRow(bmw::PluginApp* app, int row, const char* utf8) {
    unsigned short wide[eng::kRowLen];
    eng::utf8to16(utf8, wide, eng::kRowLen);
    bmw::BasicString<unsigned short> text(wide);
    app->updateModel(kFirstRowModel + (unsigned)row, text);
}
#endif

// Formats the current values and writes every row whose text changed. force = write all (first call).
void renderRows(bmw::PluginApp* app, bool force) {
    eng::Metrics snap;
    pthread_mutex_lock(&g_dataMutex);
    snap = g_metrics;
    g_dirty = false;
    pthread_mutex_unlock(&g_dataMutex);
    char rows[eng::kRowCount][eng::kRowLen];
    eng::formatRows(snap, rows);
    for (int i = 0; i < eng::kRowCount; ++i) {
        if (!force && g_shownValid && strcmp(rows[i], g_shown[i]) == 0) continue;
        writeRow(app, i, rows[i]);
        memcpy(g_shown[i], rows[i], eng::kRowLen);
    }
    g_shownValid = true;
}

void renderRun(void* /*self*/) {
    bmw::PluginApp* app = g_app;
    if (!app) return;                                    // finalized: do not post again
    bool dirty;
    pthread_mutex_lock(&g_dataMutex);
    dirty = g_dirty;
    pthread_mutex_unlock(&g_dataMutex);
    if (dirty) renderRows(app, false);
    markStableWhenDue();
    if (!g_noDataLogged && g_subscribedAt >= 0 && g_totalSeen == 0 && monoSec() - g_subscribedAt >= kNoDataWarnS) {
        g_noDataLogged = true;
        elog("no CDS value arrived %ld s after subscribing: the car may not publish engine.* / sensors.* / driving.* to "
             "plugin apps, or the subscription failed (see README, 'No data')", (long)kNoDataWarnS);
    }
    app->post(reinterpret_cast<bmw::Runnable*>(&g_renderRunnable), kRenderMs);
}

// ---- CDS ---------------------------------------------------------------------------------------------------------
void handleCds(int prop, const bmw::BasicString<unsigned short>& value) {
    char text[200];
    eng::narrow(value.raw(), text, sizeof(text));
    bool changed;
    bool ok;
    int seen;
    bool wasOk;
    pthread_mutex_lock(&g_dataMutex);
    changed = eng::apply(g_metrics, prop, text);
    if (changed) g_dirty = true;
    ok = eng::propValid(g_metrics, prop);
    seen = ++g_seen[prop];
    wasOk = g_lastOk[prop];
    g_lastOk[prop] = ok;
    ++g_totalSeen;
    pthread_mutex_unlock(&g_dataMutex);
    // The first values of every property are logged raw (that is what is needed to check a car's layout); after that
    // only a change between usable / not usable, so a revving engine does not flood the log.
    if (seen <= 5 || ok != wasOk) elog("CDS %s = '%s' -> %s", eng::propName(prop), text, ok ? "ok" : "not usable");
}

typedef bool (*CdsStub)(void*, const bmw::BasicString<unsigned short>&);

template <int P> bool onCds(void* /*app*/, const bmw::BasicString<unsigned short>& v) {
    handleCds(P, v);
    return true;
}

const CdsStub kStubs[eng::kPropCount] = { &onCds<0>, &onCds<1>, &onCds<2>, &onCds<3>, &onCds<4>, &onCds<5> };

void subscribeRun(void* /*self*/) {
    bmw::PluginApp* app = g_app;
    if (!app) return;
    for (int p = 0; p < eng::kPropCount; ++p) {
        bmw::BasicString<char> name(eng::propName(p));
        bmw::CdsDelegate d;
        d.object = app;
        d.stub = kStubs[p];
        app->cdsAddPropertyChangedEventHandler(name, 0, d);
        elog("CDS handler for %s registered", eng::propName(p));
    }
    g_subscribedAt = monoSec();
    initRunnable(g_renderRunnable, g_renderVtbl, &renderRun);
    app->post(reinterpret_cast<bmw::Runnable*>(&g_renderRunnable), kRenderMs);
}

// ---- the app object ---------------------------------------------------------------------------------------------
void* g_vtbl[2 + kVtblSlots];   // [offset-to-top, typeinfo, slots...] copied from bmw::PluginApp's vtable

bool appOnInit(bmw::PluginApp* self) {
    bool ok = self->onInit();                            // base implementation
    for (int p = 0; p < eng::kPropCount; ++p) { g_seen[p] = 0; g_lastOk[p] = false; }
    g_totalSeen = 0;
    g_subscribedAt = -1;
    g_noDataLogged = false;
    g_shownValid = false;
    g_initAt = monoSec();
    renderRows(self, true);                              // "--" in every row until the first CDS values arrive
    initRunnable(g_subRunnable, g_subVtbl, &subscribeRun);
    self->post(reinterpret_cast<bmw::Runnable*>(&g_subRunnable), kSubscribeDelayMs);
    elog("onInit: base onInit -> %d, %d label rows written, CDS subscription in %u ms", (int)ok, (int)eng::kRowCount,
         kSubscribeDelayMs);
    return ok;
}

void appOnError(bmw::PluginApp* /*self*/, unsigned code, const bmw::BasicString<char>& text) {
    const char* s = text.raw();
    elog("onError %u: %s", code, s ? s : "(null)");
}

void appOnFinalize(bmw::PluginApp* self) {
    elog("onFinalize");
    g_app = NULL;                                        // posted Runnables see this and stop
    self->onFinalize();
}

bmw::PluginApp* createApp(bmw::IDispatcher& dispatcher, const char* name, const bmw::Bundle& params,
                          const bmw::Bundle& config) {
#ifdef GAUGE_ENTRYNAV2
    mkdir(kDataDir, 0755);
#endif
    elog("create(name=%s) %s", name ? name : "(null)", ENGINE_APP_VERSION);
    if (fileExists(kDisableA) || fileExists(kDisableB)) { elog("disabled by app.disable"); return NULL; }
    if (g_app) { elog("create: already created"); return NULL; }
    if (!crashGuardAllows()) return NULL;

    void* mem = ::operator new(bmw::kPluginAppStorage);
    memset(mem, 0, bmw::kPluginAppStorage);
    bmw::PluginApp* app = new (mem) bmw::PluginApp(dispatcher, bmw::BasicString<char>(name ? name : "GaugeApp"), 1, 0,
                                                   bmw::RHMI_INTERFACE_VERSION_1, params, config);

    // Own vtable: identical to bmw::PluginApp's, with our onInit / onError / onFinalize (what a C++ subclass would do).
    void** base = *reinterpret_cast<void***>(app);
    memcpy(g_vtbl, base - 2, sizeof(g_vtbl));
    g_vtbl[2 + kSlotOnInit]     = reinterpret_cast<void*>(&appOnInit);
    g_vtbl[2 + kSlotOnError]    = reinterpret_cast<void*>(&appOnError);
    g_vtbl[2 + kSlotOnFinalize] = reinterpret_cast<void*>(&appOnFinalize);
    *reinterpret_cast<void***>(app) = g_vtbl + 2;

    g_app = app;
    elog("create: app %p (PluginApp vtable %p)", (void*)app, (void*)base);
    return app;
}

void destroyApp(void* app) {
    elog("destroy(%p)", app);
    if (!app) return;
    if (app == g_app) g_app = NULL;
    void** vt = *reinterpret_cast<void***>(app);
    reinterpret_cast<void (*)(void*)>(vt[1])(app);       // deleting destructor (PluginApp::~PluginApp + operator delete)
}

__attribute__((constructor)) void libraryLoaded() {
#ifdef GAUGE_ENTRYNAV2
    mkdir(kDataDir, 0755);
#endif
    elog("library loaded into pid %d, %s", (int)getpid(), ENGINE_APP_VERSION);
}

} // namespace

// ---- entry point looked up by ManagedPluginApp::init (dlsym "pluginAppInfo") ----------------------------------------
extern "C" {
struct EnginePluginAppInfo {
    uint16_t versionMajor;
    uint16_t versionMinor;
    const char* name;
    const char* vendor;
    uint32_t rhmiInterfaceVersion;
    bmw::PluginApp* (*create)(bmw::IDispatcher&, const char*, const bmw::Bundle&, const bmw::Bundle&);
    void (*destroy)(void*);
};
__attribute__((visibility("default"))) EnginePluginAppInfo pluginAppInfo = {
    1, 0, "GAUGE APP", "NBT-ENGINE", 1, &createApp, &destroyApp
};
}
