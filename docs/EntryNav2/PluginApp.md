# EntryNav2 – the app framework (PluginApp)

How the HMI loads your own app and what it may do. Everything below except the "Not verified" section was checked in
the car (EntryNav2, F40) with GaugeApp, CdsScan and a series of diagnostic packages. The code pattern comes from NbtAad
and entry-aad. NBT Evo has the same framework (`/opt/hmi/ID5/lib`, the same symbols and the same `bmw::Image` layout).

## Plugin files

`/opt/hmi/data/ro/Plugins/<Name>/`:

| File | Role |
|---|---|
| `<Name>.manifest` | XML: `<file>{pluginDir}/<Name>` (the HMI loads `lib<Name>.so`), `autoStart`, `pluginAppConnector` (type `Etch`, `id`), paths to the XML and both DBs |
| `lib<Name>.so` | the library, exports only `pluginAppInfo` |
| `<Name>.xml` | description of the menu and the screens (`DescFile`) |
| `<Name>_ALL_Texts.zip` | text DB: `<language>.txt`, lines `id=text`, `100000=<language name>`; ASCII only |
| `<Name>_ALL_Images.zip` | image DB: `<id>.png`. **Must be small** (see below) |

The `pluginAppConnector` and `entryButtonFocusID` ids must differ between plugins:

| Plugin | connector id | entryButtonFocusID | applicationWeight |
|---|---|---|---|
| entry-aad | 210 | (entry-aad) | |
| GaugeApp | 211 | 32751 | 210 |
| CdsScan | 212 | 32753 | 212 |

## Entry point

```cpp
extern "C" struct PluginAppInfo {
    uint16_t versionMajor, versionMinor;    // 1, 0
    const char* name;                       // text of the menu row
    const char* vendor;
    uint32_t rhmiInterfaceVersion;          // 1
    bmw::PluginApp* (*create)(bmw::IDispatcher&, const char* name, const bmw::Bundle& params, const bmw::Bundle& config);
    void (*destroy)(void*);
} pluginAppInfo;
```

`create` constructs a `bmw::PluginApp` (constructor `PluginApp(IDispatcher&, BasicString<char> name, unsigned major,
unsigned minor, RHMIInterfaceVersion, const Bundle&, const Bundle&)`) in at least **0x200 bytes** of memory. Your own
`onInit` / `onError` / `onFinalize` are hooked in through a copy of the `PluginApp` vtable: 34 slots, **onError = 21,
onInit = 22, onFinalize = 23**. `destroy` calls slot 1 (the destructor with `operator delete`).

## `bmw::PluginApp` functions (libAppFramework.A.so)

| Function | Works in the car | For |
|---|---|---|
| `post(Runnable*, unsigned ms)` | yes | runs `run()` on the app thread after a delay. Your own Runnable: a copy of the vtable `_ZTVN3bmw8RunnableE` (5 words, `run` in slot 4) |
| `updateModel(unsigned, const Image&)` | yes | a PNG picture sent as data into a `raImageModel` |
| `updateModel(unsigned, const ImageID&)` | yes | a picture from the image DB |
| `updateModel(unsigned, const TextID&)` | yes | a text of the text DB into a `textIdModel` (changes a button's label) |
| `addHandler(unsigned action, const Delegate&)` | yes | handles a `raAction` (button). Register it **before** the base `onInit` |
| `cdsAddPropertyChangedEventHandler(BasicString<char>&, unsigned, const CdsDelegate&)` | yes | CDS subscription. First value = the current state, then only changes. 248 subscriptions (10 every 300 ms) without errors |
| `cdsRemovePropertyChangedEventHandler` | – | ends a subscription |
| `cdsGetPropertyAsync(name, delegate)` | – | one-off read, the answer comes the same way as changes |
| `cdsIsPropertyAvailable(name)` | – | synchronous question about a name (result type unknown) |
| `cdsSetPropertyAsync(name, value, data, size)` | **do not use** | writes to CDS |
| `invokeCDSUpdate(name, value)` | – | called by the framework: looks up the name in the map and calls the delegate |

Inside (EntryNav2 disassembly): the CDS map `name → delegate` is at `this+0x140`, the connection object at
`this+0x68`. Its virtual methods: `0x9c` add a subscription, `0x94` asynchronous read, `0xa4` `isPropertyAvailable`.
A delegate (`bmw::Delegate`) is the pair `{void* object; R (*stub)(void*, A1)}`. CDS passes the value as a
`BasicString<unsigned short>` (UTF-16) without the property name, so every subscription needs its own stub.

`bmw::Image(const unsigned char* data, unsigned size)`: 28 bytes (`BasicString<char>` + `BufferStream`, i.e. a vptr
and 5 words), copies the data. **There is no exported `~Image`**: call `BufferStream::~BufferStream()` (at +4) and
`BasicString<char>::~BasicString()` (at +0) by hand.

## Screen description (XML)

```xml
<pluginApps><pluginApp applicationType="OnlineServices" applicationWeight="…" entryButtonFocusID="…"
            insertAfterFocusID="2270" insertStateID="20" text="…">
  <entryButton action="5" id="1" model="3" imageModel="4"/>
  <actions> <hmiAction id="5" target="10"/> <raAction id="31"/> … </actions>
  <models> <textIdModel id="3" textId="1"/> <imageIdModel id="4" imageId="…"/> <raImageModel id="100"/> … </models>
  <hmiStates>
    <hmiState id="10" text="…" textModel="3">
      <optionComponents> <button action="7" id="60" model="46" text="…"/> </optionComponents>
      <components> <image id="300" model="100"><properties>…</properties></image> <button …/> <label …/> </components>
    </hmiState>
  </hmiStates></pluginApp></pluginApps>
```

- **Where the row goes:** `applicationType="OnlineServices"` = the ConnectedDrive menu (`"Online"` alone does not
  work); `"Custom"` with `insertStateID 20` / `insertAfterFocusID 2270` = Media/Radio after Bluetooth audio.
- **Ids** of models, components, actions and states must all be different in the whole file.
- **Image properties:** 2 = SELECTABLE, 3 = VISIBLE, 9 = width, 10 = height, 20 = X, 21 = Y (in pixels).
- **Components:** `image`, `button` (with `action`; its text is changed with `updateModel(TextID)`), `label`,
  `checkbox`, `separator`.
- **OPTION:** `optionComponents` with `hmiAction` buttons → another state. The HMI shows entries of its own above
  them (e.g. "Wyłącz pojazd" – switch the car off, or its own "Ustawienia" – Settings – in some contexts; the Polish
  HMI's labels), so an app entry named like one of them looks
  duplicated. Child states (`parentId`) also show the **parent's** OPTION entries, so an entry repeated in a child
  appears twice: GaugeApp puts "Ustawienia" only in the parent state 10, and its settings page holds the screen
  buttons (`hmiAction` to each screen's state) above the settings.
- **Opening a state from code:** `<events><focusEvent id="…" target="<state>"/></events>` and
  `PluginApp::triggerEvent(id)` (entry-aad, car-verified there; iDrive refuses it while one of its own popups is on
  top). An entry button with a `raAction` instead of an `hmiAction` lets the app choose the state: GaugeApp opens the
  screen shown last (focusEvents 90..94).
- **The title of the state on screen** arrives in CDS `hmi.graphicalContext` → `menuTitle` (the text DB's text). That
  tells which screen of the app is visible.

## Limits checked in the car

| What | Result |
|---|---|
| Big image DB (635 PNGs in `_ALL_Images.zip`) | the HMI shows **no** picture at all and reports `onError 9`. With 3 pictures everything works |
| Pictures in one state | about **60**. Components beyond that stay empty. Every state has its own limit |
| Visible area of a state | about **1250 × 470 px** (GaugeApp: 960 × 400 design, scale 1.15, origin at 73,4) |
| Positions and stacking | work: pictures sit at the given pixels and stack in XML order |
| `raImageModel` (PNG as data) | works, and replacing it 5 times a second is smooth (about 4.9 frames/s) |
| PNG | RGBA and indexed (palette, 32 / 256 colours with transparency) both work. GaugeApp stores every frame as an indexed PNG: 4-6 times smaller |
| Texts | ASCII only in `*.txt`. Polish letters can only be shown drawn into pictures |

That is why GaugeApp keeps its frames in its own packs (`*_frames*.bin`) and sends them as data, and the image DB
only holds the menu row icon.

## Good practice

- **Off switch:** an `app.disable` file in the data or plugin folder makes `create` return `NULL`.
- **Restart-loop guard:** a start counter in a file. 3 HMI restarts within 2 min turn the app off.
- Log to a file in `/var/local/data/<app>/` (with a size limit) and optionally to a USB stick when a file of the same
  name is there.
- Write data files through a temporary file and `rename`, with `fsync`: power goes away without warning.
- Register CDS subscriptions about 1.5 s after `onInit` (with `post`), in batches.

## Not verified

- the result type of `cdsIsPropertyAvailable` and whether `cdsGetPropertyAsync` works;
- the exact mount point of a USB stick.
