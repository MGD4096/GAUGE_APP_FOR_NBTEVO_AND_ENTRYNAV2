// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Engine data for BMW NBT Evo / EntryNav2 - pure logic, no iDrive framework: parsing of CDS property texts, derived
// values (power, longitudinal g from the speed) and the all-time maxima. Host-tested in tests/test_cds_values.cpp.
// C++98 (the QNX SDP 6.5 compiler is GCC 4.4).
//
// The parsing style (key lookup in the JSON-like text the car sends as UTF-16) follows NBT-AAD's rhmiapp/cds_parse.hpp
// (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto). CDS property names and value layouts come from
// https://bimmergestalt.github.io/BMWConnectedAnalysis/cds/ (a community list: units partly "probably"):
//   engine.temperature    {"temperature":{"engine":19,"oil":18}}                         deg C
//   engine.RPMSpeed       {"RPMSpeed":0}                                                 1/min
//   engine.torque         {"torque":0}                                                   Nm
//   driving.gear          {"gear":0}                                                     1 N, 2 R, 3 P, 4+ D1+
//   driving.acceleration  {"acceleration":{"lateral":-0.19,"longitudinal":65535.00}}     probably m/s^2
//   driving.speedActual   {"speedActual":0}                                              km/h
//   sensors.fuel          {"fuel":{"range":522,"reserve":0,"tanklevel":39}}              litres (tanklevel)
//   vehicle.language      {"language":3}                     1 DE, 2 EN_UK, 3 EN_US, ... 18 PL (HMI language)
// There is no engine power in CDS: it is torque * rpm. When the car sends no usable longitudinal acceleration (the list
// shows 65535, a "not available" value), it is taken from the change of speedActual instead.
// A value that is missing, not a number or outside a plausible range counts as "no data" (e.g. {"error":400}).
#ifndef NBT_ENGINE_CDS_VALUES_HPP
#define NBT_ENGINE_CDS_VALUES_HPP

#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

namespace eng {

// CDS properties the app subscribes to (index = Prop).
enum Prop { kEngineTemp = 0, kRpm, kTorque, kGear, kAccel, kSpeed, kFuel, kLanguage, kPropCount };

const int kLangPolish = 18;          // vehicle.language: the texts drawn into the pictures are Polish for it, else English

inline const char* propName(int p) {
    switch (p) {
    case kEngineTemp: return "engine.temperature";
    case kRpm:        return "engine.RPMSpeed";
    case kTorque:     return "engine.torque";
    case kGear:       return "driving.gear";
    case kAccel:      return "driving.acceleration";
    case kSpeed:      return "driving.speedActual";
    case kFuel:       return "sensors.fuel";
    case kLanguage:   return "vehicle.language";
    }
    return "";
}

// ---- tuning ---------------------------------------------------------------------------------------------------------
const double kAccelPerG = 9.81;      // driving.acceleration in m/s^2 (the CDS list says "probably m/s"); 1.0 if in g
const double kLatSign = 1.0;         // flip to -1 if the g-meter dot moves the wrong way in a bend
const double kLonSign = 1.0;         // + : the dot moves down when accelerating, up when braking
const double kPsPerNmRpm = 1.0 / 7023.5;   // PS (KM) = Nm * 1/min / 7023.5

// UTF-16 (as the car delivers CDS values) -> ASCII; anything above 0x7f becomes '?'. Returns the length.
inline size_t narrow(const unsigned short* in, char* out, size_t n) {
    size_t i = 0;
    if (!out || n == 0) return 0;
    while (in && in[i] && i < n - 1) {
        out[i] = in[i] < 0x80 ? (char)in[i] : '?';
        ++i;
    }
    out[i] = 0;
    return i;
}

// Number after "<key>": in text. false when the key is missing, the value is not a number (null, string, ...) or
// not finite. Accepts integers and decimals.
inline bool numField(const char* text, const char* key, double* out) {
    if (!text || !key || !out) return false;
    char pat[48];
    size_t kl = strlen(key);
    if (kl + 3 > sizeof(pat)) return false;
    pat[0] = '"';
    memcpy(pat + 1, key, kl);
    pat[kl + 1] = '"';
    pat[kl + 2] = 0;
    const char* p = strstr(text, pat);
    if (!p) return false;
    p += kl + 2;
    while (*p == ' ' || *p == ':') ++p;
    if (!(*p == '-' || *p == '.' || (*p >= '0' && *p <= '9'))) return false;
    char* end = NULL;
    double v = strtod(p, &end);
    if (end == p) return false;
    if (!(v > -1e9 && v < 1e9)) return false;           // also rejects NaN and infinity
    *out = v;
    return true;
}

inline bool inRange(double v, double lo, double hi) { return v >= lo && v <= hi; }

// Latest known values. A has* flag is false until a valid value arrived and again after an invalid one.
struct Metrics {
    bool   hasCoolant, hasOil, hasRpm, hasTorque, hasGear, hasLat, hasLon, hasSpeed, hasLonFromSpeed, hasFuel;
    double coolant, oil, rpm, torque, lat, lon, speed, lonFromSpeed;   // lat / lon / lonFromSpeed in m/s^2
    double fuel;                                     // litres in the tank
    int    gear;
    int    language;                                 // vehicle.language, 0 = not known yet
    long   speedAtMs;                                // when speed was received
    Metrics()
        : hasCoolant(false), hasOil(false), hasRpm(false), hasTorque(false), hasGear(false), hasLat(false),
          hasLon(false), hasSpeed(false), hasLonFromSpeed(false), hasFuel(false), coolant(0), oil(0), rpm(0),
          torque(0), lat(0), lon(0), speed(0), lonFromSpeed(0), fuel(0), gear(0), language(0), speedAtMs(0) {}

    // Texts in the pictures: Polish until the language is known (the car this was made for), then Polish only for
    // a Polish HMI.
    bool polish() const { return language == 0 || language == kLangPolish; }

    bool hasPower() const { return hasTorque && hasRpm; }
    double power() const { return (torque > 0 ? torque : 0) * rpm * kPsPerNmRpm; }   // KM, 0 on overrun
    bool hasLatG() const { return hasLat; }
    double latG() const { return kLatSign * lat / kAccelPerG; }
    bool hasLonG() const { return hasLon || hasLonFromSpeed; }
    double lonG() const { return kLonSign * (hasLon ? lon : lonFromSpeed) / kAccelPerG; }
};

// Stores one value; returns true when it changed.
inline bool setValue(bool& has, double& cur, bool ok, double v) {
    if (!ok) { bool ch = has; has = false; return ch; }
    bool ch = !has || cur != v;
    has = true;
    cur = v;
    return ch;
}

// Applies the text of one CDS property to m (nowMs: a monotonic clock, for the speed derivative). Returns true when a
// value changed. Note: ok is computed in its own statement; passing numField(.., &v) and v in one call would read v
// before it is set (the order in which function arguments are evaluated is unspecified).
inline bool apply(Metrics& m, int prop, const char* text, long nowMs) {
    double v = 0;
    bool ch = false;
    switch (prop) {
    case kEngineTemp: {
        bool a = numField(text, "engine", &v) && inRange(v, -40, 200);
        ch = setValue(m.hasCoolant, m.coolant, a, v) || ch;
        v = 0;
        bool b = numField(text, "oil", &v) && inRange(v, -40, 250);
        ch = setValue(m.hasOil, m.oil, b, v) || ch;
        break;
    }
    case kRpm: {
        bool ok = numField(text, "RPMSpeed", &v) && inRange(v, 0, 12000);
        ch = setValue(m.hasRpm, m.rpm, ok, v);
        break;
    }
    case kTorque: {
        bool ok = numField(text, "torque", &v) && inRange(v, -1000, 2000);
        ch = setValue(m.hasTorque, m.torque, ok, v);
        break;
    }
    case kGear: {
        bool ok = numField(text, "gear", &v) && inRange(v, 0, 30);
        int g = ok ? (int)v : 0;
        ch = (m.hasGear != ok) || (ok && m.gear != g);
        m.hasGear = ok;
        if (ok) m.gear = g;
        break;
    }
    case kAccel: {
        bool a = numField(text, "lateral", &v) && inRange(v, -30, 30);
        ch = setValue(m.hasLat, m.lat, a, v) || ch;
        v = 0;
        bool b = numField(text, "longitudinal", &v) && inRange(v, -30, 30);
        ch = setValue(m.hasLon, m.lon, b, v) || ch;
        break;
    }
    case kSpeed: {
        bool ok = numField(text, "speedActual", &v) && inRange(v, 0, 500);
        if (ok && m.hasSpeed) {
            long dt = nowMs - m.speedAtMs;
            if (dt >= 50 && dt <= 2000) {
                double a = (v - m.speed) / 3.6 / (dt / 1000.0);
                if (a < -30) a = -30;
                if (a > 30) a = 30;
                double s = m.hasLonFromSpeed ? 0.5 * m.lonFromSpeed + 0.5 * a : a;   // smooths the 1 km/h steps
                ch = setValue(m.hasLonFromSpeed, m.lonFromSpeed, true, s) || ch;
            } else if (dt > 2000) {
                ch = setValue(m.hasLonFromSpeed, m.lonFromSpeed, false, 0) || ch;
            } else {
                return ch;                           // too close to the last one: keep it as the reference
            }
        } else if (!ok) {
            ch = setValue(m.hasLonFromSpeed, m.lonFromSpeed, false, 0) || ch;
        }
        ch = setValue(m.hasSpeed, m.speed, ok, v) || ch;
        if (ok) m.speedAtMs = nowMs;
        break;
    }
    case kFuel: {
        bool ok = numField(text, "tanklevel", &v) && inRange(v, 0, 200);
        ch = setValue(m.hasFuel, m.fuel, ok, v);
        break;
    }
    case kLanguage: {
        bool ok = numField(text, "language", &v) && inRange(v, 1, 99);
        int lang = ok ? (int)v : m.language;         // an invalid value keeps the last known language
        ch = lang != m.language;
        m.language = lang;
        break;
    }
    }
    return ch;
}

// Is anything usable for this property (diagnostics only).
inline bool propValid(const Metrics& m, int prop) {
    switch (prop) {
    case kEngineTemp: return m.hasCoolant || m.hasOil;
    case kRpm:        return m.hasRpm;
    case kTorque:     return m.hasTorque;
    case kGear:       return m.hasGear;
    case kAccel:      return m.hasLat || m.hasLon;
    case kSpeed:      return m.hasSpeed;
    case kFuel:       return m.hasFuel;
    case kLanguage:   return m.language != 0;
    }
    return false;
}

// ---- maxima of the current run (reset when the app starts; the last run's are kept in max.txt) ----------------------
enum Gauge { kGCoolant = 0, kGOil, kGPower, kGTorque, kGaugeCount };

inline const char* gaugeKey(int g) {
    switch (g) {
    case kGCoolant: return "coolant";
    case kGOil:     return "oil";
    case kGPower:   return "power";
    case kGTorque:  return "torque";
    }
    return "";
}

// A new maximum needs two samples in a row: max = max(max, min(previous, current)). One glitch (a single bogus value)
// can then not become the record of the run.
struct Maxima {
    bool   has[kGaugeCount], hasPrev[kGaugeCount];
    double v[kGaugeCount], prev[kGaugeCount];
    Maxima() {
        for (int g = 0; g < kGaugeCount; ++g) { has[g] = hasPrev[g] = false; v[g] = prev[g] = 0; }
    }
    // One sample of gauge g (ok = false: no data). Returns true when the maximum changed.
    bool sample(int g, bool ok, double x) {
        if (!ok) { hasPrev[g] = false; return false; }
        bool changed = false;
        if (hasPrev[g]) {
            double c = prev[g] < x ? prev[g] : x;
            if (!has[g] || c > v[g]) { has[g] = true; v[g] = c; changed = true; }
        }
        hasPrev[g] = true;
        prev[g] = x;
        return changed;
    }
};

// Feeds the maxima from the values one CDS property just changed. Returns true when a maximum changed.
inline bool updateMaxima(Maxima& mx, const Metrics& m, int prop) {
    bool ch = false;
    switch (prop) {
    case kEngineTemp:
        ch = mx.sample(kGCoolant, m.hasCoolant, m.coolant) || ch;
        ch = mx.sample(kGOil, m.hasOil, m.oil) || ch;
        break;
    case kTorque:
        ch = mx.sample(kGTorque, m.hasTorque, m.torque) || ch;
        ch = mx.sample(kGPower, m.hasPower(), m.power()) || ch;
        break;
    case kRpm:
        ch = mx.sample(kGPower, m.hasPower(), m.power()) || ch;
        break;
    }
    return ch;
}

// "coolant=98.0\noil=112.0\n..." - only the maxima that exist.
inline void formatMaxima(const Maxima& mx, char* out, size_t n) {
    size_t o = 0;
    out[0] = 0;
    for (int g = 0; g < kGaugeCount && o < n; ++g) {
        if (!mx.has[g]) continue;
        int w = snprintf(out + o, n - o, "%s=%.1f\n", gaugeKey(g), mx.v[g]);
        if (w < 0) break;
        o += (size_t)w;
    }
}

// Reads what formatMaxima wrote; unknown or broken lines are skipped.
inline void parseMaxima(Maxima& mx, const char* text) {
    for (int g = 0; g < kGaugeCount; ++g) {
        char key[24];
        snprintf(key, sizeof(key), "%s=", gaugeKey(g));
        const char* p = text;
        while ((p = strstr(p, key)) != NULL) {
            if (p == text || p[-1] == '\n') break;
            p += 1;
        }
        if (!p) continue;
        char* end = NULL;
        double v = strtod(p + strlen(key), &end);
        if (end == p + strlen(key) || !(v > -1000 && v < 5000)) continue;
        mx.has[g] = true;
        mx.v[g] = v;
    }
}

inline int roundInt(double v) { return (int)(v >= 0 ? v + 0.5 : v - 0.5); }

}  // namespace eng

#endif
