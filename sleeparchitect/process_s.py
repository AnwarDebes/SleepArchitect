"""Process S: homeostatic sleep pressure (Borbely 1982 / Daan 1984).

Process S rises asymptotically during wake toward ~ 1 with time
constant tau_W = 18.2 h, and falls toward ~ 0 during sleep with
time constant tau_S = 4.2 h.  When S exceeds the upper threshold
(which depends on Process C) the subject is biased toward sleep;
when S falls below the lower threshold, wake.

The fundamental ODEs:

    dS/dt = -(S - S_W_asymp) / tau_W   during wake
    dS/dt = -(S - S_S_asymp) / tau_S   during sleep

with S_W_asymp = 1 (sleep pressure climbs toward 1 during wake) and
S_S_asymp = 0 (pressure dissipates toward 0 during sleep).

The analytical solutions on a piecewise-constant state interval are
the standard exponentials.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np


S_TAU_WAKE  = 18.2    # hours -- Skeldon 2017 / Daan 1984
S_TAU_SLEEP = 4.2     # hours
S_INIT      = 0.40    # initial S at midnight post-typical-sleep


def process_s_during_wake(S0: float, dt_h: float,
                             tau_W: float = S_TAU_WAKE) -> float:
    """S at t = dt_h after waking with initial value S0."""
    return 1.0 - (1.0 - S0) * math.exp(-dt_h / tau_W)


def process_s_during_sleep(S0: float, dt_h: float,
                              tau_S: float = S_TAU_SLEEP) -> float:
    """S at t = dt_h after sleep onset with initial value S0."""
    return S0 * math.exp(-dt_h / tau_S)


@dataclass
class ProcessSTrajectory:
    times_h:   np.ndarray
    S:         np.ndarray
    wake_or_sleep: np.ndarray   # 1 = wake, 0 = sleep


def process_s_trajectory(wake_time_h:        float,
                            bedtime_h:          float,
                            morning_wake_h:     float,
                            S_init_at_wake:     float = S_INIT,
                            tau_W:              float = S_TAU_WAKE,
                            tau_S:              float = S_TAU_SLEEP,
                            dt_h:               float = 0.1) -> ProcessSTrajectory:
    """Trajectory of Process S from waking through tonight's sleep.

    wake_time_h:    today's wake (e.g. 7.0 = 7 a.m.)
    bedtime_h:      tonight's predicted bedtime (e.g. 23.0 = 11 p.m.,
                       or 25.0 = 1 a.m. next day)
    morning_wake_h: tomorrow's wake (e.g. 31.0 = 7 a.m. next day)
    S_init_at_wake: S at this morning's wake (typically 0.3-0.5)
    """
    n = max(2, int(round((morning_wake_h - wake_time_h) / dt_h)))
    times = wake_time_h + np.arange(n) * dt_h
    S = np.zeros(n)
    state = np.ones(n, dtype=int)
    S[0] = S_init_at_wake
    for k in range(1, n):
        t = times[k]
        prev_S = S[k - 1]
        if t < bedtime_h:
            S[k] = process_s_during_wake(prev_S, dt_h, tau_W)
            state[k] = 1
        else:
            S[k] = process_s_during_sleep(prev_S, dt_h, tau_S)
            state[k] = 0
    return ProcessSTrajectory(times_h=times, S=S, wake_or_sleep=state)
