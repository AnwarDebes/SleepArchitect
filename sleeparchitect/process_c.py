"""Process C: circadian propensity to sleep.

We use the two-harmonic sinusoid form from Daan, Beersma & Borbely
1984:

    C(t) = a1 * sin(2 pi t / 24) + a2 * sin(4 pi t / 24)

with a1 = 0.12, a2 = 0.04, t measured in hours past the circadian
nadir (the body-temperature minimum, ~ 04:00 in intermediate
chronotypes).  The sleep / wake thresholds are then

    H_upper = 0.6  + C(t) * 0.1     (transition to sleep when S > H_upper)
    H_lower = 0.17 + C(t) * 0.1     (transition to wake when S < H_lower)

For chronotype individualisation we shift the C-phase by
(MSFsc_h - 4.0) so that an extreme lark (MSFsc 02:00) has a 2-hour
earlier nadir, and an extreme owl (MSFsc 07:00) a 3-hour later nadir.

References:
    Borbely & Achermann 1999 J Biol Rhythms
    Daan, Beersma & Borbely 1984 Am J Physiol 246:R161
    Skeldon et al. 2017 Sci Rep 7:45158
"""

from __future__ import annotations

import math

import numpy as np


SLEEP_UPPER_THRESHOLD_BASE = 0.60   # H_upper = base + 0.1 * C
SLEEP_LOWER_THRESHOLD_BASE = 0.17
C_AMPLITUDE_1ST_HARMONIC = 0.12
C_AMPLITUDE_2ND_HARMONIC = 0.04


def circadian_C_at_phase(clock_h: float, chronotype_msfsc_h: float = 4.0
                            ) -> float:
    """Process C value at clock-time clock_h (hours past midnight)
    for a user with chronotype MSFsc."""
    # Population-average nadir is ~ 04:00 for intermediate chronotype.
    nadir_h = chronotype_msfsc_h - 1.0   # nadir is ~ 1 h before MSFsc
    t_rel = (clock_h - nadir_h) % 24.0
    return (C_AMPLITUDE_1ST_HARMONIC * math.sin(2 * math.pi * t_rel / 24.0)
            + C_AMPLITUDE_2ND_HARMONIC * math.sin(4 * math.pi * t_rel / 24.0))


def monthly_phase_for_chronotype(chronotype_msfsc_h: float) -> float:
    """Return the nadir (CBTmin) in clock-hours for this chronotype.
    Used by light PRC to determine advance vs delay."""
    return (chronotype_msfsc_h - 1.0) % 24.0


def H_upper(clock_h: float, chronotype_msfsc_h: float = 4.0) -> float:
    return SLEEP_UPPER_THRESHOLD_BASE + 0.1 * circadian_C_at_phase(clock_h, chronotype_msfsc_h)


def H_lower(clock_h: float, chronotype_msfsc_h: float = 4.0) -> float:
    return SLEEP_LOWER_THRESHOLD_BASE + 0.1 * circadian_C_at_phase(clock_h, chronotype_msfsc_h)


SLEEP_UPPER_THRESHOLD = H_upper
SLEEP_LOWER_THRESHOLD = H_lower
