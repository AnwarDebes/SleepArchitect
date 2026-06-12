"""Integrate Process S, Process C, and all modulators into a
sleep forecast for tonight.

The forecast produces:

* predicted sleep onset latency (minutes)
* total sleep time (hours)
* sleep efficiency (%)
* SWS / REM / N1+N2 proportions
* a 5-cycle hypnogram
* a SAFTE alertness curve through tomorrow

Method:

1. Process S from this morning's wake -> target bedtime.
2. Process C threshold at target bedtime determines whether the
   biological signal is "ready for sleep".
3. The deviation of S - H_upper at bedtime modulates SOL: if S is
   already above the threshold (high pressure), SOL is short; if S
   is below, SOL is long.
4. Caffeine residual at bedtime adds delay (Drake 2013).
5. Late meal + evening exercise + bright screens add delay.
6. Alcohol *reduces* SOL but shifts the architecture.
7. Light exposure shifts the circadian phase for tomorrow.
8. Final SOL, TST, architecture -> hypnogram simulation.
9. Sleep intensity (reduced by caffeine SWS suppression / alcohol
   fragmentation) -> SAFTE reservoir replenishment rate -> tomorrow
   alertness.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .person import Person
from .day_schedule import DaySchedule
from .process_s import process_s_during_wake, S_TAU_WAKE, S_TAU_SLEEP, S_INIT
from .process_c import (
    circadian_C_at_phase, H_upper,
)
from .caffeine import (
    caffeine_burden_at_bedtime_mg, caffeine_sol_delay_min,
    caffeine_sws_suppression_pct,
)
from .alcohol import (
    BAC_at_time, alcohol_rem_suppression_first_half_pct,
    alcohol_rem_rebound_second_half_pct, alcohol_sol_change_min,
)
from .exercise import exercise_sol_delay_min, exercise_sws_boost_pp
from .meal import meal_sol_delay_min, meal_rem_reduction_pp
from .light import light_phase_shift_h, melatonin_suppression_pct
from .architecture import (
    simulate_hypnogram, Hypnogram, sleep_proportions,
)
from .alertness import (
    safte_alertness_curve, KSSEstimate, R_CAPACITY_UNIT_MIN,
)


@dataclass
class SleepForecast:
    # Inputs (echoed back)
    person:                Person
    schedule:              DaySchedule
    # Predicted sleep
    sleep_onset_clock_h:   float
    sol_min:               float
    tst_h:                 float
    se_pct:                float
    morning_wake_clock_h:  float
    # Architecture
    sws_pct:               float
    rem_pct:               float
    n1_n2_pct:             float
    sws_min:               float
    rem_min:               float
    waso_min:              float
    hypnogram:             Hypnogram
    # Process internals
    S_at_bedtime:          float
    H_upper_at_bedtime:    float
    C_at_bedtime:          float
    caffeine_burden_mg:    float
    bac_at_bedtime:        float
    phase_shift_tomorrow_h: float
    melatonin_suppression_pct: float
    # Alertness
    alertness_curve:       KSSEstimate
    # Score (0-100, higher = better sleep)
    sleep_score:           float
    interpretation:        str


def _S_at_target_bedtime(schedule: DaySchedule) -> float:
    """Process S at target_bedtime starting from S_INIT scaled by
    previous-night sleep."""
    S0 = max(0.05, min(0.60, S_INIT
                * (8.0 / max(schedule.prev_night_sleep_h, 4.0))))
    hours_awake = schedule.target_bedtime_h - schedule.wake_time_h
    return process_s_during_wake(S0, max(0.0, hours_awake))


def forecast_sleep(person: Person, schedule: DaySchedule) -> SleepForecast:
    """Predict tonight's sleep + tomorrow's alertness."""
    # ---- Process S + C at target bedtime ----
    S_bedtime = _S_at_target_bedtime(schedule)
    C_bedtime = circadian_C_at_phase(schedule.target_bedtime_h % 24,
                                          person.chronotype_msfsc_h)
    H_up = H_upper(schedule.target_bedtime_h % 24, person.chronotype_msfsc_h)

    # ---- SOL components ----
    # Baseline SOL from S relative to H_upper.  When S >> H_upper, SOL ~ 5 min.
    sol_base = 12.0
    if S_bedtime < H_up:
        # Trying to sleep before circadian-homeostatic readiness
        sol_base += 30.0 * (H_up - S_bedtime) / max(0.05, H_up)
    # Caffeine residual
    burden = caffeine_burden_at_bedtime_mg(person, schedule.caffeine,
                                                  schedule.target_bedtime_h)
    sol_caff = caffeine_sol_delay_min(burden)
    # Alcohol effect on SOL (negative -> reduces SOL)
    bac_b = BAC_at_time(person.weight_kg, person.sex,
                          schedule.alcohol_drinks, schedule.target_bedtime_h)
    sol_alc = alcohol_sol_change_min(bac_b)
    # Exercise
    sol_ex = exercise_sol_delay_min(schedule.exercise,
                                          schedule.target_bedtime_h)
    # Meal timing
    sol_meal = meal_sol_delay_min(schedule.last_meal_h,
                                       schedule.target_bedtime_h,
                                       schedule.meal_size)
    # Bright screens late
    sol_screen = 8.0 if schedule.screen_time_late else 0.0
    # Light suppression of melatonin adds to SOL
    mel_supp = melatonin_suppression_pct(schedule.light_lux_evening)
    sol_light = 0.30 * mel_supp / 10.0    # ~ 3 min per 100% suppression

    sol_total = max(2.0, sol_base + sol_caff + sol_alc + sol_ex
                            + sol_meal + sol_screen + sol_light)

    # ---- TST + Sleep Efficiency ----
    sleep_onset_clock = schedule.target_bedtime_h + sol_total / 60.0
    # User typically sets a morning_wake by need (work / school).  We
    # default to 7.5 h after bedtime + some adjustment.
    nominal_target_TST = 8.0
    morning_wake_clock = schedule.target_bedtime_h + nominal_target_TST
    tst_h = max(0.5, morning_wake_clock - sleep_onset_clock)
    # WASO from caffeine + alcohol + late meal
    waso_caff = burden * 0.05
    waso_alc = 35.0 * bac_b
    waso_meal = sol_meal * 0.2
    waso_min = max(8.0, 12.0 + waso_caff + waso_alc + waso_meal)
    # Sleep efficiency
    time_in_bed_min = (morning_wake_clock - schedule.target_bedtime_h) * 60
    se = max(40.0, 100.0 * (tst_h * 60 - waso_min) / max(time_in_bed_min, 1))
    se = float(min(100.0, se))

    # ---- Architecture modifiers ----
    sws_mod_caff = -caffeine_sws_suppression_pct(burden) / 100.0 * 100.0  # negative pp
    sws_mod_ex = exercise_sws_boost_pp(schedule.exercise,
                                              schedule.target_bedtime_h)
    sws_mod = sws_mod_caff + sws_mod_ex
    # Alcohol REM modifiers
    rem_first_mod  = -alcohol_rem_suppression_first_half_pct(bac_b)
    rem_second_mod = alcohol_rem_rebound_second_half_pct(bac_b)
    # Late meal REM reduction
    rem_mealmod = -meal_rem_reduction_pp(schedule.last_meal_h,
                                              schedule.target_bedtime_h,
                                              schedule.meal_size)
    rem_first_mod += rem_mealmod
    rem_second_mod += rem_mealmod * 0.3   # softer on second half

    hyp = simulate_hypnogram(tst_min=tst_h * 60.0,
                                sws_modifier_pp=sws_mod,
                                rem_modifier_pp_first=rem_first_mod,
                                rem_modifier_pp_second=rem_second_mod,
                                waso_min=waso_min - 12.0)
    props = sleep_proportions(hyp)

    # ---- Phase shift from evening light ----
    mid_light_h = schedule.target_bedtime_h - 2.0
    phase_shift = light_phase_shift_h(schedule.light_lux_evening, 2.0,
                                          mid_light_h, person.chronotype_msfsc_h)

    # ---- Alertness curve through tomorrow ----
    # Sleep intensity: reduced if SWS is suppressed
    intensity = 1.0 - max(0, -sws_mod / 100.0)
    # R0 at today's wake: scale by previous-night TST relative to 8 h
    R0_today = R_CAPACITY_UNIT_MIN * min(1.0, schedule.prev_night_sleep_h / 8.0)
    alertness = safte_alertness_curve(
        wake_time_h=schedule.wake_time_h,
        bedtime_h=sleep_onset_clock,
        morning_wake_h=morning_wake_clock,
        R0_at_today_wake=R0_today,
        chronotype_msfsc_h=person.chronotype_msfsc_h,
        tomorrow_end_h=morning_wake_clock + 17.0,
        sleep_intensity=intensity,
    )

    # ---- Sleep score (0-100) ----
    # Penalise long SOL (>30 min), short TST (<6.5 h), low SE (<85%).
    score = 100.0
    score -= max(0.0, sol_total - 15.0) * 0.6     # 1 pp per 1.7 min over 15
    score -= max(0.0, 7.5 - tst_h) * 8.0          # 8 pp per missing hour
    score -= max(0.0, 85.0 - se) * 1.0            # 1 pp per missing SE pp
    score -= max(0.0, -sws_mod) * 0.4
    score = float(max(0.0, min(100.0, score)))

    if score >= 80:    interp = "Predicted sleep should be restorative."
    elif score >= 65:  interp = "Sleep should be acceptable but suboptimal."
    elif score >= 50:  interp = "Significant sleep disruption likely."
    else:              interp = "Severe sleep disruption likely; consider interventions."

    return SleepForecast(
        person=person, schedule=schedule,
        sleep_onset_clock_h=float(sleep_onset_clock),
        sol_min=float(sol_total),
        tst_h=float(tst_h),
        se_pct=float(se),
        morning_wake_clock_h=float(morning_wake_clock),
        sws_pct=float(props["sws_pct"]),
        rem_pct=float(props["rem_pct"]),
        n1_n2_pct=float(props["n1_n2_pct"]),
        sws_min=float(hyp.sws_min),
        rem_min=float(hyp.rem_min),
        waso_min=float(waso_min),
        hypnogram=hyp,
        S_at_bedtime=float(S_bedtime),
        H_upper_at_bedtime=float(H_up),
        C_at_bedtime=float(C_bedtime),
        caffeine_burden_mg=float(burden),
        bac_at_bedtime=float(bac_b),
        phase_shift_tomorrow_h=float(phase_shift),
        melatonin_suppression_pct=float(mel_supp),
        alertness_curve=alertness,
        sleep_score=float(score),
        interpretation=interp,
    )
