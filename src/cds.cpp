// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// CDS values in. PluginApp::cdsAddPropertyChangedEventHandler (the call NBT-AAD / entry-aad use for driving.gear)
// delivers the value as UTF-16 JSON text, without the property's name: one stub per property (onCds<P>). The first
// value is the current state, then only changes. Runs on the HMI's thread: parse, update the shared state, log - no
// files, nothing slow (the render tick writes).
#include <stdio.h>
#include <string.h>
#include "app.hpp"

namespace ga {
namespace {

void handleCds(int prop, const bmw::BasicString<unsigned short>& value) {
    char text[200];
    eng::narrow(value.raw(), text, sizeof(text));
    const long now = monoMs();
    bool ok, wasOk;
    int seen;
    int logScreen = -2;                                  // -1 / 0: the screen on display changed (logged below)
    bool logCal = false;                                 // the fuel counter was calibrated (logged below)
    int visibleNow = kVisUnknown;
    char title[96];
    double factor;
    {
        MutexLock lock(g_dataMutex);
        AppState& g = g_state;
        if (eng::apply(g.metrics, prop, text, now)) g.dirty = true;
        if (eng::updateMaxima(g.maxima, g.metrics, prop)) { g.dirty = true; g.maxDirty = true; }
        const eng::Metrics& m = g.metrics;
        switch (prop) {                                  // screens 1..4
        case eng::kSpeed:
            if (m.hasSpeed) { g.trip.speed(now, m.speed); g.perf.speed(now, m.speed); }
            else { g.trip.noSpeed(); g.perf.noSpeed(); }
            g.gmax.sample(m.hasLatG() && m.hasLonG(), m.hasLatG() ? m.latG() : 0, m.hasLonG() ? m.lonG() : 0);
            break;
        case eng::kAccel:
            g.gmax.sample(m.hasLatG() && m.hasLonG(), m.hasLatG() ? m.latG() : 0, m.hasLonG() ? m.lonG() : 0);
            break;
        case eng::kTorque:
            if (m.hasTorque && m.hasRpm) g.env.sample(m.rpm, m.torque);
            break;
        case eng::kRpm:
            if (m.hasTorque && m.hasRpm) g.env.sample(m.rpm, m.torque);
            g.warm.update(m, now);
            break;
        case eng::kEngineTemp:
        case eng::kEngineStatus:
            g.warm.update(m, now);
            break;
        case eng::kConsumption:
            if (m.hasConsumption) g.cal.addSteps(g.trip.counterValue(now, m.consumption));
            break;
        case eng::kFuel:
            if (m.hasFuel && g.cal.tank(m.fuel)) logCal = true;
            break;
        case eng::kBrake:
            if (m.hasBrake && m.brake > g.brakeFull) g.brakeFull = m.brake;
            break;
        case eng::kGraphic:
            if (m.hasTitle) {
                int v = screenForTitle(m.title);
                if (v < 0) v = strcmp(m.appType, "4") == 0 ? kVisSomeApp : kVisOther;
                if (v != g.visible) {
                    g.visible = v;
                    logScreen = v == kVisOther ? -1 : 0;
                    snprintf(title, sizeof(title), "%s' appType '%s", m.title, m.appType);
                    visibleNow = v;
                }
                if (v >= 0 && v != g.settings.screen) {  // remembered for the entry button
                    g.settings.screen = v;
                    g.settingsDirty = true;              // written on the next render tick
                }
            }
            break;
        }
        ok = eng::propValid(g.metrics, prop);
        seen = ++g.seen[prop];
        wasOk = g.lastOk[prop];
        g.lastOk[prop] = ok;
        ++g.totalSeen;
        factor = g.cal.factor;
    }
    if (logScreen >= -1)
        elog("on screen: '%s' -> %s", title, visibleNow >= 0 ? "a screen of this app" :
             visibleNow == kVisSomeApp ? "a plugin app (all screens written)" : "something else (nothing written)");
    if (logCal) elog("fuel counter calibrated from the tank level: %.3f ul per step", factor * 1e6);
    // The first values of every property are logged raw (that is what is needed to check a car's layout); after that
    // only a change between usable / not usable, so a revving engine does not flood the log.
    if (seen <= 5 || ok != wasOk) elog("CDS %s = '%s' -> %s", eng::propName(prop), text, ok ? "ok" : "not usable");
}

typedef bool (*CdsStub)(void*, const bmw::BasicString<unsigned short>&);

template <int P> bool onCds(void* /*app*/, const bmw::BasicString<unsigned short>& v) {
    handleCds(P, v);
    return true;
}

const CdsStub kStubs[] = { &onCds<0>, &onCds<1>, &onCds<2>, &onCds<3>, &onCds<4>, &onCds<5>, &onCds<6>, &onCds<7>,
                           &onCds<8>, &onCds<9>, &onCds<10>, &onCds<11>, &onCds<12>, &onCds<13>, &onCds<14>,
                           &onCds<15>, &onCds<16>, &onCds<17>, &onCds<18>, &onCds<19>, &onCds<20>, &onCds<21> };
GA_STATIC_ASSERT(GA_COUNT(kStubs) == eng::kPropCount, one_cds_stub_per_prop);

} // namespace

void subscribeAll(bmw::PluginApp* app) {
    for (int p = 0; p < eng::kPropCount; ++p) {
        bmw::BasicString<char> name(eng::propName(p));
        bmw::CdsDelegate d;
        d.object = app;
        d.stub = kStubs[p];
        app->cdsAddPropertyChangedEventHandler(name, 0, d);
        elog("CDS handler for %s registered", eng::propName(p));
    }
    MutexLock lock(g_dataMutex);
    g_state.subscribedAt = monoSec();
}

} // namespace ga
