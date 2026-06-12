"""Unit tests for SleepArchitect."""

import math

import numpy as np
import pytest

from sleeparchitect import (
    Person, DaySchedule, forecast_sleep,
    process_s_trajectory, S_TAU_WAKE, S_TAU_SLEEP, S_INIT,
    circadian_C_at_phase, SLEEP_UPPER_THRESHOLD, SLEEP_LOWER_THRESHOLD,
    light_phase_shift_h, melatonin_suppression_pct, KHALSA_HALF_MAX_LUX,
    caffeine_burden_at_bedtime_mg, caffeine_sol_delay_min, caffeine_sws_suppression_pct,
    BAC_at_time, alcohol_rem_suppression_first_half_pct,
    alcohol_rem_rebound_second_half_pct,
    exercise_sol_delay_min, exercise_sws_boost_pp,
    meal_sol_delay_min, meal_rem_reduction_pp,
    simulate_hypnogram, sleep_proportions,
    safte_alertness_curve,
    classify_chronotype, ChronotypeCategory,
    rank_interventions, evaluate_interventions, INTERVENTIONS,
)
from sleeparchitect.process_s import process_s_during_wake, process_s_during_sleep


# ---------- Process S ----------

def test_process_s_rises_during_wake():
    s_init = 0.40
    s_5h = process_s_during_wake(s_init, 5.0)
    s_10h = process_s_during_wake(s_init, 10.0)
    s_20h = process_s_during_wake(s_init, 20.0)
    assert s_init < s_5h < s_10h < s_20h
    # Asymptotes toward 1.0
    s_inf = process_s_during_wake(s_init, 1000.0)
    assert abs(s_inf - 1.0) < 1e-6


def test_process_s_falls_during_sleep():
    s_init = 0.85
    s_2h = process_s_during_sleep(s_init, 2.0)
    s_4h = process_s_during_sleep(s_init, 4.0)
    assert s_init > s_2h > s_4h
    # Asymptotes toward 0
    assert process_s_during_sleep(s_init, 1000.0) < 0.001


def test_tau_constants_match_daan():
    """Daan/Beersma/Borbely 1984: tau_W = 18.2 h, tau_S = 4.2 h."""
    assert abs(S_TAU_WAKE - 18.2) < 0.1
    assert abs(S_TAU_SLEEP - 4.2) < 0.1


# ---------- Process C ----------

def test_circadian_C_period_24h():
    """C(t) should be approximately periodic with period 24 h."""
    msfsc = 4.0
    for t in [0.0, 6.0, 12.0]:
        c_t = circadian_C_at_phase(t, msfsc)
        c_t_plus_24 = circadian_C_at_phase(t + 24.0, msfsc)
        assert abs(c_t - c_t_plus_24) < 1e-9


def test_h_upper_above_h_lower():
    for clock in [0, 6, 12, 18]:
        assert SLEEP_UPPER_THRESHOLD(clock) > SLEEP_LOWER_THRESHOLD(clock)


# ---------- Light PRC ----------

def test_light_no_shift_for_zero_lux():
    assert light_phase_shift_h(0.0, 2.0, 22.0) == 0.0


def test_light_more_shift_for_higher_lux():
    s_100  = abs(light_phase_shift_h(100.0,  2.0, 22.0))
    s_1000 = abs(light_phase_shift_h(1000.0, 2.0, 22.0))
    assert s_1000 > s_100


def test_melatonin_suppression_monotone():
    for lux_lo, lux_hi in [(0, 50), (50, 100), (100, 500), (500, 1000)]:
        assert melatonin_suppression_pct(lux_lo) < melatonin_suppression_pct(lux_hi)


def test_melatonin_50pct_around_100_lux():
    """Brainard 2001 / Lockley 2003: ~50% suppression at ~100 lux."""
    s = melatonin_suppression_pct(100.0)
    assert 50 < s < 75


# ---------- Caffeine ----------

def test_caffeine_burden_grows_with_dose():
    me = Person()
    burden_low  = caffeine_burden_at_bedtime_mg(me, [(7.0, 50)], 23.0)
    burden_high = caffeine_burden_at_bedtime_mg(me, [(7.0, 200)], 23.0)
    assert burden_high > burden_low


def test_caffeine_burden_smaller_for_smokers():
    """Smokers metabolise caffeine ~2x faster (Carrillo 2000)."""
    s = Person(smoker=True)
    n = Person(smoker=False)
    burden_s = caffeine_burden_at_bedtime_mg(s, [(7.0, 200)], 23.0)
    burden_n = caffeine_burden_at_bedtime_mg(n, [(7.0, 200)], 23.0)
    assert burden_s < burden_n / 1.5


def test_drake_2013_400mg_sol_delay():
    """Drake 2013: 400 mg residual at bedtime adds ~ 35 min SOL."""
    sol_400 = caffeine_sol_delay_min(400)
    assert 25 < sol_400 < 50


# ---------- Alcohol ----------

def test_alcohol_bac_increases_with_drinks():
    bac1 = BAC_at_time(70, "M", [(20.0, 1)], 23.0)
    bac3 = BAC_at_time(70, "M", [(20.0, 3)], 23.0)
    assert bac3 > bac1


def test_alcohol_rem_suppression_increases_with_bac():
    s_0 = alcohol_rem_suppression_first_half_pct(0.0)
    s_05 = alcohol_rem_suppression_first_half_pct(0.05)
    s_10 = alcohol_rem_suppression_first_half_pct(0.10)
    assert s_0 == 0.0
    assert s_05 < s_10
    # Ebrahim 2013 ranges: ~15% at 0.05, ~25% at 0.10
    assert 10 < s_05 < 25
    assert 20 < s_10 < 35


def test_alcohol_rem_rebound():
    assert alcohol_rem_rebound_second_half_pct(0.10) > 0


# ---------- Exercise ----------

def test_exercise_late_vigorous_delays_sol():
    sol = exercise_sol_delay_min([(22.5, "vigorous", 60)], 23.0)
    assert sol > 5


def test_exercise_morning_no_delay():
    """Morning exercise should not increase SOL."""
    sol = exercise_sol_delay_min([(7.0, "moderate", 30)], 23.0)
    assert sol <= 0


def test_exercise_sws_boost_positive():
    boost = exercise_sws_boost_pp([(18.0, "moderate", 45)], 23.0)
    assert boost > 0


# ---------- Meal ----------

def test_meal_late_delays_sol():
    sol = meal_sol_delay_min(22.0, 23.0, "heavy")
    assert sol > 10


def test_meal_early_no_effect():
    sol = meal_sol_delay_min(17.0, 23.0)
    assert sol == 0


# ---------- Architecture ----------

def test_hypnogram_proportions_realistic():
    """Adult sleep should be ~20% REM, ~15-20% SWS, balance N1+N2."""
    h = simulate_hypnogram(tst_min=480, waso_min=15)
    p = sleep_proportions(h)
    assert 12 < p["sws_pct"] < 30
    assert 15 < p["rem_pct"] < 30
    assert 40 < p["n1_n2_pct"] < 70


def test_hypnogram_responds_to_caffeine_modifier():
    """SWS suppression should reduce the SWS proportion."""
    h_baseline = simulate_hypnogram(tst_min=480, sws_modifier_pp=0.0)
    h_caff = simulate_hypnogram(tst_min=480, sws_modifier_pp=-20.0)
    p1 = sleep_proportions(h_baseline)
    p2 = sleep_proportions(h_caff)
    assert p2["sws_pct"] < p1["sws_pct"]


# ---------- Alertness ----------

def test_safte_alertness_dips_at_post_lunch_or_evening():
    """SAFTE alertness should vary substantially through the day.
    KSS should be lowest (most alert) ~ 11 h after wake, and higher
    (sleepier) by 16+ h after wake (early evening dip)."""
    alertness = safte_alertness_curve(
        wake_time_h=7.0, bedtime_h=23.0, morning_wake_h=31.0,
        R0_at_today_wake=2880, chronotype_msfsc_h=4.0,
        tomorrow_end_h=48.0)
    # Day variation should be at least 1 KSS point
    daytime_mask = (alertness.times_h >= 8) & (alertness.times_h <= 22)
    kss_day = alertness.kss[daytime_mask]
    assert kss_day.max() - kss_day.min() >= 0.5


# ---------- Chronotype ----------

def test_chronotype_classification_thresholds():
    assert classify_chronotype(2.0) == ChronotypeCategory.EXTREME_LARK
    assert classify_chronotype(3.0) == ChronotypeCategory.MODERATE_LARK
    assert classify_chronotype(4.0) == ChronotypeCategory.INTERMEDIATE
    assert classify_chronotype(5.0) == ChronotypeCategory.MODERATE_OWL
    assert classify_chronotype(6.0) == ChronotypeCategory.EXTREME_OWL


# ---------- Forecast integration ----------

def test_forecast_baseline_is_high_score():
    me = Person()
    today = DaySchedule(wake_time_h=7.0, target_bedtime_h=23.0,
                          caffeine=[(7.0, 95)], alcohol_drinks=[],
                          exercise=[(18.0, "moderate", 30)],
                          light_lux_evening=80,
                          last_meal_h=19.0, prev_night_sleep_h=8.0,
                          screen_time_late=False)
    fc = forecast_sleep(me, today)
    assert fc.sleep_score > 80
    assert fc.sol_min < 25


def test_forecast_bad_day_is_low_score():
    me = Person()
    today = DaySchedule(wake_time_h=7.0, target_bedtime_h=23.0,
                          caffeine=[(7.0, 95), (10.5, 95), (18.0, 200)],
                          alcohol_drinks=[(20.0, 2.0)],
                          exercise=[(22.0, "vigorous", 60)],
                          light_lux_evening=800,
                          last_meal_h=22.5, meal_size="heavy",
                          prev_night_sleep_h=5.0,
                          screen_time_late=True)
    fc = forecast_sleep(me, today)
    assert fc.sleep_score < 80
    assert fc.sol_min > 30


def test_smoker_lower_caffeine_burden():
    today = DaySchedule(wake_time_h=7.0, target_bedtime_h=23.0,
                          caffeine=[(7.0, 95), (15.0, 95)],
                          alcohol_drinks=[], exercise=[])
    fc_smoker  = forecast_sleep(Person(smoker=True),  today)
    fc_n       = forecast_sleep(Person(smoker=False), today)
    assert fc_smoker.caffeine_burden_mg < fc_n.caffeine_burden_mg


def test_rank_interventions_improves_score():
    me = Person()
    bad = DaySchedule(wake_time_h=7.0, target_bedtime_h=23.0,
                        caffeine=[(7.0, 95), (15.0, 200)],
                        alcohol_drinks=[(20.0, 2.0)],
                        exercise=[(21.5, "vigorous", 60)],
                        light_lux_evening=800, last_meal_h=22.0,
                        meal_size="heavy", prev_night_sleep_h=6.0,
                        screen_time_late=True)
    recs = rank_interventions(me, bad, max_n=4)
    assert len(recs) >= 2
    assert all(r["score_delta"] > 0 for r in recs)


def test_intervention_count_matches_catalog():
    me = Person()
    base = DaySchedule(wake_time_h=7.0, target_bedtime_h=23.0,
                         caffeine=[(7.0, 95), (15.0, 100)],
                         alcohol_drinks=[(20.0, 1)],
                         exercise=[(20.0, "moderate", 30)],
                         light_lux_evening=300,
                         last_meal_h=20.0, prev_night_sleep_h=7.0,
                         screen_time_late=True)
    rows = evaluate_interventions(me, base)
    assert len(rows) == len(INTERVENTIONS)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
