# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""GaugeApp.xml: models, actions, events, states (the settings page, the OPTION menu, every screen)."""

from .base import DEFAULT_MENU, MENUS
from .layout import H, W, sc
from .ids import IMG_ICON, IMG_TEST
from .texts import SETTING_KEYS, TEXTS, TEXT_SETTINGS_TITLE, TITLE, XML_LANG
from .screens import SCREEN_LIST

# ---- more screens: Driving, Fuel and trip, Performance (OPTION menu) ---------------------------------------------------
# Each is a state of its own (states 14..16): its own background frame (model base + 99) and image slots (model base +
# 100 + i), so each has its own ~60-image budget. Their frames are in GaugeApp_frames_s.bin (colour-independent) and
# in the colour packs (bars, lit gear). The app only writes the screen that is on display (hmi.graphicalContext's
# menuTitle = the state's title).
# The screens themselves (ids, titles, slots) are the SCREEN_LIST entries below the slot lists.
# The entry button is a raAction: the app opens the screen used last with focusEvent SCREEN_EVENT0 + k (target state
# k), the way entry-aad opens its menu from its entry button (car-verified there).
ENTRY_ACTION = 6
SCREEN_EVENT0 = 90


def screen_parts(ox, oy):
    """XML of screens 1..3: models, actions, states (with their OPTION menus)."""
    models, states = [], []
    for scr in SCREEN_LIST:
        models.append(text_model(scr.text_model, scr.text_id))
    actions = ["      <hmiAction id=\"%d\" target=\"%d\"/>\n" % (scr.action, scr.state) for scr in SCREEN_LIST]
    for s, scr in enumerate(SCREEN_LIST[1:], 1):
        fn = scr.slots
        base = 1000 * s
        models.append("      <raImageModel id=\"%d\"/>\n" % (base + 99))
        comps = [image(base + 299, base + 99, props(ox, oy, sc(W), sc(H)))]
        for i, (_n, x, y, w, h) in enumerate(fn()):
            models.append("      <raImageModel id=\"%d\"/>\n" % (base + 100 + i))
            comps.append(image(base + 300 + i, base + 100 + i, props(sc(x) + ox, sc(y) + oy, sc(w), sc(h))))
        states.append((s, comps))
    return models, actions, states


def screen_options(_s, comp_ids):
    """OPTION menu of every screen: only Settings (the screens are chosen on the settings page). The HMI adds entries
    of its own above it ("Wylacz pojazd", ...)."""
    return ["          <button action=\"%d\" id=\"%d\" model=\"%d\" text=\"%s\"/>\n"
            % (OPTION_ACTION, next(comp_ids), OPTION_TEXTMODEL, TEXTS[XML_LANG]["settings_title"])]


def settings_screen_buttons(comp_ids):
    """The first buttons of the settings page: one per screen, each opening it (hmiAction to its state)."""
    return ["          <button action=\"%d\" id=\"%d\" model=\"%d\" text=\"%s\"/>\n"
            % (scr.action, next(comp_ids), scr.text_model, TEXTS[XML_LANG]["screen_titles"][k])
            for k, scr in enumerate(SCREEN_LIST)]


# ---- outputs --------------------------------------------------------------------------------------------------------
def props(x, y, w, h, selectable=False):
    """Image properties as entry-aad's EntryAad.xml writes them: 2 SELECTABLE, 3 VISIBLE, 9 WIDTH, 10 HEIGHT, 20 X, 21 Y."""
    return ("            <properties>\n"
            "              <property id=\"2\" value=\"%s\"/>\n"
            "              <property id=\"3\" value=\"true\"/>\n"
            "              <property id=\"9\" value=\"%d\"/>\n"
            "              <property id=\"10\" value=\"%d\"/>\n"
            "              <property id=\"20\" value=\"%d\"/>\n"
            "              <property id=\"21\" value=\"%d\"/>\n"
            "            </properties>\n" % ("true" if selectable else "false", w, h, x, y))


def text_model(mid, tid):
    return "      <textIdModel id=\"%d\" textId=\"%d\">\n        <synonyms/>\n      </textIdModel>\n" % (mid, tid)


def image(cid, mid, p=""):
    return "          <image id=\"%d\" model=\"%d\">\n%s          </image>\n" % (cid, mid, p)


def gauge_parts(slot_list, ox, oy):
    """Models and components of the gauge screen: the background (model 99) and slot i in model 100 + i, all
    raImageModels the app fills with frames of GaugeApp_frames.bin. Positions and sizes in pixels on the car."""
    models = ["      <raImageModel id=\"99\"/>\n"]
    comps = [image(299, 99, props(ox, oy, sc(W), sc(H)))]
    for i, (_n, x, y, w, h, _img) in enumerate(slot_list):
        models.append("      <raImageModel id=\"%d\"/>\n" % (100 + i))
        comps.append(image(300 + i, 100 + i, props(sc(x) + ox, sc(y) + oy, sc(w), sc(h))))
    return models, comps


def state(sid, title, text_model_id, comps, parent=None, options=None):
    opt = ("        <optionComponents>\n%s        </optionComponents>\n" % "".join(options)) if options else ""
    return ("      <hmiState id=\"%d\"%s text=\"%s\" textModel=\"%d\">\n%s        <components>\n%s        </components>\n"
            "      </hmiState>\n" % (sid, " parentId=\"%d\"" % parent if parent else "", title, text_model_id, opt,
                                    "".join(comps)))


# The settings page (hmiState 12), opened from the OPTION menu of the gauge screen (optionComponents). One button per
# setting: action 31 + s (raAction, handled by the app: next value), text model 41 + s (the app writes the text id of
# the current value), component 50 + s. The OPTION entry: hmiAction 7 -> state 12, text model 46, component 60.
SETTINGS_STATE, SETTINGS_ACTION0, SETTINGS_TEXTMODEL0, SETTINGS_COMP0 = 12, 31, 41, 50
OPTION_ACTION, OPTION_TEXTMODEL, OPTION_COMP = 7, 46, 60


def settings_parts():
    models = [text_model(SETTINGS_TEXTMODEL0 + s, base) for s, (base, _key) in enumerate(SETTING_KEYS)]
    models.append(text_model(OPTION_TEXTMODEL, TEXT_SETTINGS_TITLE))
    actions = ["      <raAction id=\"%d\"/>\n" % (SETTINGS_ACTION0 + s) for s in range(len(SETTING_KEYS))]
    actions.append("      <hmiAction id=\"%d\" target=\"%d\"/>\n" % (OPTION_ACTION, SETTINGS_STATE))
    buttons = ["          <button action=\"%d\" id=\"%d\" model=\"%d\" text=\"%s\"/>\n"
               % (SETTINGS_ACTION0 + s, SETTINGS_COMP0 + s, SETTINGS_TEXTMODEL0 + s, TEXTS[XML_LANG]["settings"][key][0])
               for s, (_base, key) in enumerate(SETTING_KEYS)]
    option = ["          <button action=\"%d\" id=\"%d\" model=\"%d\" text=\"%s\"/>\n"
              % (OPTION_ACTION, OPTION_COMP, OPTION_TEXTMODEL, TEXTS[XML_LANG]["settings_title"])]
    return models, actions, buttons, option


# Diagnostic build (make_db.py --diag-out DIR): the row opens a menu of test pages, to find out on the car what the HMI
# shows. Diagnostics 1 (car, EntryNav2): labels show; no image component showed anything, even the bare icon and a
# 549x484 picture set up exactly like entry-aad's - with the full 635-image DB. Diagnostics 2 tests the image paths
# one by one with a DB as small as entry-aad's.
# Diagnostics 2 (car): every image path works with a 3-image DB (imageId image, button icon, picture sent as data =
# raImage, labels); the 635-image DB was the problem. Diagnostics 3 checks what the layout can rely on: pixel positions
# and stacking (E1 imageId, E2 raImage), the largest picture (E3, a ruler), and pictures replaced 5 times a second (E4).
DIAG_PAGES = [(11, 10, "E1"), (12, 11, "E2"), (13, 12, "E3"), (14, 13, "E4")]   # state, text id, menu text
DIAG_TEXTS = {
    10: "E1: pozycje i nakladanie (imageId)",
    11: "E2: pozycje i nakladanie (raImage)",
    12: "E3: linijka 1280x560 (raImage)",
    13: "E4: animacja 5 klatek/s (raImage)",
}
DIAG_LAYOUT = [(0, 0, 549, 484), (20, 20, 63, 54), (700, 150, 63, 54)]   # card, icon on the card, icon to the right
WIDE_W, WIDE_H = 1280, 560


def xml(slot_list, ox, oy, diag=False, menu_name=DEFAULT_MENU):
    app_type = MENUS[menu_name]
    models = [text_model(3, 1), "      <imageIdModel id=\"4\" imageId=\"%d\"/>\n" % IMG_ICON]
    gm, gc = gauge_parts(slot_list, ox, oy)
    models += gm
    actions = ["      <hmiAction id=\"5\" target=\"10\"/>\n"]
    entry_action, events = 5, []
    if not diag:
        entry_action = ENTRY_ACTION
        actions = ["      <raAction id=\"%d\"/>\n" % ENTRY_ACTION]
        events = ["      <focusEvent id=\"%d\" target=\"%d\"/>\n" % (SCREEN_EVENT0 + k, sid)
                  for k, sid in enumerate(scr.state for scr in SCREEN_LIST)]
        sm, sa, sb, _so = settings_parts()
        models += sm
        actions += sa
        xm, xa, xs = screen_parts(ox, oy)
        models += xm
        actions += xa
        comp_ids = iter(range(600, 700))                 # OPTION buttons, screen buttons, separator
        # The settings page starts with the screens (like the colour, a choice made there), then the settings.
        page = settings_screen_buttons(comp_ids) + ["          <separator id=\"%d\"/>\n" % next(comp_ids)] + sb
        states = [state(10, TITLE, 3, gc, options=screen_options(0, comp_ids)),
                  state(SETTINGS_STATE, TEXTS[XML_LANG]["settings_title"], OPTION_TEXTMODEL, page, 10)]
        # The other screens are children of 10 (parentId) and the HMI shows the parent's OPTION entries in them too
        # (car-verified: an own Settings entry there appeared twice), so they get none of their own.
        for s, comps in xs:
            scr = SCREEN_LIST[s]
            states.append(state(scr.state, TEXTS[XML_LANG]["screen_titles"][s], scr.text_model, comps, 10))
        what = ("hmiState 10 (engine) is one background image and %d image components on top of it. The OPTION menu"
                " of every screen has one entry, Settings (hmiState 12); the settings page lists the screens - Engine"
                " 10, Driving 14, Fuel and trip 15, Performance 16, Warm-up 17, each its own background and images -"
                " then the settings" % len(slot_list))
    else:
        what = ("DIAGNOSTIC build 3: hmiState 10 is a menu of test pages E1..E4 (states 11..14). The gauge models stay"
                " (the app writes them) but have no components")
        menu, states = [], []
        for k, (sid, tid, label) in enumerate(DIAG_PAGES):
            models.append(text_model(510 + k, tid))
            actions.append("      <hmiAction id=\"%d\" target=\"%d\"/>\n" % (501 + k, sid))
            menu.append("          <button action=\"%d\" id=\"%d\" model=\"%d\" text=\"%s\"/>\n"
                        % (501 + k, 520 + k, 510 + k, label))
        models += ["      <imageIdModel id=\"541\" imageId=\"%d\"/>\n" % IMG_TEST,
                   "      <imageIdModel id=\"540\" imageId=\"%d\"/>\n" % IMG_ICON,
                   "      <imageIdModel id=\"542\" imageId=\"%d\"/>\n" % IMG_ICON]
        models += ["      <raImageModel id=\"%d\"/>\n" % m for m in (560, 561, 562, 563, 564, 565)]
        states.append(state(10, TITLE, 3, menu))
        states.append(state(11, "E1", 510, [image(530 + k, m, props(*DIAG_LAYOUT[k]))
                                            for k, m in enumerate((541, 540, 542))], 10))
        states.append(state(12, "E2", 511, [image(533 + k, m, props(*DIAG_LAYOUT[k]))
                                            for k, m in enumerate((560, 564, 565))], 10))
        states.append(state(13, "E3", 512, [image(536, 562, props(0, 0, WIDE_W, WIDE_H))], 10))
        states.append(state(14, "E4", 513, [image(537, 563, props(0, 0, 549, 484))], 10))
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<!-- GENERATED by make_db.py - edit the layout there. applicationType %s: %s (make_db.py, menu option).\n"
        "     entryButtonFocusID / applicationWeight differ from NBT-AAD's / entry-aad's so the apps can be installed\n"
        "     side by side. %s.\n"
        "     Each gauge image is bound to a raImageModel that libGaugeApp.so fills with PNG data from\n"
        "     GaugeApp_frames.bin (PluginApp::updateModel(model, bmw::Image)); the image DB only holds the row icon.\n"
        "     All ids (models, components, actions, states) are unique. -->\n"
        "<pluginApps>\n"
        "  <pluginApp applicationType=\"%s\" applicationWeight=\"210\" entryButtonFocusID=\"32751\" "
        "insertAfterFocusID=\"2270\" insertStateID=\"20\" text=\"%s\">\n"
        "    <comment/>\n"
        "    <entryButton action=\"%d\" id=\"1\" model=\"3\" imageModel=\"4\">\n      <properties/>\n    </entryButton>\n"
        "    <actions>\n%s    </actions>\n"
        "    <models>\n%s    </models>\n"
        "%s"
        "    <hmiStates>\n%s    </hmiStates>\n"
        "  </pluginApp>\n"
        "</pluginApps>\n" % (app_type, "the ConnectedDrive menu" if menu_name == "connected" else
                             "the Media/Radio list after the Bluetooth audio row", what, app_type, TITLE,
                             entry_action, "".join(actions), "".join(models),
                             "    <events>\n%s    </events>\n" % "".join(events) if events else "",
                             "".join(states)))
