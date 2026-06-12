"""Intervention ranking.

Given a planned schedule that produces a sub-optimal sleep forecast,
rank candidate interventions by predicted improvement in sleep score:

* skip_last_caffeine
* halve_last_caffeine
* skip_alcohol
* exercise_earlier (move evening exercise 3 h earlier)
* eat_earlier (move last meal 1 h earlier)
* dim_evening_light (200 -> 30 lux)
* no_screens (turn off bright screens)
* go_to_bed_30min_later (avoid pre-circadian sleep onset)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import List

from .person import Person
from .day_schedule import DaySchedule
from .forecast import forecast_sleep, SleepForecast


@dataclass
class Intervention:
    key:         str
    label:       str
    description: str


INTERVENTIONS = {
    "skip_last_caffeine": Intervention(
        "skip_last_caffeine", "Skip your last caffeinated drink today",
        "Removes the residual body caffeine that suppresses SWS + delays SOL."),
    "halve_last_caffeine": Intervention(
        "halve_last_caffeine", "Halve your last caffeinated drink",
        "Halves the bedtime burden contribution."),
    "skip_alcohol": Intervention(
        "skip_alcohol", "Skip the alcoholic drinks tonight",
        "Removes first-half-night REM suppression and second-half fragmentation."),
    "exercise_earlier": Intervention(
        "exercise_earlier", "Move evening exercise 3 hours earlier",
        "Vigorous exercise within 1 h of bed adds 6-10 min to SOL (Stutz 2019)."),
    "eat_earlier": Intervention(
        "eat_earlier", "Eat your last meal 1 hour earlier",
        "Meals within 2 h of bed delay SOL by 10-30 min (Crispim 2011)."),
    "dim_evening_light": Intervention(
        "dim_evening_light", "Dim ambient light below 30 lux 2 h pre-bed",
        "Reduces melatonin suppression; promotes sleep onset (Khalsa 2003)."),
    "no_screens": Intervention(
        "no_screens", "No bright screens within 1 hour of bed",
        "Smartphone/tablet displays produce ~ 50-100 lux at face."),
    "delay_bedtime_30min": Intervention(
        "delay_bedtime_30min", "Delay bedtime by 30 minutes",
        "Lets homeostatic sleep pressure build above the threshold; "
        "reduces SOL for early-bedtime owls."),
    "advance_bedtime_30min": Intervention(
        "advance_bedtime_30min", "Go to bed 30 minutes earlier",
        "If your TST is too short, an earlier bedtime extends sleep."),
}


def _apply(schedule: DaySchedule, key: str) -> DaySchedule:
    s = copy.deepcopy(schedule)
    if key == "skip_last_caffeine":
        if s.caffeine: s.caffeine = s.caffeine[:-1]
    elif key == "halve_last_caffeine":
        if s.caffeine:
            t, mg = s.caffeine[-1]
            s.caffeine[-1] = (t, mg / 2.0)
    elif key == "skip_alcohol":
        s.alcohol_drinks = []
    elif key == "exercise_earlier":
        s.exercise = [(t - 3.0, intensity, dur)
                          for (t, intensity, dur) in s.exercise]
    elif key == "eat_earlier":
        s.last_meal_h = max(0.0, s.last_meal_h - 1.0)
    elif key == "dim_evening_light":
        s.light_lux_evening = 30.0
    elif key == "no_screens":
        s.screen_time_late = False
    elif key == "delay_bedtime_30min":
        s.target_bedtime_h += 0.5
    elif key == "advance_bedtime_30min":
        s.target_bedtime_h -= 0.5
    return s


def evaluate_interventions(person: Person, schedule: DaySchedule
                              ) -> List[dict]:
    base = forecast_sleep(person, schedule)
    rows = []
    for key, intv in INTERVENTIONS.items():
        s_new = _apply(schedule, key)
        if s_new is schedule:
            continue
        fc = forecast_sleep(person, s_new)
        delta = fc.sleep_score - base.sleep_score
        rows.append({
            "intervention": key, "label": intv.label, "desc": intv.description,
            "score_baseline": base.sleep_score,
            "score_after":    fc.sleep_score,
            "score_delta":    delta,
            "sol_delta_min":  fc.sol_min - base.sol_min,
            "tst_delta_h":    fc.tst_h - base.tst_h,
            "sws_delta_pp":   fc.sws_pct - base.sws_pct,
            "rem_delta_pp":   fc.rem_pct - base.rem_pct,
        })
    return rows


def rank_interventions(person: Person, schedule: DaySchedule,
                          max_n: int = 5) -> List[dict]:
    rows = evaluate_interventions(person, schedule)
    rows.sort(key=lambda r: -r["score_delta"])
    return [r for r in rows if r["score_delta"] > 0.5][:max_n]
