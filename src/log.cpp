// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Logging and time. NBT Evo: slog (code 0x4e47). EntryNav2: <data dir>/gauge-app.log (bounded, rotated once). Both
// also append to <usb stick>/gauge-app.log when that file already exists on a stick (an empty file made on a PC
// switches it on). Host tests: stderr.
#include <dirent.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#ifdef __QNX__
#include <sys/slog.h>
#include <sys/slogcodes.h>
#endif
#include "app.hpp"

namespace ga {
namespace {

pthread_mutex_t g_logMutex = PTHREAD_MUTEX_INITIALIZER;
char   g_logPath[320] = "";                  // the stick's log, "" = none (g_logMutex)
time_t g_logChecked = 0;

// Folders a USB stick is mounted under, and the prefix of its mount point ("" = any). NBT Evo (QNX): /fs/usb0 (as
// NBTApp's install guide finds it) or /mnt/umass*. EntryNav2 (Linux): the mount point is not known for sure, so every
// folder directly under /media and /mnt is tried.
struct UsbRoot { const char* dir; const char* prefix; };
#ifdef GAUGE_ENTRYNAV2
const UsbRoot kUsbRoots[] = { { "/media", "" }, { "/mnt", "" }, { "/run/media", "" } };
#else
const UsbRoot kUsbRoots[] = { { "/fs", "usb" }, { "/mnt", "umass" } };
#endif

// <stick>/gauge-app.log of the first stick that already holds that file. Looked up at most every 5 s.
bool usbLogPath(char* out, size_t n) {
    MutexLock lock(g_logMutex);
    time_t now = time(NULL);
    if (!g_logChecked || now - g_logChecked >= 5 || now < g_logChecked) {
        g_logChecked = now;
        g_logPath[0] = 0;
        for (size_t r = 0; r < GA_COUNT(kUsbRoots) && !g_logPath[0]; ++r) {
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
    if (!g_logPath[0]) return false;
    snprintf(out, n, "%s", g_logPath);
    return true;
}

void appendTo(const char* path, const char* line, int n, int flags) {
    int fd = open(path, O_WRONLY | O_APPEND | flags, 0644);
    if (fd < 0) return;
    ssize_t w = write(fd, line, (size_t)n);
    (void)w;
    close(fd);
}

} // namespace

bool fileExists(const char* p) {
    struct stat st;
    return stat(p, &st) == 0;
}

long monoSec() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long)ts.tv_sec;
}

long monoMs() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long)ts.tv_sec * 1000L + (long)(ts.tv_nsec / 1000000);
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
    if (usbLogPath(path, sizeof(path))) appendTo(path, line, n, 0);
#ifdef GAUGE_ENTRYNAV2
    {   // EntryEVO has no slog: a bounded log on the data partition, always on (read it over SSH).
        MutexLock lock(g_logMutex);
        struct stat st;
        if (stat(kAppLog, &st) == 0 && (long)st.st_size > kAppLogMaxBytes) rename(kAppLog, kAppLogOld);
        appendTo(kAppLog, line, n, O_CREAT);
    }
#endif
#ifdef __QNX__
    slogf(_SLOG_SETCODE(0x4e47, 1), _SLOG_INFO, "[GaugeApp] %s", msg);
#else
    fputs(line, stderr);                                  // host tests
#endif
}

} // namespace ga
