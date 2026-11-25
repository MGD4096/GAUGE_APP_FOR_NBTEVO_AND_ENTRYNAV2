// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Minimal declarations of BMW's RHMI app framework (libAppFramework.A.so / libCoreFramework.A.so). There are no BMW
// headers: names and parameter types only, so that the compiler produces the mangled names both head units export
// (checked with nm -D on the copies from the cars; `make check` compares every bmw:: import of the library with
// lib/*/lib*Framework.A.so when they are there, tests/check_abi.sh). Nothing here is defined by this project.
// The framework glue follows NBT-AAD's rhmiapp/nbt_aad_app.cpp (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// and entry-aad's hmiapp/bmw_framework.cpp, both car-verified.
#ifndef GAUGE_BMW_FRAMEWORK_HPP
#define GAUGE_BMW_FRAMEWORK_HPP
#include <stddef.h>

namespace bmw {
class IDispatcher;
class Bundle;
class Runnable;
enum RHMIInterfaceVersion { RHMI_INTERFACE_VERSION_1 = 1 };

template <typename T> class BasicString {
public:
    BasicString(const T* s);                 // _ZN3bmw11BasicStringIcEC1EPKc
    BasicString(const BasicString& other);
    ~BasicString();
    const T* raw() const { return m_data; }  // the data pointer is the only member
private:
    T* m_data;
};

// Image data for a raImageModel. EntryEVO layout (libCoreFramework disassembly): +0 BasicString<char> (a file name),
// +4 BufferStream (vptr + 5 words, 24 bytes) holding a copy of the data; 28 bytes. There is no exported ~Image: the
// two member destructors are called by hand (destroyImage). Storage is oversized on purpose.
class BufferStream {
public:
    ~BufferStream();                         // _ZN3bmw12BufferStreamD1Ev
};
class Image {
public:
    Image(const unsigned char* data, unsigned size);   // _ZN3bmw5ImageC1EPKhj (copies the data)
private:
    unsigned char m_storage[64];
};

class Parcel;                                // the value of an action (only passed through)
class TextID {
public:
    explicit TextID(unsigned id);            // _ZN3bmw6TextIDC1Ej (entry-aad's menu texts, car-verified)
private:
    unsigned m_id, m_type;
};

template <typename R, typename A1, typename A2, typename A3, typename A4> struct Delegate {
    void* object;
    R (*stub)(void* object, A1 a1);
};
typedef Delegate<bool, const BasicString<unsigned short>&, void, void, void> CdsDelegate;
typedef Delegate<bool, const Parcel&, void, void, void> ActionDelegate;

const size_t kPluginAppStorage = 0x200;      // SecurityMenu's own members start at 0x160, EntryEVO writes up to +0x174

class PluginApp {
public:
    PluginApp(IDispatcher& dispatcher, BasicString<char> name, unsigned major, unsigned minor,
              RHMIInterfaceVersion rhmi, const Bundle& params, const Bundle& config);
    void post(Runnable* runnable, unsigned delayMs);                // runs runnable->run() on the app thread
    void updateModel(unsigned modelId, const Image& image);        // raImageModel: picture data (car-verified)
    void updateModel(unsigned modelId, const TextID& text);        // textIdModel (entry-aad, car-verified)
    void addHandler(unsigned actionId, const ActionDelegate& handler);   // raAction (entry-aad, car-verified)
    void triggerEvent(unsigned eventId);     // focusEvent of the XML: opens its state (entry-aad, car-verified)
    void cdsAddPropertyChangedEventHandler(BasicString<char>& property, unsigned id, const CdsDelegate& handler);
    bool onInit();                           // base implementations, called from our overrides
    void onFinalize();
private:
    unsigned char m_storage[kPluginAppStorage];
};
} // namespace bmw

namespace ga {
// bmw::PluginApp's vtable as both head units lay it out: our overrides replace these slots in a copy of it.
enum { kSlotOnError = 21, kSlotOnInit = 22, kSlotOnFinalize = 23, kVtblSlots = 34 };
} // namespace ga

#endif
