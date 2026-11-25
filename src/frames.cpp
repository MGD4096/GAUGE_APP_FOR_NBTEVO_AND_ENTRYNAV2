// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Frames and pictures. GaugeApp_frames.bin holds the frames that are the same in every colour (loaded once, kept);
// GaugeApp_frames_c<k>.bin the frames drawn in gauge colour k (arcs, g-meter dot, lit gear), loaded for the colour in
// use; GaugeApp_frames_s.bin the frames of screens 1..4, mapped the first time one of them is drawn.
// Format (make_db.py write_frames): "GFR1", u32 count, count x (u32 id, u32 offset, u32 size) sorted by id, then the
// PNG data; little endian. The packs are mapped read-only (mmap), never read into memory: only the pages of frames
// that are sent get loaded, and the system can drop them again under memory pressure.
// Pictures go out as data (PluginApp::updateModel(model, bmw::Image)): with every frame in the HMI's image DB an
// EntryNav2 showed no image at all (onError 9).
#include <fcntl.h>
#include <new>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include "app.hpp"

namespace ga {
namespace {

// bmw::Image copies the bytes; it has no exported destructor, so its two members are destroyed by hand. EntryEVO
// layout (libCoreFramework disassembly): +0 BasicString<char>, +4 BufferStream (vptr + 5 words); 28 bytes.
const size_t kImageWords = 16;
const size_t kImageRealSize = 28;
GA_STATIC_ASSERT(sizeof(bmw::Image) >= kImageRealSize && sizeof(bmw::Image) <= kImageWords * sizeof(void*),
                 image_storage_fits);

bool sendImageData(void* ctx, unsigned model, const unsigned char* data, unsigned size) {
    bmw::PluginApp* app = static_cast<bmw::PluginApp*>(ctx);
    void* mem[kImageWords];                  // >= sizeof(bmw::Image), pointer aligned
    memset(mem, 0, sizeof(mem));
    bmw::Image* img = new (mem) bmw::Image(data, size);
    app->updateModel(model, *img);
    reinterpret_cast<bmw::BufferStream*>(reinterpret_cast<char*>(mem) + sizeof(void*))->~BufferStream();
    reinterpret_cast<bmw::BasicString<char>*>(mem)->~BasicString();
    return true;
}

const char* const kFramesFile = "GaugeApp_frames.bin";
const char* const kScreensFile = "GaugeApp_frames_s.bin";
const long        kFramesMax = 16L * 1024L * 1024L;
struct Pack { unsigned char* data; unsigned size, count; };
Pack g_common = { NULL, 0, 0 };
Pack g_screens = { NULL, 0, 0 };
Pack g_color = { NULL, 0, 0 };
int  g_colorLoaded = -1;
bool g_screensTried = false;                 // the screens pack was asked for (a missing one is logged once)
bool g_missingLogged = false;

unsigned le32(const unsigned char* p) {
    return (unsigned)p[0] | ((unsigned)p[1] << 8) | ((unsigned)p[2] << 16) | ((unsigned)p[3] << 24);
}

void releasePack(Pack& pk) {
    if (pk.data) munmap(pk.data, pk.size);
    pk.data = NULL;
    pk.size = pk.count = 0;
}

bool loadPack(const char* name, Pack& out) {
    char path[256];
    snprintf(path, sizeof(path), "%s/%s", kPluginDir, name);
    int fd = open(path, O_RDONLY);
    if (fd < 0) { elog("cannot read %s: pictures are missing", path); return false; }
    struct stat st;
    void* m = MAP_FAILED;
    unsigned size = 0;
    if (fstat(fd, &st) == 0 && (long)st.st_size >= 8 && (long)st.st_size <= kFramesMax) {
        size = (unsigned)st.st_size;
        m = mmap(NULL, size, PROT_READ, MAP_PRIVATE, fd, 0);
    }
    close(fd);                                           // the mapping stays valid without the descriptor
    if (m == MAP_FAILED) { elog("cannot map %s (size %u)", path, size); return false; }
    unsigned char* p = static_cast<unsigned char*>(m);
    unsigned n = le32(p + 4);
    bool ok = memcmp(p, "GFR1", 4) == 0 && n > 0 && n < 100000 && 8 + 12ul * n <= size;
    for (unsigned i = 0; ok && i < n; ++i) {             // reads the table only, not the pictures
        const unsigned char* e = p + 8 + 12 * i;
        unsigned off = le32(e + 4), len = le32(e + 8);
        ok = off >= 8 + 12 * n && len > 0 && off <= size && len <= size - off && (i == 0 || le32(e) > le32(e - 12));
    }
    if (!ok) { elog("%s is damaged", name); munmap(m, size); return false; }
    releasePack(out);
    out.data = p;
    out.size = size;
    out.count = n;
    elog("%s: %u frames, %u bytes (mapped)", name, n, size);
    return true;
}

// The PNG data of frame id in a pack (binary search in its table).
bool findIn(const Pack& pk, unsigned id, const unsigned char** data, unsigned* size) {
    unsigned lo = 0, hi = pk.count;
    while (lo < hi) {
        unsigned mid = (lo + hi) / 2;
        const unsigned char* e = pk.data + 8 + 12 * mid;
        unsigned k = le32(e);
        if (k == id) { *data = pk.data + le32(e + 4); *size = le32(e + 8); return true; }
        if (k < id) lo = mid + 1; else hi = mid;
    }
    return false;
}

// Colour pack first, then the screens' and the common one.
bool findFrame(unsigned id, const unsigned char** data, unsigned* size) {
    return (g_color.data && findIn(g_color, id, data, size)) || (g_screens.data && findIn(g_screens, id, data, size)) ||
           (g_common.data && findIn(g_common, id, data, size));
}

} // namespace

FrameSink pluginSink(bmw::PluginApp* app) {
    FrameSink s = { app, &sendImageData };
    return s;
}

// A whole file of the plugin folder into a malloc'ed buffer (NULL when missing, empty or bigger than maxSize).
unsigned char* readPluginFile(const char* name, unsigned* size, long maxSize) {
    char path[256];
    snprintf(path, sizeof(path), "%s/%s", kPluginDir, name);
    struct stat st;
    if (stat(path, &st) != 0 || (long)st.st_size <= 0 || (long)st.st_size > maxSize) return NULL;
    unsigned char* buf = static_cast<unsigned char*>(malloc((size_t)st.st_size));
    if (!buf) return NULL;
    FILE* f = fopen(path, "rb");
    size_t n = f ? fread(buf, 1, (size_t)st.st_size, f) : 0;
    if (f) fclose(f);
    if (n != (size_t)st.st_size) { free(buf); return NULL; }
    *size = (unsigned)n;
    return buf;
}

bool loadFrames() {
    return g_common.data || loadPack(kFramesFile, g_common);
}

bool framesLoaded() { return g_common.data != NULL; }

void framesStartRun() { g_screensTried = false; }

// The pack of screens 1..4, the first time one of them is drawn (an engine-screen-only user never maps it).
bool loadScreens() {
    if (g_screens.data) return true;
    if (g_screensTried) return false;
    g_screensTried = true;
    return loadPack(kScreensFile, g_screens);
}

// The frame pack of gauge colour k (only when it is not the one already loaded).
bool loadColor(int k) {
    if (k == g_colorLoaded && g_color.data) return true;
    char name[48];
    snprintf(name, sizeof(name), "GaugeApp_frames_c%d.bin", k);
    if (!loadPack(name, g_color)) return false;
    g_colorLoaded = k;
    return true;
}

bool sendFrame(const FrameSink& out, unsigned model, unsigned id) {
    const unsigned char* data;
    unsigned size;
    if (!findFrame(id, &data, &size)) {
        if (!g_missingLogged) { g_missingLogged = true; elog("frame %u not in the frame packs (model %u)", id, model); }
        return false;
    }
    return out.send(out.ctx, model, data, size);
}

} // namespace ga
