"""Light exposure -> circadian phase shift + melatonin suppression.

Light is the dominant zeitgeber.  Two effects:

* Phase shift (Khalsa et al. 2003 PRC, Zeitzer et al. 2000
  dose-response).  Saturating logistic in lux:

      sensitivity(lux) = 1 / (1 + (100 / lux)^k)    k ~ 1.5

  with half-max at ~ 100 lux and saturation ~ 1000 lux.  Phase
  shifts are negative (delay) for light before CBTmin (00:00-04:00
  for intermediate chronotypes) and positive (advance) for light
  after CBTmin (typically 04:00-12:00).

* Melatonin suppression.  Brainard 2001 / Lockley 2003: 50%
  suppression at ~ 100 lux (action spectrum peak around 460-480 nm,
  i.e. short-wavelength / blue).  We use an empirical curve

      suppression_pct = 100 * (1 - exp(-lux / 100))

References:
    Khalsa, Jewett, Cajochen, Czeisler 2003 J Physiol 549:945
    Zeitzer, Dijk, Kronauer, Brown, Czeisler 2000 J Physiol 526:695
    Brainard, Hanifin, Greeson 2001 J Neurosci 21:6405
    Lockley, Brainard, Czeisler 2003 J Clin Endocrinol Metab 88:4502
"""

from __future__ import annotations

import math


KHALSA_HALF_MAX_LUX = 100.0
KHALSA_K = 1.5
ZEITZER_DOSE_RESPONSE = (100.0, 1000.0)   # (half-max, saturation)


def _logistic_lux_response(lux: float, half_max: float = KHALSA_HALF_MAX_LUX,
                              k: float = KHALSA_K) -> float:
    """Fractional response on (0,1)."""
    if lux <= 0:
        return 0.0
    return 1.0 / (1.0 + (half_max / lux) ** k)


def light_phase_shift_h(lux:              float,
                          duration_h:       float,
                          clock_h_midpoint: float,
                          chronotype_msfsc_h: float = 4.0,
                          ) -> float:
    """Circadian phase shift (hours) from a light exposure of the
    given intensity, duration, and clock-time midpoint.

    Negative = delay (later sleep next night); positive = advance
    (earlier sleep next night).
    """
    cbt_min = (chronotype_msfsc_h - 1.0) % 24.0     # nadir clock-time
    resp = _logistic_lux_response(lux)               # 0..1 saturation
    # Convert midpoint to hours from CBTmin in [-12, +12]
    dt = (clock_h_midpoint - cbt_min) % 24.0
    if dt > 12:
        dt -= 24.0
    # Khalsa-type PRC: cosine-shape, max advance ~ +3 h centred ~ +5 h
    # after CBTmin, max delay ~ -3 h centred ~ -5 h before CBTmin.
    # We approximate by a half-sinusoid with two lobes.
    if dt > 0:
        # post-CBTmin: advance, peaking ~ +5 h after, returning to 0 by +12
        shape = max(0.0, math.sin(math.pi * dt / 12.0))
    else:
        shape = -max(0.0, math.sin(math.pi * (-dt) / 12.0))
    # Magnitude scaled by lux dose-response and duration (hours)
    max_shift_h = 2.0    # 9000 lux 6.5 h yields ~ 2 h shift (Khalsa 2003)
    return float(max_shift_h * resp * (duration_h / 6.5) * shape)


def melatonin_suppression_pct(lux: float) -> float:
    """Melatonin suppression (%) from sustained light exposure."""
    if lux <= 0:
        return 0.0
    return float(100.0 * (1.0 - math.exp(-lux / 100.0)))
