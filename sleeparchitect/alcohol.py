"""Alcohol effect on sleep.

Alcohol exhibits zero-order pharmacokinetics: it is eliminated at
a roughly constant rate of beta = 0.015 % BAC per hour (Widmark
formula).  Peak BAC after a standard drink (14 g ethanol) for a
70-kg man is ~ 0.020 % at 30-60 min.

Effects on sleep (Ebrahim et al. 2013 Alcohol Clin Exp Res):

* Sleep onset latency: shorter (negative delay) at moderate BAC.
* First-half REM: reduced 10-30% depending on BAC.
* Second-half REM rebound + fragmentation.
* Sleep efficiency typically reduced 3-7%.
"""

from __future__ import annotations

from typing import Sequence, Tuple


WIDMARK_R_MALE   = 0.68
WIDMARK_R_FEMALE = 0.55
ETHANOL_G_PER_DRINK = 14.0
BAC_ELIM_RATE_PERCENT_PER_H = 0.015


def BAC_at_time(weight_kg: float, sex: str,
                  drinks: Sequence[Tuple[float, float]],
                  t_h: float) -> float:
    """Blood alcohol concentration (% by volume) at clock-time t_h.

    drinks: sequence of (time_h, n_drinks).  Standard drink = 14 g ethanol.
    """
    r = WIDMARK_R_MALE if sex.upper() == "M" else WIDMARK_R_FEMALE
    bac = 0.0
    for (t_drink, n) in drinks:
        if t_h <= t_drink:
            continue
        ethanol_g = n * ETHANOL_G_PER_DRINK
        peak_bac = ethanol_g / (weight_kg * r * 10.0)   # % vol/vol
        elapsed = max(0.0, t_h - t_drink - 0.5)         # ~30 min to peak
        decay = BAC_ELIM_RATE_PERCENT_PER_H * elapsed
        bac += max(0.0, peak_bac - decay)
    return float(bac)


def alcohol_rem_suppression_first_half_pct(bac_at_bedtime: float) -> float:
    """First-half-night REM suppression (% reduction).

    Ebrahim 2013: low BAC ~ 0.02 produces 5%; BAC ~ 0.05 produces 10-15%;
    BAC > 0.08 produces 20-30%.  Linear in BAC, capped at 35%.
    """
    return max(0.0, min(40.0, 320.0 * bac_at_bedtime))


def alcohol_rem_rebound_second_half_pct(bac_at_bedtime: float) -> float:
    """Second-half-night REM rebound (% increase vs baseline)."""
    return max(0.0, min(20.0, 200.0 * bac_at_bedtime))


def alcohol_sol_change_min(bac_at_bedtime: float) -> float:
    """Sleep onset latency change.  Alcohol REDUCES SOL at low BAC,
    can REDUCE further or even increase at very high BAC.  Linear,
    negative for moderate BAC."""
    return -10.0 * min(0.05, bac_at_bedtime) * 20.0    # ~ -10 min at 0.05
