// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// What the Driving / Fuel / Performance screens show beyond the raw CDS values - pure logic, host-tested in
// tests/test_cds_values.cpp. C++98.
//   GMax      the largest g per direction of this run (left, right, accelerating, braking)
//   TorqueEnv the largest torque seen per engine speed (kept in torque-env.txt): engine load = torque / envelope
//   FuelCal   litres per step of the engine.consumption counter, learned from the tank level (fuel-cal.txt)
//   Trip      distance, fuel and time since the app started, instant consumption, a 5-minute history
//   Perf      0-100, 60-100, 80-120 km/h, 1/4 mile and 100-0 km/h braking distance, timed from driving.speedActual
#ifndef GAUGE_DRIVE_STATS_HPP
#define GAUGE_DRIVE_STATS_HPP

#include "cds_values.hpp"

namespace eng {

// ---- g per direction ------------------------------------------------------------------------------------------------
// Two samples in a row are needed (the smaller one counts), like the maxima of the engine screen. Directions as the
// g-meter dot moves: + lat = right, + lon = down (accelerating, kLonSign).
enum GDir { kGLeft = 0, kGRight, kGAccel, kGBrake, kGDirCount };
struct GMax {
    bool   has[kGDirCount];
    double v[kGDirCount];
    bool   hasPrev;
    double prevLat, prevLon;
    GMax() : hasPrev(false), prevLat(0), prevLon(0) { for (int i = 0; i < kGDirCount; ++i) { has[i] = false; v[i] = 0; } }
    void put(int d, double x) {
        if (x <= 0) return;
        if (!has[d] || x > v[d]) { has[d] = true; v[d] = x; }
    }
    void sample(bool ok, double lat, double lon) {
        if (!ok) { hasPrev = false; return; }
        if (hasPrev) {
            double l = fabs(lat) < fabs(prevLat) ? lat : prevLat;   // the smaller of the two
            double o = fabs(lon) < fabs(prevLon) ? lon : prevLon;
            if (lat * prevLat > 0) put(l < 0 ? kGLeft : kGRight, fabs(l));
            if (lon * prevLon > 0) put(o > 0 ? kGAccel : kGBrake, fabs(o));
        }
        hasPrev = true;
        prevLat = lat;
        prevLon = lon;
    }
};

// ---- torque envelope (engine load) -----------------------------------------------------------------------------------
const int    kEnvBinRpm = 250;
const int    kEnvBins = 32;                       // 0..8000 rpm
const double kEnvMinNm = 60;                      // below this the envelope is not known yet: no load shown
struct TorqueEnv {
    double nm[kEnvBins];
    bool   hasPrev;
    int    prevBin;
    double prevNm;
    bool   changed;                               // since the file was written
    TorqueEnv() : hasPrev(false), prevBin(0), prevNm(0), changed(false) { for (int i = 0; i < kEnvBins; ++i) nm[i] = 0; }
    static int bin(double rpm) {
        int b = (int)(rpm / kEnvBinRpm);
        return b < 0 ? 0 : b >= kEnvBins ? kEnvBins - 1 : b;
    }
    // Torque and rpm of one moment (both known). Two samples in the same bin are needed.
    void sample(double rpm, double torque) {
        int b = bin(rpm);
        if (hasPrev && prevBin == b) {
            double t = torque < prevNm ? torque : prevNm;
            if (t > nm[b]) { nm[b] = t; changed = true; }
        }
        hasPrev = true;
        prevBin = b;
        prevNm = torque;
    }
    // The largest torque known around this engine speed (the bin and its neighbours).
    double at(double rpm) const {
        int b = bin(rpm);
        double m = nm[b];
        if (b > 0 && nm[b - 1] > m) m = nm[b - 1];
        if (b + 1 < kEnvBins && nm[b + 1] > m) m = nm[b + 1];
        return m;
    }
    // Engine load 0..100 %; false when not known (no torque / rpm, idle, envelope too small).
    bool load(const Metrics& m, double* out) const {
        if (!m.hasTorque || !m.hasRpm || m.rpm < 500) return false;
        double e = at(m.rpm);
        if (e < kEnvMinNm) return false;
        double l = m.torque <= 0 ? 0 : m.torque / e * 100.0;
        *out = l > 100 ? 100 : l;
        return true;
    }
};

// "env=0,0,...,310.0,..." (one number per bin)
inline void formatEnv(const TorqueEnv& e, char* out, size_t n) {
    size_t o = (size_t)snprintf(out, n, "env=");
    for (int i = 0; i < kEnvBins && o < n; ++i) {
        int w = snprintf(out + o, n - o, i ? ",%.0f" : "%.0f", e.nm[i]);
        if (w < 0) break;
        o += (size_t)w;
    }
    if (o < n) snprintf(out + o, n - o, "\n");
}
inline void parseEnv(TorqueEnv& e, const char* text) {
    const char* p = strstr(text, "env=");
    if (!p) return;
    p += 4;
    for (int i = 0; i < kEnvBins; ++i) {
        char* end = NULL;
        double v = strtod(p, &end);
        if (end == p) break;
        if (v >= 0 && v < 3000) e.nm[i] = v;
        p = end;
        if (*p != ',') break;
        ++p;
    }
}

// ---- fuel: litres per counter step ------------------------------------------------------------------------------------
// engine.consumption counts injected fuel; its unit is not documented. 1 ul per step matches the idle of a cold
// 2.0 l engine on the EntryNav2 F40 (about 550 steps/s); the real factor is learned from the tank level: every time
// the level has dropped by kCalLitres since an anchor, factor = litres / steps (averaged with the previous one).
const double kFuelPerStepDefault = 1e-6;          // litres
const double kCalLitres = 8;                      // tank level drop needed for one calibration (level is in litres)
struct FuelCal {
    double factor;
    int    calibrations;
    bool   hasAnchor;
    double anchorTank, steps;                     // tank level at the anchor, counter steps since then
    bool   changed;
    FuelCal() : factor(kFuelPerStepDefault), calibrations(0), hasAnchor(false), anchorTank(0), steps(0),
                changed(false) {}
    void addSteps(double s) { if (hasAnchor) { steps += s; changed = true; } }
    // A tank level reading. Returns true when the factor changed.
    bool tank(double litres) {
        if (!hasAnchor || litres > anchorTank + 2) {           // first reading or refuelled: start again
            hasAnchor = true; anchorTank = litres; steps = 0; changed = true;
            return false;
        }
        if (anchorTank - litres < kCalLitres || steps < 1000) return false;
        double f = (anchorTank - litres) / steps;
        bool ok = f > 1e-8 && f < 1e-4;                         // 0.01 .. 100 ul per step
        if (ok) {
            factor = calibrations ? 0.5 * factor + 0.5 * f : f;
            ++calibrations;
        }
        anchorTank = litres;
        steps = 0;
        changed = true;
        return ok;
    }
};

inline void formatCal(const FuelCal& c, char* out, size_t n) {
    snprintf(out, n, "factor=%.6e\ncalibrations=%d\nanchor=%.1f\nsteps=%.0f\n", c.factor, c.calibrations,
             c.hasAnchor ? c.anchorTank : -1.0, c.steps);
}
inline void parseCal(FuelCal& c, const char* text) {
    double v;
    const char* p;
    if ((p = strstr(text, "factor=")) != NULL) { v = strtod(p + 7, NULL); if (v > 1e-8 && v < 1e-4) c.factor = v; }
    if ((p = strstr(text, "calibrations=")) != NULL) { long k = strtol(p + 13, NULL, 10); if (k >= 0 && k < 100000) c.calibrations = (int)k; }
    if ((p = strstr(text, "anchor=")) != NULL) {
        v = strtod(p + 7, NULL);
        if (v >= 0 && v < 200) { c.hasAnchor = true; c.anchorTank = v; }
    }
    if ((p = strstr(text, "steps=")) != NULL) { v = strtod(p + 6, NULL); if (v >= 0 && v < 1e12) c.steps = v; }
}

// ---- the trip (since the app started) ---------------------------------------------------------------------------------
const long kBarMs = 10000;                        // one history bar = 10 s
enum { kTripBars = 30, kTripWin = 32 };
struct Trip {
    long   startMs;
    double km;
    bool   hasSpeed;
    long   speedMs;
    double speedKmh;
    bool   hasCounter;
    unsigned counter;                             // last raw value
    double steps;                                 // counter steps since the start
    long   winMs[kTripWin];                       // recent counter readings (for the instant consumption)
    double winSteps[kTripWin];
    int    winCount, winHead;
    double bars[kTripBars];                       // l/100 km per 10 s, oldest first
    int    barCount;
    long   barStartMs;
    double barSteps0, barKm0;
    Trip() { reset(0); }
    void reset(long now) {
        startMs = now; km = 0; hasSpeed = false; speedMs = 0; speedKmh = 0; hasCounter = false; counter = 0;
        steps = 0; winCount = 0; winHead = 0; barCount = 0; barStartMs = now; barSteps0 = 0; barKm0 = 0;
        for (int i = 0; i < kTripBars; ++i) bars[i] = 0;
    }
    void speed(long ms, double kmh) {
        if (hasSpeed) {
            long dt = ms - speedMs;
            if (dt > 0 && dt <= 3000) km += (speedKmh + kmh) / 2.0 * dt / 3600000.0;
        }
        hasSpeed = true; speedMs = ms; speedKmh = kmh;
    }
    void noSpeed() { hasSpeed = false; }
    // A raw engine.consumption reading. Returns the steps added (0 for the first one or a jump).
    double counterValue(long ms, unsigned raw) {
        double d = 0;
        if (hasCounter) {
            unsigned diff = (raw - counter) & 0xffffu;            // the counter wraps at 65536
            if (diff < 30000) d = diff;                           // bigger: a reset of the counter (engine start)
        }
        hasCounter = true;
        counter = raw;
        steps += d;
        winMs[winHead] = ms;
        winSteps[winHead] = steps;
        winHead = (winHead + 1) % kTripWin;
        if (winCount < kTripWin) ++winCount;
        return d;
    }
    // Litres per hour over the last ~2 s. The counter only sends changes: no reading for a while = no fuel (overrun
    // or engine off). false before the first readings.
    bool litresPerHour(long now, double factor, double* out) const {
        if (winCount < 2) return false;
        int last = (winHead + kTripWin - 1) % kTripWin;
        if (now - winMs[last] > 1500) { *out = 0; return true; }
        int ref = -1;
        for (int k = 1; k < winCount; ++k) {                      // newest first: the first reading >= 2 s old
            int i = (last + kTripWin - k) % kTripWin;
            ref = i;
            if (now - winMs[i] >= 2000) break;
        }
        if (ref < 0) return false;
        long dt = now - winMs[ref];
        if (dt < 500) return false;
        *out = (steps - winSteps[ref]) * factor / (dt / 3600000.0);
        return true;
    }
    // Called every render tick: closes a history bar every 10 s.
    void tick(long now, double factor) {
        if (now - barStartMs < kBarMs) return;
        double dkm = km - barKm0;
        double v = dkm >= 0.02 ? (steps - barSteps0) * factor / dkm * 100.0 : 0;
        if (barCount == kTripBars) {
            for (int i = 1; i < kTripBars; ++i) bars[i - 1] = bars[i];
            bars[kTripBars - 1] = v;
        } else {
            bars[barCount++] = v;
        }
        barStartMs = now;
        barSteps0 = steps;
        barKm0 = km;
    }
    double litres(double factor) const { return steps * factor; }
    long minutes(long now) const { return (now - startMs) / 60000; }
};

// ---- performance timing ----------------------------------------------------------------------------------------------
// From driving.speedActual (whole km/h). Threshold crossings are interpolated between two readings; a run starts at the
// last reading at standstill. Results are ms (times) or metres (braking), -1 = none yet.
enum PerfStatus { kPerfNoData = 0, kPerfReady, kPerfRunning, kPerfStop, kPerfBraking, kPerfStatusCount };
const double kQuarterMile = 402.336;              // m
const long   kRunMaxMs = 60000;
struct Perf {
    long   r0100, best0100, r60100, r80120, rQuarter;
    double rBrake;                                // 100-0 km/h, m
    bool   hasPrev;
    long   prevMs;
    double prevV;
    bool   atRest;                                // the last reading was 0 km/h
    bool   run, done100, doneQuarter;
    long   runStart;
    double runDist, runPeak;
    bool   roll60, roll80;
    long   t60, t80;
    bool   brk;
    long   brkStart;
    double brkDist, brkMin;
    Perf() : r0100(-1), best0100(-1), r60100(-1), r80120(-1), rQuarter(-1), rBrake(-1) { clearRun(); }
    void clearRun() {
        hasPrev = false; prevMs = 0; prevV = 0; atRest = false; run = false; done100 = false; doneQuarter = false;
        runStart = 0; runDist = 0; runPeak = 0; roll60 = false; roll80 = false; t60 = 0; t80 = 0; brk = false;
        brkStart = 0; brkDist = 0; brkMin = 0;
    }
    long cross(long ms, double v, double th) const {   // when the speed passed th between the last two readings
        if (v == prevV) return ms;
        return prevMs + (long)((th - prevV) / (v - prevV) * (double)(ms - prevMs));
    }
    void noSpeed() { clearRun(); }
    void speed(long ms, double v) {
        if (!hasPrev || ms - prevMs > 3000 || ms <= prevMs) {   // first reading or a gap: nothing to time
            clearRun();
            hasPrev = true; prevMs = ms; prevV = v; atRest = v == 0;
            return;
        }
        const double step = (prevV + v) / 2.0 / 3.6 * (double)(ms - prevMs) / 1000.0;   // metres
        // 0-100 / 1/4 mile
        if (atRest && prevV == 0 && v > 0) {
            run = true; done100 = false; doneQuarter = false; runStart = prevMs; runDist = 0; runPeak = 0;
        }
        if (run) {
            runDist += step;
            if (v > runPeak) runPeak = v;
            if (!done100 && prevV < 100 && v >= 100) {
                r0100 = cross(ms, v, 100) - runStart;
                if (best0100 < 0 || r0100 < best0100) best0100 = r0100;
                done100 = true;
            }
            if (!doneQuarter && runDist >= kQuarterMile) {
                double over = runDist - kQuarterMile;         // metres past the line at this reading
                long back = v > 0 ? (long)(over / (v / 3.6) * 1000.0) : 0;
                rQuarter = ms - back - runStart;
                doneQuarter = true;
            }
            if (v < runPeak - 3 || v == 0 || ms - runStart > kRunMaxMs || (done100 && doneQuarter)) run = false;
        }
        // rolling 60-100 / 80-120
        if (prevV < 60 && v >= 60) { roll60 = true; t60 = cross(ms, v, 60); }
        if (roll60 && v < 55) roll60 = false;
        if (roll60 && prevV < 100 && v >= 100) { r60100 = cross(ms, v, 100) - t60; roll60 = false; }
        if (prevV < 80 && v >= 80) { roll80 = true; t80 = cross(ms, v, 80); }
        if (roll80 && v < 75) roll80 = false;
        if (roll80 && prevV < 120 && v >= 120) { r80120 = cross(ms, v, 120) - t80; roll80 = false; }
        // 100-0
        if (brk) {
            brkDist += step;
            if (v < brkMin) brkMin = v;
            if (v == 0) { rBrake = brkDist; brk = false; }
            else if (v > brkMin + 3 || ms - brkStart > kRunMaxMs) brk = false;
        }
        if (!brk && prevV > 100 && v <= 100 && v > 0) {
            brk = true; brkStart = ms; brkMin = v;
            brkDist = step * (100 - v) / (prevV - v);           // the part of the step after 100 km/h
        }
        hasPrev = true; prevMs = ms; prevV = v; atRest = v == 0;
    }
    PerfStatus status() const {
        if (!hasPrev) return kPerfNoData;
        if (run) return kPerfRunning;
        if (brk) return kPerfBraking;
        if (prevV == 0) return kPerfReady;
        return kPerfStop;
    }
    // ms since the run started (the clock on screen while timing).
    long elapsed(long now) const { return run ? now - runStart : 0; }
};

// ---- warm-up -----------------------------------------------------------------------------------------------------------
// Engine running = engine.status 2 (seen 0 -> 1 -> 2 at a start), or engine speed above 400 when the status is not sent.
// Warm = oil at kWarmOilTarget. The time to warm is estimated from how fast the oil warmed over the last minutes.
enum WarmStatus { kWarmNoData = 0, kWarmOff, kWarmWarming, kWarmReady, kWarmStatusCount };
const double kWarmOilTarget = 80;                 // deg C: full load from here (a common rule for BMW engines)
const long   kWarmRateMinMs = 60000;              // at least this much history for an estimate
const long   kWarmRateMaxMs = 300000;             // and at most this much
enum { kWarmHist = 32 };
struct WarmUp {
    bool   running;
    long   runStartMs;
    bool   hasStartOil;
    double startOil;
    long   histMs[kWarmHist];
    double histOil[kWarmHist];
    int    histCount, histHead;
    WarmUp() { reset(); }
    void reset() { running = false; runStartMs = 0; hasStartOil = false; startOil = 0; histCount = 0; histHead = 0; }
    static bool isRunning(const Metrics& m) {
        if (m.hasEngineStatus) return m.engineStatus == 2;
        return m.hasRpm && m.rpm > 400;
    }
    // After every engine.status / RPMSpeed / engine.temperature value.
    void update(const Metrics& m, long now) {
        bool r = isRunning(m);
        if (r && !running) { runStartMs = now; hasStartOil = false; histCount = 0; histHead = 0; }
        running = r;
        if (!running || !m.hasOil) return;
        if (!hasStartOil) { hasStartOil = true; startOil = m.oil; }
        int last = (histHead + kWarmHist - 1) % kWarmHist;
        if (histCount && histOil[last] == m.oil) return;           // only changes are kept
        histMs[histHead] = now;
        histOil[histHead] = m.oil;
        histHead = (histHead + 1) % kWarmHist;
        if (histCount < kWarmHist) ++histCount;
    }
    WarmStatus status(const Metrics& m) const {
        if (!m.hasOil) return kWarmNoData;
        if (!running) return kWarmOff;
        return m.oil >= kWarmOilTarget ? kWarmReady : kWarmWarming;
    }
    // 0..1 from the oil temperature at the start to the target.
    double progress(const Metrics& m) const {
        if (!m.hasOil) return 0;
        if (m.oil >= kWarmOilTarget) return 1;
        double s = hasStartOil && startOil < kWarmOilTarget ? startOil : m.oil;
        double f = (m.oil - s) / (kWarmOilTarget - s);
        return f < 0 ? 0 : f > 1 ? 1 : f;
    }
    long runMinutes(long now) const { return running ? (now - runStartMs) / 60000 : 0; }
    // Minutes until warm; false when it cannot be told yet (too little history, not warming).
    bool minutesLeft(const Metrics& m, long now, double* out) const {
        if (status(m) == kWarmReady) { *out = 0; return true; }
        if (status(m) != kWarmWarming || histCount < 2) return false;
        int last = (histHead + kWarmHist - 1) % kWarmHist;
        int ref = -1;
        for (int k = histCount - 1; k >= 1; --k) {                 // the oldest reading inside the window
            int i = (last + kWarmHist - k) % kWarmHist;
            if (now - histMs[i] <= kWarmRateMaxMs) { ref = i; break; }
        }
        if (ref < 0 || now - histMs[ref] < kWarmRateMinMs) return false;
        double rate = (m.oil - histOil[ref]) / (double)(now - histMs[ref]);   // deg per ms
        if (rate <= 0) return false;
        *out = (kWarmOilTarget - m.oil) / rate / 60000.0;
        return true;
    }
};

} // namespace eng
#endif
