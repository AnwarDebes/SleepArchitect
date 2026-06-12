"""Meal-timing effect on sleep.

Crispim et al. 2011; Iao et al. 2021 (ATUS): eating within 2 hours
of bedtime increases SOL by 10-30 min and reduces REM by a few
percentage points.

Heavy / high-fat meals are worse than small / vegetable meals.
We expose a "meal size" parameter (light / medium / heavy) that
scales the effect.
"""

from __future__ import annotations


def meal_sol_delay_min(last_meal_h:    float,
                          bedtime_h:      float,
                          meal_size:      str = "medium") -> float:
    """SOL delay from last meal close to bedtime."""
    gap_h = bedtime_h - last_meal_h
    if gap_h >= 3.0:
        return 0.0
    if gap_h < 0:
        return 0.0     # meal is after bedtime (shouldn't happen)
    size_factor = {"light": 0.4, "medium": 1.0, "heavy": 1.8
                      }.get(meal_size, 1.0)
    return float(size_factor * 20.0 * (1.0 - gap_h / 3.0))


def meal_rem_reduction_pp(last_meal_h:    float,
                              bedtime_h:      float,
                              meal_size:      str = "medium") -> float:
    """REM reduction (percentage points) from late meal."""
    gap_h = bedtime_h - last_meal_h
    if gap_h >= 3.0:
        return 0.0
    if gap_h < 0:
        return 0.0
    size_factor = {"light": 0.5, "medium": 1.0, "heavy": 1.6
                      }.get(meal_size, 1.0)
    return float(min(5.0, size_factor * 3.0 * (1.0 - gap_h / 3.0)))
