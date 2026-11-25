// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Host-test stand-in for libAppFramework.A.so / libCoreFramework.A.so: a bmw::PluginApp with the same 34-slot vtable
// layout, recording what the app does (updateModel images, posted Runnables, CDS handlers). Not the real framework.
#ifndef ENGINE_FAKE_APPFRAMEWORK_HPP
#define ENGINE_FAKE_APPFRAMEWORK_HPP
#include <stddef.h>
#include <string>
#include <vector>
#include <map>

namespace bmw {
class IDispatcher;
class Bundle;
enum RHMIInterfaceVersion { V1 = 1 };

template <typename T> class BasicString {
public:
    BasicString(const T* s);
    BasicString(const BasicString& o);
    ~BasicString();
    T* m_data;
};

class ImageID {
public:
    explicit ImageID(unsigned id);
    unsigned m_id, m_type;
};

// As on the car: a BasicString<char> first (destroyed by the app by hand), then a BufferStream.
class BufferStream {
public:
    ~BufferStream();
    const unsigned char* data;               // the caller's bytes (valid during updateModel)
    unsigned size;
};
class Image {
public:
    Image(const unsigned char* data, unsigned size);
    char* name;
    BufferStream stream;
};

class Runnable {
public:
    virtual ~Runnable();
    virtual void run() = 0;
};

class Parcel {
public:
    int dummy;
};
class TextID {
public:
    explicit TextID(unsigned id);
    unsigned m_id, m_type;
};

template <typename R, typename A1, typename A2, typename A3, typename A4> struct Delegate {
    void* object;
    R (*stub)(void*, A1);
};
typedef Delegate<bool, const BasicString<unsigned short>&, void, void, void> CdsDelegate;
typedef Delegate<bool, const Parcel&, void, void, void> ActionDelegate;

#define FAKE_SLOT(n) virtual void s##n();
class PluginApp {
public:
    PluginApp(IDispatcher&, BasicString<char> name, unsigned a, unsigned b, RHMIInterfaceVersion v, const Bundle&,
              const Bundle&);
    virtual ~PluginApp();
    FAKE_SLOT(2) FAKE_SLOT(3) FAKE_SLOT(4) FAKE_SLOT(5) FAKE_SLOT(6) FAKE_SLOT(7) FAKE_SLOT(8) FAKE_SLOT(9)
    FAKE_SLOT(10) FAKE_SLOT(11) FAKE_SLOT(12) FAKE_SLOT(13) FAKE_SLOT(14) FAKE_SLOT(15) FAKE_SLOT(16) FAKE_SLOT(17)
    FAKE_SLOT(18) FAKE_SLOT(19) FAKE_SLOT(20)
    virtual void onError(unsigned code, const BasicString<char>& text);   // slot 21
    virtual bool onInit();                                                // slot 22
    virtual void onFinalize();                                            // slot 23
    FAKE_SLOT(24) FAKE_SLOT(25) FAKE_SLOT(26) FAKE_SLOT(27) FAKE_SLOT(28) FAKE_SLOT(29) FAKE_SLOT(30) FAKE_SLOT(31)
    FAKE_SLOT(32) FAKE_SLOT(33)
    void post(Runnable* r, unsigned ms);
    void updateModel(unsigned modelId, const ImageID& image);
    void updateModel(unsigned modelId, const Image& image);
    void updateModel(unsigned modelId, const TextID& text);
    void addHandler(unsigned actionId, const ActionDelegate& handler);
    void triggerEvent(unsigned eventId);
    void cdsAddPropertyChangedEventHandler(BasicString<char>& name, unsigned id, const CdsDelegate& d);
    char name[64];
};
} // namespace bmw

// Recorded by the fake.
struct FakeState {
    std::map<unsigned, unsigned> modelImage;       // modelId -> latest frame id (picture data "ID:<n>", test packs)
    std::map<unsigned, int> modelWrites;           // modelId -> number of updateModel calls
    std::map<unsigned, unsigned> modelImageBytes;  // raImageModel -> size of the picture data
    int bufferStreamsDestroyed;
    std::vector<std::pair<bmw::Runnable*, unsigned> > posted;   // not yet run
    std::map<std::string, bmw::CdsDelegate> cds;   // property name -> handler
    std::map<unsigned, bmw::ActionDelegate> actions;   // raAction id -> handler
    std::map<unsigned, unsigned> modelText;        // textIdModel -> latest text id
    std::vector<unsigned> events;                  // triggerEvent ids, in order
    int baseOnInit, baseOnFinalize;
    FakeState() : bufferStreamsDestroyed(0), baseOnInit(0), baseOnFinalize(0) {}
};
extern FakeState g_fake;
#endif
