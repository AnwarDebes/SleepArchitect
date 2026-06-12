"""Sleep architecture: REM / NREM / SWS / N1+N2.

Healthy adults cycle every ~ 90-110 min between NREM (with SWS
predominating in the first half) and REM (with REM predominating in
the second half).  Typical proportions:

    N1: 5-10%
    N2: 45-55%
    N3 / SWS: 13-23%  (front-loaded -- decreases each cycle)
    REM: 20-25%  (back-loaded -- increases each cycle)

We synthesise a hypnogram with 4-6 cycles and per-cycle distribution
that shifts from SWS-dominant to REM-dominant.  Caffeine, alcohol,
exercise, and meal modulators shift these proportions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np


CYCLE_LENGTH_MIN = 95.0     # typical adult NREM-REM cycle


@dataclass
class Hypnogram:
    times_min:     np.ndarray   # minutes since sleep onset
    stage:         np.ndarray   # 0=Wake, 1=N1, 2=N2, 3=N3/SWS, 4=REM
    sws_min:       float
    rem_min:       float
    n1_n2_min:     float
    wake_after_sleep_onset_min: float


def _stage_distribution_for_cycle(cycle_index: int,
                                       n_cycles: int) -> np.ndarray:
    """Return fractional distribution [N1, N2, SWS, REM] for one cycle."""
    # Cycle index 0 has most SWS; cycle n_cycles-1 has most REM.
    progress = cycle_index / max(1.0, n_cycles - 1)
    # SWS front-loaded: 0.45 in cycle 0 -> 0.05 in last cycle
    sws_frac = max(0.05, 0.45 - 0.40 * progress)
    # REM back-loaded: 0.08 in cycle 0 -> 0.40 in last cycle
    rem_frac = min(0.45, 0.08 + 0.32 * progress)
    # N1 + N2 split: residual
    residual = max(0.05, 1.0 - sws_frac - rem_frac)
    n1_frac = 0.10
    n2_frac = max(0.05, residual - n1_frac)
    return np.array([n1_frac, n2_frac, sws_frac, rem_frac])


def simulate_hypnogram(tst_min:                  float,
                          sws_modifier_pp:         float = 0.0,
                          rem_modifier_pp_first:   float = 0.0,
                          rem_modifier_pp_second:  float = 0.0,
                          waso_min:                float = 12.0,
                          ) -> Hypnogram:
    """Synthesise a hypnogram with the given total sleep time and
    macro-architecture modifiers (in percentage points).

    sws_modifier_pp:  add this many pp to the SWS share (negative for
                        caffeine suppression).
    rem_modifier_pp_first: applied to first-half-night REM (alcohol).
    rem_modifier_pp_second: applied to second-half-night REM (alcohol
                                rebound).
    """
    n_cycles = max(2, int(round(tst_min / CYCLE_LENGTH_MIN)))
    actual_cycle_min = tst_min / n_cycles

    times = np.linspace(0, tst_min, num=int(tst_min) + 1)
    stage = np.full_like(times, 0.0, dtype=np.int32)

    cum_sws = 0.0; cum_rem = 0.0; cum_n12 = 0.0
    for c in range(n_cycles):
        frac = _stage_distribution_for_cycle(c, n_cycles)
        # Apply modifiers
        frac_sws = max(0.0, frac[2] + sws_modifier_pp / 100.0)
        first_half = c < n_cycles / 2
        rem_mod = (rem_modifier_pp_first if first_half
                     else rem_modifier_pp_second) / 100.0
        frac_rem = max(0.0, frac[3] + rem_mod)
        # Re-normalise so frac sums to 1
        total = frac_sws + frac_rem + frac[0] + frac[1]
        if total <= 0:
            continue
        frac_sws /= total; frac_rem /= total
        frac_n1 = frac[0] / total; frac_n2 = frac[1] / total

        cycle_start = c * actual_cycle_min
        cycle_end   = (c + 1) * actual_cycle_min
        # Within each cycle: simple ordering N1 -> N2 -> SWS -> N2 -> REM
        # (closely approximates real PSG)
        durs = [frac_n1, frac_n2 * 0.4, frac_sws,
                  frac_n2 * 0.6, frac_rem]
        codes = [1, 2, 3, 2, 4]
        t_start = cycle_start
        for d, code in zip(durs, codes):
            t_end = t_start + d * actual_cycle_min
            mask = (times >= t_start) & (times < t_end)
            stage[mask] = code
            t_start = t_end
        cum_sws  += frac_sws * actual_cycle_min
        cum_rem  += frac_rem * actual_cycle_min
        cum_n12  += (frac_n1 + frac_n2) * actual_cycle_min

    # Insert WASO (brief wakeups in the second half of the night)
    if waso_min > 0:
        n_inserts = max(1, int(waso_min / 3.0))
        for _ in range(n_inserts):
            idx = int(np.random.uniform(0.55 * len(times), 0.95 * len(times)))
            # Set a 2-3 min wake epoch
            end_idx = min(len(times) - 1, idx + 3)
            stage[idx:end_idx] = 0

    return Hypnogram(
        times_min=times, stage=stage,
        sws_min=float(cum_sws), rem_min=float(cum_rem),
        n1_n2_min=float(cum_n12),
        wake_after_sleep_onset_min=float(waso_min),
    )


def sleep_proportions(hypnogram: Hypnogram) -> dict:
    total = hypnogram.sws_min + hypnogram.rem_min + hypnogram.n1_n2_min
    if total <= 0:
        return {"sws_pct": 0.0, "rem_pct": 0.0, "n1_n2_pct": 0.0}
    return {
        "sws_pct":   100 * hypnogram.sws_min / total,
        "rem_pct":   100 * hypnogram.rem_min / total,
        "n1_n2_pct": 100 * hypnogram.n1_n2_min / total,
    }
