// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#include "fake_appframework.hpp"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

FakeState g_fake;

namespace bmw {
template <> BasicString<char>::BasicString(const char* s) : m_data(strdup(s)) {}
template <> BasicString<char>::BasicString(const BasicString& o) : m_data(strdup(o.m_data)) {}
template <> BasicString<char>::~BasicString() { free(m_data); }
template <> BasicString<unsigned short>::BasicString(const unsigned short* s) {
    size_t n = 0;
    while (s[n]) ++n;
    m_data = (unsigned short*)malloc((n + 1) * sizeof(unsigned short));
    memcpy(m_data, s, (n + 1) * sizeof(unsigned short));
}
template <> BasicString<unsigned short>::~BasicString() { free(m_data); }

ImageID::ImageID(unsigned id) : m_id(id), m_type(1) {}
TextID::TextID(unsigned id) : m_id(id), m_type(0) {}

void PluginApp::updateModel(unsigned id, const TextID& t) { g_fake.modelText[id] = t.m_id; }
void PluginApp::addHandler(unsigned id, const ActionDelegate& d) { g_fake.actions[id] = d; }
void PluginApp::triggerEvent(unsigned id) { g_fake.events.push_back(id); }

BufferStream::~BufferStream() { g_fake.bufferStreamsDestroyed++; }
Image::Image(const unsigned char* data, unsigned size) : name(NULL) { stream.data = data; stream.size = size; }

Runnable::~Runnable() {}

#define FAKE_SLOT_DEF(n) void PluginApp::s##n() { printf("FAKE slot %d\n", n); }
PluginApp::PluginApp(IDispatcher&, BasicString<char> n, unsigned, unsigned, RHMIInterfaceVersion, const Bundle&,
                     const Bundle&) {
    snprintf(name, sizeof(name), "%s", n.m_data);
}
PluginApp::~PluginApp() {}
FAKE_SLOT_DEF(2) FAKE_SLOT_DEF(3) FAKE_SLOT_DEF(4) FAKE_SLOT_DEF(5) FAKE_SLOT_DEF(6) FAKE_SLOT_DEF(7) FAKE_SLOT_DEF(8)
FAKE_SLOT_DEF(9) FAKE_SLOT_DEF(10) FAKE_SLOT_DEF(11) FAKE_SLOT_DEF(12) FAKE_SLOT_DEF(13) FAKE_SLOT_DEF(14)
FAKE_SLOT_DEF(15) FAKE_SLOT_DEF(16) FAKE_SLOT_DEF(17) FAKE_SLOT_DEF(18) FAKE_SLOT_DEF(19) FAKE_SLOT_DEF(20)
FAKE_SLOT_DEF(24) FAKE_SLOT_DEF(25) FAKE_SLOT_DEF(26) FAKE_SLOT_DEF(27) FAKE_SLOT_DEF(28) FAKE_SLOT_DEF(29)
FAKE_SLOT_DEF(30) FAKE_SLOT_DEF(31) FAKE_SLOT_DEF(32) FAKE_SLOT_DEF(33)
void PluginApp::onError(unsigned c, const BasicString<char>& t) { printf("FAKE base onError %u %s\n", c, t.m_data); }
bool PluginApp::onInit() { g_fake.baseOnInit++; return true; }
void PluginApp::onFinalize() { g_fake.baseOnFinalize++; }

void PluginApp::post(Runnable* r, unsigned ms) { g_fake.posted.push_back(std::make_pair(r, ms)); }

void PluginApp::updateModel(unsigned id, const ImageID& img) {
    g_fake.modelImage[id] = img.m_id;
    g_fake.modelWrites[id]++;
}

// Pictures of the test frame pack are the text "ID:<frame id>": recorded as that frame id.
void PluginApp::updateModel(unsigned id, const Image& img) {
    g_fake.modelImageBytes[id] = img.stream.size;
    g_fake.modelWrites[id]++;
    std::string s(reinterpret_cast<const char*>(img.stream.data), img.stream.size);
    if (s.compare(0, 3, "ID:") == 0) g_fake.modelImage[id] = (unsigned)strtoul(s.c_str() + 3, NULL, 10);
}

void PluginApp::cdsAddPropertyChangedEventHandler(BasicString<char>& n, unsigned, const CdsDelegate& d) {
    g_fake.cds[n.m_data] = d;
}
} // namespace bmw
