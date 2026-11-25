// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// C++98 helpers shared by the pure headers and the plugin (QNX GCC 4.4 / armhf GCC 4.6 have no static_assert).
#ifndef GAUGE_COMPAT_HPP
#define GAUGE_COMPAT_HPP

// Fails the build (an array of size -1) when cond is false. Use it at namespace scope (a local typedef draws
// -Wunused-local-typedefs on newer compilers) for every table that must match an enum and every hand-sized buffer that
// must hold an object: a mismatch would otherwise only show on the car.
#define GA_STATIC_ASSERT(cond, name) typedef char ga_static_assert_##name[(cond) ? 1 : -1]

// Number of elements of a C array.
#define GA_COUNT(a) (sizeof(a) / sizeof((a)[0]))

#endif
