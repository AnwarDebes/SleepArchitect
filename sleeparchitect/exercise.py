"""Exercise effect on sleep.

Stutz et al. 2019 meta-analysis (Sleep Med Rev) on 23 studies:

* Morning / afternoon exercise: improves SOL and sleep efficiency.
* Evening exercise (1-2 h before bed): non-significant effect.
* Vigorous exercise within 1 h of bedtime: increases SOL by ~ 6-10 min.
* Exercise of any intensity: increases SWS by +1.3 pp on average.
* REM latency increases ~ 7.7 min.
"""

from __future__ import annotations

from typing import Sequence, Tuple


def exercise_sol_delay_min(bouts: Sequence[Tuple[float, str, float]],
                              bedtime_h: float) -> float:
    """Net SOL delay (minutes) from today's exercise bouts.

    bouts: list of (clock_h_start, intensity, duration_min).
        intensity in {"light", "moderate", "vigorous"}.
    """
    total = 0.0
    for (start_h, intensity, duration_min) in bouts:
        gap_h = bedtime_h - (start_h + duration_min / 60.0)
        intensity_factor = {"light": 0.3, "moderate": 1.0, "vigorous": 1.8
                              }.get(intensity, 1.0)
        if gap_h < 0:
            # Exercise ends after bedtime -- maximum disruption
            total += 10.0 * intensity_factor
            continue
        if gap_h < 1.0:
            # Vigorous within 1 h: +6-10 min
            total += 8.0 * intensity_factor * (1.0 - gap_h)
        elif gap_h < 3.0:
            # Slight residual effect
            total += 2.0 * intensity_factor * (1.0 - (gap_h - 1.0) / 2.0)
        else:
            # Earlier exercise typically REDUCES SOL by 2-4 min
            total += -2.0 * intensity_factor * min(1.0, (gap_h - 3.0) / 6.0)
    return float(total)


def exercise_sws_boost_pp(bouts: Sequence[Tuple[float, str, float]],
                            bedtime_h: float) -> float:
    """SWS increase (percentage points) from today's exercise."""
    total = 0.0
    for (start_h, intensity, duration_min) in bouts:
        intensity_factor = {"light": 0.3, "moderate": 1.0, "vigorous": 1.5
                              }.get(intensity, 1.0)
        duration_factor = min(1.0, duration_min / 30.0)
        total += 1.3 * intensity_factor * duration_factor
    return float(min(5.0, total))
