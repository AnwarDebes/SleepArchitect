"""SleepArchitect: predict tonight's sleep, optimise tomorrow's alertness.

Existing sleep apps (Oura, Whoop, Apple Health, Sleep Cycle, AutoSleep)
are retrospective -- they tell you how you slept last night.  None
predict tonight's sleep from today's caffeine, alcohol, light, exercise,
and meals.  SleepArchitect closes that gap with the Borbely two-process
model (Process S homeostatic + Process C circadian) coupled to:

  * caffeine PK (Carrillo & Benitez 2000) -> SWS suppression + SOL delay
  * alcohol PK (Ebrahim 2013) -> first-half REM suppression + rebound
  * Khalsa 2003 light PRC -> circadian phase shift from evening light
  * Stutz 2019 exercise meta-analysis -> SWS / SOL effects
  * Crispim 2011 meal-timing effects on SOL + REM
  * chronotype (MCTQ / MEQ) sets the baseline circadian phase

The predicted output:

  * sleep onset latency (SOL) in minutes
  * total sleep time (TST) in hours
  * sleep efficiency (SE) in percent
  * REM / SWS / N1+N2 proportions
  * hypnogram (4-6 NREM-REM cycles)
  * SAFTE-style alertness curve through tomorrow

Quick start
-----------

    from sleeparchitect import (
        Person, DaySchedule, SleepForecast, forecast_sleep,
        rank_interventions,
    )

    me = Person(chronotype_msfsc_h=4.0, age=35, sex="M")
    today = DaySchedule(wake_time_h=7.0, target_bedtime_h=23.0,
        caffeine=[(7.0, 95), (14.0, 95)],
        alcohol_drinks=[(20.0, 1.5)],
        exercise=[(18.0, "moderate", 45)],
        light_lux_evening=600.0,
        last_meal_h=20.0,
        prev_night_sleep_h=7.0)
    fc = forecast_sleep(me, today)
    print(f"SOL {fc.sol_min:.0f} min, TST {fc.tst_h:.2f} h, SE {fc.se_pct:.0f}%")
"""

from .person import Person, ChronotypeCategory, classify_chronotype
from .process_s import process_s_trajectory, S_TAU_WAKE, S_TAU_SLEEP, S_INIT
from .process_c import (
    circadian_C_at_phase, monthly_phase_for_chronotype,
    SLEEP_UPPER_THRESHOLD, SLEEP_LOWER_THRESHOLD,
)
from .light import (
    light_phase_shift_h, melatonin_suppression_pct,
    KHALSA_HALF_MAX_LUX, ZEITZER_DOSE_RESPONSE,
)
from .caffeine import (
    caffeine_burden_at_bedtime_mg, caffeine_sol_delay_min,
    caffeine_sws_suppression_pct,
)
from .alcohol import (
    BAC_at_time, alcohol_rem_suppression_first_half_pct,
    alcohol_rem_rebound_second_half_pct,
)
from .exercise import (
    exercise_sol_delay_min, exercise_sws_boost_pp,
)
from .meal import (
    meal_sol_delay_min, meal_rem_reduction_pp,
)
from .architecture import (
    Hypnogram, simulate_hypnogram, sleep_proportions,
)
from .alertness import (
    safte_alertness_curve, sleep_inertia_decay_min,
    KSSEstimate,
)
from .day_schedule import DaySchedule, CaffeineDose, AlcoholDrink, ExerciseBout
from .forecast import SleepForecast, forecast_sleep
from .intervention import (
    Intervention, INTERVENTIONS, evaluate_interventions, rank_interventions,
)
