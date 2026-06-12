"""Intervention experiment.

For three archetypal user-day patterns, rank interventions:

  * Knowledge worker bad day: late espresso, exercise, screens
  * Weekend bender: heavy alcohol + late meal
  * Shift worker: irregular schedule + bright light at wrong phase
"""

from __future__ import annotations

import json
from pathlib import Path

from sleeparchitect import (
    Person, DaySchedule, forecast_sleep, evaluate_interventions,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


ARCHETYPES = {
    "knowledge_worker_bad_day": {
        "person": Person(chronotype_msfsc_h=4.0, age=35),
        "schedule": DaySchedule(
            wake_time_h=7.0, target_bedtime_h=23.0,
            caffeine=[(7.0, 95), (10.0, 95), (15.0, 200)],
            alcohol_drinks=[(19.0, 1)],
            exercise=[(20.5, "vigorous", 45)],
            light_lux_evening=600, last_meal_h=21.0,
            meal_size="medium", prev_night_sleep_h=6.5,
            screen_time_late=True),
    },
    "weekend_bender": {
        "person": Person(chronotype_msfsc_h=5.0, age=28),
        "schedule": DaySchedule(
            wake_time_h=9.0, target_bedtime_h=25.0,
            caffeine=[(10.0, 95)], alcohol_drinks=[(20.0, 4)],
            exercise=[],
            light_lux_evening=500, last_meal_h=23.0,
            meal_size="heavy", prev_night_sleep_h=7.0,
            screen_time_late=True),
    },
    "owl_forced_to_sleep_early": {
        "person": Person(chronotype_msfsc_h=6.0),
        "schedule": DaySchedule(
            wake_time_h=5.0, target_bedtime_h=22.0,
            caffeine=[(5.0, 95), (12.0, 95)],
            alcohol_drinks=[],
            exercise=[(17.0, "moderate", 30)],
            light_lux_evening=400, last_meal_h=19.0,
            prev_night_sleep_h=6.5, screen_time_late=True),
    },
}


def main(out_path: Path = RESULTS / "interventions.json"):
    print()
    results = []
    for name, spec in ARCHETYPES.items():
        person = spec["person"]; sched = spec["schedule"]
        base = forecast_sleep(person, sched)
        print(f"\n=== {name} ===")
        print(f"  Baseline: SOL={base.sol_min:.0f} min, TST={base.tst_h:.2f} h, "
              f"score={base.sleep_score:.0f}")
        rows = evaluate_interventions(person, sched)
        rows.sort(key=lambda r: -r["score_delta"])
        for r in rows[:5]:
            print(f"    {r['intervention']:25s}: "
                  f"+{r['score_delta']:5.1f} score; SOL {r['sol_delta_min']:+5.1f} min; "
                  f"SWS {r['sws_delta_pp']:+4.1f} pp; REM {r['rem_delta_pp']:+4.1f} pp")
        results.append({"archetype": name,
                          "baseline_score": float(base.sleep_score),
                          "baseline_sol_min": float(base.sol_min),
                          "interventions": rows})
    out_path.write_text(json.dumps({"per_archetype": results}, indent=2,
                                      default=float))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
