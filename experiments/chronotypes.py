"""Chronotype sweep: same external environment, different chronotypes.

Demonstrates that an extreme owl trying to sleep at the lark's
preferred time has trouble even with otherwise-perfect inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

from sleeparchitect import (
    Person, DaySchedule, forecast_sleep, classify_chronotype,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


def main(out_path: Path = RESULTS / "chronotypes.json"):
    print("Same person tries different bedtimes; chronotype determines what works")
    rows = []
    for msfsc in [2.5, 3.5, 4.0, 4.5, 5.5, 6.5]:
        person = Person(chronotype_msfsc_h=msfsc)
        chrono = classify_chronotype(msfsc).value
        # Each chronotype has a natural wake / bedtime; we test
        # "lark's bedtime" 21:00 and "owl's bedtime" 25:00
        for bedtime_h in [21.0, 23.0, 25.0]:
            # Set wake 8 h before
            wake = max(4.0, bedtime_h - 8.0) if bedtime_h <= 24 else 7.0
            today = DaySchedule(
                wake_time_h=wake,
                target_bedtime_h=bedtime_h,
                caffeine=[(wake, 95)], alcohol_drinks=[],
                exercise=[(wake + 11, "moderate", 30)],
                light_lux_evening=80, last_meal_h=bedtime_h - 3.0,
                prev_night_sleep_h=7.5, screen_time_late=False,
            )
            fc = forecast_sleep(person, today)
            rows.append({
                "msfsc": msfsc, "chronotype": chrono,
                "bedtime": bedtime_h, "wake": wake,
                "S_at_bedtime": fc.S_at_bedtime,
                "H_upper": fc.H_upper_at_bedtime,
                "C_at_bedtime": fc.C_at_bedtime,
                "sol_min": fc.sol_min, "tst_h": fc.tst_h,
                "score": fc.sleep_score,
            })
            print(f"  {chrono:14s} (MSFsc {msfsc}) -> bedtime {bedtime_h:.0f}:00, "
                  f"wake {wake:.0f}:00: SOL={fc.sol_min:.0f}min  TST={fc.tst_h:.1f}h  score={fc.sleep_score:.0f}")
        print()

    out_path.write_text(json.dumps({"per_case": rows}, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
