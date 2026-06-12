"""SAFTE-style alertness model for tomorrow.

Sleep, Activity, Fatigue, and Task Effectiveness (Hursh et al.
2004 / Mallis et al. 2004): three additive components on a 0-100
effectiveness scale.

    Reservoir R(t):     Sleep credit. Replenished during sleep at
                            rate proportional to sleep intensity;
                            depleted during wake at K = 0.5 unit-min/min.
                            Capacity R_c = 2880 unit-min (48 hours of
                            depletion to empty).

    Circadian C(t):     Sinusoidal modulation, peaks ~ 18-20 h,
                            troughs ~ 04-06 h.  Amplitude ~ +/- 8.

    Inertia I(t):       Wake-from-sleep transient. Decays
                            exponentially with t_h_after_wake; magnitude
                            scales with sleep depth at wake.

    E(t) = 100 * R(t) / R_c + C(t) + I(t)

The Karolinska Sleepiness Scale (KSS, 1-9) is the simplest
operational metric.  We map E -> KSS by a linear scale fit to
Akerstedt 1990 data: KSS ~= 9 - 0.07 * E.

References:
    Hursh, Eddy, Storm et al. 2004 SAFTE white paper
    Mallis, Mejdal, Nguyen 2004 Aviat Space Environ Med 75 (3)
    Akerstedt & Gillberg 1990 Int J Neurosci 52:29 (KSS)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np

from .process_c import circadian_C_at_phase


R_CAPACITY_UNIT_MIN = 2880.0
WAKE_DEPLETION_PER_H = 0.5 * 60.0     # 30 unit-min depleted per hour wake
SLEEP_REPLENISH_PER_H = 4.4 * 60.0    # 264 unit-min per hour sleep at full intensity
INERTIA_DECAY_TAU_MIN = 30.0
INERTIA_MAGNITUDE = -12.0             # negative offset just after wake


@dataclass
class KSSEstimate:
    times_h:           np.ndarray
    effectiveness:     np.ndarray
    kss:               np.ndarray


def safte_alertness_curve(wake_time_h:            float,
                              bedtime_h:              float,
                              morning_wake_h:         float,
                              R0_at_today_wake:       float,
                              chronotype_msfsc_h:     float = 4.0,
                              tomorrow_end_h:         float = None,
                              dt_h:                   float = 0.1,
                              sleep_intensity:        float = 1.0,
                              ) -> KSSEstimate:
    """Forward-simulate SAFTE effectiveness from today's wake to
    end of tomorrow.

    sleep_intensity in (0, 1] modulates the replenishment rate
    (e.g.\\ severe SWS suppression -> 0.7 effective intensity).
    """
    if tomorrow_end_h is None:
        tomorrow_end_h = morning_wake_h + 17.0    # default through tomorrow evening
    n = max(2, int(round((tomorrow_end_h - wake_time_h) / dt_h)))
    times = wake_time_h + np.arange(n) * dt_h
    R = np.zeros(n)
    R[0] = R0_at_today_wake
    E = np.zeros(n)
    for k in range(n):
        t = times[k]
        if k > 0:
            prev_state_sleep = bedtime_h <= times[k - 1] < morning_wake_h
            if prev_state_sleep:
                # Sleep replenishment
                dR = SLEEP_REPLENISH_PER_H * dt_h * sleep_intensity
                R[k] = min(R_CAPACITY_UNIT_MIN, R[k - 1] + dR)
            else:
                # Wake depletion
                R[k] = max(0.0, R[k - 1] - WAKE_DEPLETION_PER_H * dt_h)
        # Circadian component scaled to +/- 8
        clock = t % 24.0
        C = 80.0 * circadian_C_at_phase(clock, chronotype_msfsc_h)
        # Inertia: only just after waking (today or tomorrow)
        if 0 <= t - wake_time_h < 2:
            inertia = INERTIA_MAGNITUDE * math.exp(-(t - wake_time_h) * 60 / INERTIA_DECAY_TAU_MIN)
        elif morning_wake_h <= t < morning_wake_h + 2:
            inertia = INERTIA_MAGNITUDE * math.exp(-(t - morning_wake_h) * 60 / INERTIA_DECAY_TAU_MIN)
        else:
            inertia = 0.0
        E[k] = 100.0 * R[k] / R_CAPACITY_UNIT_MIN + C + inertia
    # KSS mapping (1=alert, 9=sleepy)
    kss = np.clip(9 - 0.07 * E, 1.0, 9.0)
    return KSSEstimate(times_h=times, effectiveness=E, kss=kss)


def sleep_inertia_decay_min(t_min_after_wake: float) -> float:
    """Sleep inertia magnitude (negative effectiveness shift) at
    t_min_after_wake."""
    return INERTIA_MAGNITUDE * math.exp(-t_min_after_wake / INERTIA_DECAY_TAU_MIN)
