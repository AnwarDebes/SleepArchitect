"""Validation experiment: compare SleepArchitect outputs to published
data from Drake 2013 (caffeine), Ebrahim 2013 (alcohol),
Stutz 2019 (exercise), and Khalsa 2003 (light)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from sleeparchitect import (
    Person, DaySchedule, forecast_sleep,
    caffeine_sol_delay_min, caffeine_sws_suppression_pct,
    alcohol_rem_suppression_first_half_pct,
    light_phase_shift_h, melatonin_suppression_pct,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)


PUBLISHED_CHECKS = [
    # (name, predicted_fn, lo, hi, source)
    ("Caffeine 400 mg at bed -> SOL delay (min)",
     lambda: caffeine_sol_delay_min(400),
     25, 50, "Drake 2013 JCSM 9:1195"),
    ("Caffeine 400 mg at bed -> SWS suppression (%)",
     lambda: caffeine_sws_suppression_pct(400),
     15, 35, "Clark & Landolt 2017 Sleep Med Rev"),
    ("Caffeine 100 mg residual -> SOL delay (min)",
     lambda: caffeine_sol_delay_min(100),
     2, 12, "Drake 2013 (low dose extrapolation)"),
    ("Alcohol BAC 0.05% -> first-half REM suppression (%)",
     lambda: alcohol_rem_suppression_first_half_pct(0.05),
     10, 22, "Ebrahim 2013 Alcohol Clin Exp Res"),
    ("Alcohol BAC 0.10% -> first-half REM suppression (%)",
     lambda: alcohol_rem_suppression_first_half_pct(0.10),
     20, 35, "Ebrahim 2013"),
    ("Light 100 lux 6.5 h centred at 22:00 -> phase shift (h)",
     lambda: abs(light_phase_shift_h(100, 6.5, 22.0)),
     0.3, 1.5, "Zeitzer 2000, Khalsa 2003"),
    ("Light 1000 lux 6.5 h -> phase shift (h)",
     lambda: abs(light_phase_shift_h(1000, 6.5, 22.0)),
     1.0, 2.5, "Zeitzer 2000"),
    ("Light 100 lux -> melatonin suppression (%)",
     lambda: melatonin_suppression_pct(100),
     40, 75, "Brainard 2001, Lockley 2003"),
    ("Light 500 lux -> melatonin suppression (%)",
     lambda: melatonin_suppression_pct(500),
     90, 100, "Brainard 2001"),
]


def main(out_path: Path = RESULTS / "validation.json"):
    rows = []
    n_pass = 0
    overall = time.time()
    for label, fn, lo, hi, src in PUBLISHED_CHECKS:
        pred = float(fn())
        within = lo <= pred <= hi
        n_pass += int(within)
        rows.append({"check": label, "predicted": pred, "lo": lo, "hi": hi,
                     "source": src, "within": within})
        flag = "OK" if within else "DRIFT"
        print(f"  {label[:55]:55s}: {pred:6.2f} [{lo}-{hi}] {flag}")

    # Two-process forecast sanity tests
    print()
    print("Two-process forecast sanity:")
    me = Person()
    # 8h sleep on a clean day
    clean = DaySchedule(wake_time_h=7.0, target_bedtime_h=23.0,
                          caffeine=[(7.0, 95)], exercise=[(18.0, "moderate", 30)],
                          light_lux_evening=80, last_meal_h=19.0,
                          prev_night_sleep_h=8.0, screen_time_late=False)
    fc_clean = forecast_sleep(me, clean)
    print(f"  Clean day: SOL={fc_clean.sol_min:.1f} min, TST={fc_clean.tst_h:.2f} h, score={fc_clean.sleep_score:.0f}")
    rows.append({"check": "clean day score >= 80",
                  "predicted": fc_clean.sleep_score, "lo": 80, "hi": 100,
                  "source": "internal", "within": fc_clean.sleep_score >= 80})
    n_pass += int(fc_clean.sleep_score >= 80)

    # Bad day
    bad = DaySchedule(wake_time_h=7.0, target_bedtime_h=23.0,
                        caffeine=[(7.0, 95), (15.0, 200)],
                        alcohol_drinks=[(20.0, 3)],
                        exercise=[(22.0, "vigorous", 45)],
                        light_lux_evening=800, last_meal_h=22.5,
                        meal_size="heavy", prev_night_sleep_h=5.5,
                        screen_time_late=True)
    fc_bad = forecast_sleep(me, bad)
    print(f"  Bad day:   SOL={fc_bad.sol_min:.1f} min, TST={fc_bad.tst_h:.2f} h, score={fc_bad.sleep_score:.0f}")
    rows.append({"check": "bad day score < 75",
                  "predicted": fc_bad.sleep_score, "lo": 0, "hi": 75,
                  "source": "internal", "within": fc_bad.sleep_score < 75})
    n_pass += int(fc_bad.sleep_score < 75)

    print(f"\nValidation: {n_pass}/{len(rows)} cases within published band")
    print(f"Total: {time.time() - overall:.2f}s")
    out_path.write_text(json.dumps({"per_case": rows,
                                     "n_passed": n_pass,
                                     "n_total": len(rows)}, indent=2))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
