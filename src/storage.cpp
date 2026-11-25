// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Files in the data folder: max.txt (the last run's maxima, to read over SSH), settings.txt (colour, units, last
// screen), torque-env.txt and fuel-cal.txt (learned, kept), and the EntryNav2 crash guard (app-guard). Every write goes
// through a temporary file, fsync and rename: power can go at any moment. Never called from a CDS or action callback.
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include "app.hpp"

namespace ga {
namespace {

long g_savedAt = 0;                          // monotonic s of the last max.txt write (render thread)
long g_initAt = -1;                          // monotonic s of onInit, -1 before

// The whole (small) file into buf, NUL-terminated; false (and "") when it cannot be read.
bool readSmallFile(const char* path, char* buf, size_t n) {
    buf[0] = 0;
    FILE* f = fopen(path, "r");
    if (!f) return false;
    size_t k = fread(buf, 1, n - 1, f);
    fclose(f);
    buf[k] = 0;
    return true;
}

// path.new, fsync, rename over path: a power cut never leaves half a file.
void writeFileAtomically(const char* path, const char* text) {
    char tmp[256];
    int n = snprintf(tmp, sizeof(tmp), "%s.new", path);
    if (n < 0 || (size_t)n >= sizeof(tmp)) { elog("path too long: %s", path); return; }
    mkdir(kDataDir, 0755);
    FILE* f = fopen(tmp, "w");
    if (!f) { elog("cannot write %s", tmp); return; }
    fputs(text, f);
    fflush(f);
    fsync(fileno(f));
    fclose(f);
    if (rename(tmp, path) != 0) elog("cannot rename %s", tmp);
}

void oneLine(char* text) {
    for (char* p = text; *p; ++p) if (*p == '\n') *p = ' ';
}

} // namespace

// ---- the maxima -----------------------------------------------------------------------------------------------------
// They start from nothing every time the app starts (onInit); max.txt only keeps the maxima of the last run. The
// previous run's values are logged before they are dropped.
void resetMaxima() {
    char buf[256];
    readSmallFile(kMaxFile, buf, sizeof(buf));
    oneLine(buf);
    {
        MutexLock lock(g_dataMutex);
        g_state.maxima = eng::Maxima();
        g_state.maxDirty = false;
    }
    elog("maxima reset (last run: %s)", buf[0] ? buf : "none");
}

void saveMaxima() {
    char buf[256];
    {
        MutexLock lock(g_dataMutex);
        eng::formatMaxima(g_state.maxima, buf, sizeof(buf));
        g_state.maxDirty = false;
    }
    writeFileAtomically(kMaxFile, buf);
    g_savedAt = monoSec();
}

// ---- kept between runs: torque envelope (engine load) and the fuel counter calibration ------------------------------
void loadKept() {
    char buf[1024];
    eng::TorqueEnv env;
    eng::FuelCal cal;
    if (readSmallFile(kEnvFile, buf, sizeof(buf))) eng::parseEnv(env, buf);
    if (readSmallFile(kCalFile, buf, sizeof(buf))) eng::parseCal(cal, buf);
    {
        MutexLock lock(g_dataMutex);
        g_state.env = env;
        g_state.cal = cal;
    }
    elog("fuel counter: %.3f ul per step (%d calibrations from the tank level)", cal.factor * 1e6, cal.calibrations);
}

void saveKept() {
    char env[512], cal[256];
    bool we, wc;
    {
        MutexLock lock(g_dataMutex);
        we = g_state.env.changed;
        wc = g_state.cal.changed;
        if (we) eng::formatEnv(g_state.env, env, sizeof(env));
        if (wc) eng::formatCal(g_state.cal, cal, sizeof(cal));
        g_state.env.changed = false;
        g_state.cal.changed = false;
    }
    if (we) writeFileAtomically(kEnvFile, env);
    if (wc) writeFileAtomically(kCalFile, cal);
}

// ---- settings.txt ---------------------------------------------------------------------------------------------------
void loadSettings() {
    char buf[256];
    readSmallFile(kSettingsFile, buf, sizeof(buf));
    eng::Settings st;
    eng::parseSettings(st, buf);
    {
        MutexLock lock(g_dataMutex);
        g_state.settings = st;
        g_state.settingsDirty = false;       // just loaded
    }
    char text[128];
    eng::formatSettings(st, text, sizeof(text));
    oneLine(text);
    elog("settings: %s", text);
}

void saveSettingsIfDirty() {
    char buf[128];
    {
        MutexLock lock(g_dataMutex);
        if (!g_state.settingsDirty) return;
        eng::formatSettings(g_state.settings, buf, sizeof(buf));
        g_state.settingsDirty = false;
    }
    writeFileAtomically(kSettingsFile, buf);
}

void saveDueFiles() {
    saveSettingsIfDirty();
    if (monoSec() - g_savedAt < kSaveEveryS) return;
    bool maxDirty;
    {
        MutexLock lock(g_dataMutex);
        maxDirty = g_state.maxDirty;
    }
    if (maxDirty) saveMaxima();
    else g_savedAt = monoSec();
    saveKept();
}

// ---- crash guard (EntryNav2) ----------------------------------------------------------------------------------------
// create() appends a line to app-guard; once the HMI has run kStableAfterS with the app, the render loop deletes the
// file. kCrashGuardMax lines = HmiMain3D went down that many times shortly after loading this app: create() refuses
// and iDrive starts without it (the scheme entry-aad uses on the same head unit). NBT Evo: no-op.
void storageStartRun() {
    g_initAt = monoSec();
    g_savedAt = monoSec();
}

#ifdef GAUGE_ENTRYNAV2
namespace {
bool g_stableMarked = false;
} // namespace

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

} // namespace ga
