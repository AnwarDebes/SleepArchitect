"""Caffeine effect on sleep.

Re-uses the one-compartment open caffeine PK model.  Caffeine
residual body burden at bedtime translates to:

* Sleep onset latency increase (Drake et al. 2013 JCSM)
* Slow-wave sleep suppression (Clark & Landolt 2017 Sleep Med Rev)
* No significant REM% change
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence, Tuple


PK_K_A_PER_H        = 5.0
PK_V_L_PER_KG       = 0.50
PK_BIOAVAIL         = 1.0


def _half_life_h(person) -> float:
    """Personal caffeine half-life from covariates."""
    baseline = 5.0
    factor = 1.0
    if person.smoker:                    factor *= 0.50
    if person.pregnant:                  factor *= 1.59   # T2 default
    if person.hormonal_contraception:    factor *= 1.65
    if person.age >= 65:                 factor *= 1.30
    if person.cyp1a2 == "fast":          factor *= 0.85
    elif person.cyp1a2 == "slow":        factor *= 1.30
    return max(1.0, min(100.0, baseline * factor))


def _k_e(person) -> float:
    return math.log(2) / _half_life_h(person)


def _single_dose_C_mg_per_L(t_h: float, dose_mg: float,
                                k_e: float, V_L: float,
                                k_a: float = PK_K_A_PER_H) -> float:
    """Plasma concentration (mg/L) at t_h after a dose at t=0."""
    if t_h <= 0:
        return 0.0
    if abs(k_a - k_e) < 1e-9:
        return PK_BIOAVAIL * dose_mg / V_L * k_a * t_h * math.exp(-k_a * t_h)
    pre = (PK_BIOAVAIL * dose_mg * k_a) / (V_L * (k_a - k_e))
    return pre * (math.exp(-k_e * t_h) - math.exp(-k_a * t_h))


def caffeine_burden_at_bedtime_mg(person,
                                       doses: Sequence[Tuple[float, float]],
                                       bedtime_h: float) -> float:
    """Total body caffeine (mg) at bedtime, summing all doses."""
    if not doses:
        return 0.0
    k_e = _k_e(person)
    V_L = PK_V_L_PER_KG * person.weight_kg
    total_C_mg_per_L = 0.0
    for (t_dose, mg) in doses:
        dt = bedtime_h - t_dose
        if dt > 0:
            total_C_mg_per_L += _single_dose_C_mg_per_L(dt, mg, k_e, V_L)
    return total_C_mg_per_L * V_L


def caffeine_sol_delay_min(burden_mg: float) -> float:
    """SOL increase (minutes) given residual body caffeine.

    Calibrated to Drake et al. 2013: 400 mg at bedtime delays SOL by
    ~ 35 min vs placebo.  We use SOL_delay = max(0, 0.10 * (burden - 50)).
    """
    return max(0.0, 0.10 * (burden_mg - 50.0))


def caffeine_sws_suppression_pct(burden_mg: float) -> float:
    """SWS reduction (% of baseline SWS) given residual caffeine.

    Clark & Landolt 2017: 400 mg at bedtime reduces SWS by ~ 25%.
    Linear in body burden above 50 mg, capped at 40% suppression.
    """
    return max(0.0, min(40.0, 0.07 * (burden_mg - 50.0)))
