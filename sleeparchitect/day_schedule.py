"""User's day-in-progress: caffeine, alcohol, exercise, light, meal."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence, Tuple


@dataclass
class CaffeineDose:
    time_h:    float
    dose_mg:   float


@dataclass
class AlcoholDrink:
    time_h:    float
    n_drinks:  float          # standard drinks (14 g ethanol each)


@dataclass
class ExerciseBout:
    time_h:        float
    intensity:     str = "moderate"     # "light" | "moderate" | "vigorous"
    duration_min:  float = 30.0


@dataclass
class DaySchedule:
    """All inputs needed to predict tonight's sleep."""
    wake_time_h:             float = 7.0
    target_bedtime_h:        float = 23.0
    caffeine:                List[Tuple[float, float]] = field(default_factory=list)   # (time, mg)
    alcohol_drinks:          List[Tuple[float, float]] = field(default_factory=list)   # (time, n_drinks)
    exercise:                List[Tuple[float, str, float]] = field(default_factory=list)  # (time, intensity, duration_min)
    light_lux_evening:       float = 200.0       # average lux 2 h pre-bed
    last_meal_h:             float = 19.0
    meal_size:               str = "medium"       # "light" | "medium" | "heavy"
    prev_night_sleep_h:      float = 7.5         # to set S_init
    screen_time_late:        bool = True          # bright screen within 1 h of bed
