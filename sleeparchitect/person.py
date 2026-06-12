"""Personal characteristics that anchor the circadian phase.

The single most important personal parameter is the chronotype --
where on the morning-lark / night-owl axis the user sits.  We use the
Munich Chronotype Questionnaire (MCTQ) midpoint of sleep on free days
corrected for sleep debt (MSFsc), Roenneberg 2003, which has been
shown to correlate well with measured DLMO (dim-light melatonin
onset).  Population mean MSFsc ~ 04:00 h with SD ~ 1 h.

Alternatively a Horne-Ostberg MEQ score (19-86) can be entered.

References:
    Roenneberg et al. 2003 J Biol Rhythms (MCTQ)
    Horne & Ostberg 1976 Int J Chronobiol (MEQ)
    Kerkhof 1998 J Sleep Res (DLMO-MSFsc correspondence)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class ChronotypeCategory(str, Enum):
    EXTREME_LARK   = "extreme_lark"
    MODERATE_LARK  = "moderate_lark"
    INTERMEDIATE   = "intermediate"
    MODERATE_OWL   = "moderate_owl"
    EXTREME_OWL    = "extreme_owl"


@dataclass
class Person:
    """User profile.

    chronotype_msfsc_h: MCTQ midpoint of sleep on free days
                          (sleep-debt-corrected), in hours after midnight
                          (e.g. 04.0 = 4:00 am, population mean).
    age, sex are used for caffeine PK and (mild) age-effect on SWS.
    weight_kg is for caffeine + alcohol PK.
    """
    chronotype_msfsc_h:        float = 4.0
    age:                       int   = 35
    sex:                       Literal["M", "F"] = "M"
    weight_kg:                 float = 70.0
    smoker:                    bool = False
    hormonal_contraception:    bool = False
    pregnant:                  bool = False
    cyp1a2:                    Literal["fast", "intermediate", "slow", "unknown"] = "unknown"


def classify_chronotype(msfsc_h: float) -> ChronotypeCategory:
    """Return a categorical chronotype from MSFsc (hours)."""
    if msfsc_h < 02.50:   return ChronotypeCategory.EXTREME_LARK
    if msfsc_h < 03.50:   return ChronotypeCategory.MODERATE_LARK
    if msfsc_h < 04.50:   return ChronotypeCategory.INTERMEDIATE
    if msfsc_h < 05.50:   return ChronotypeCategory.MODERATE_OWL
    return ChronotypeCategory.EXTREME_OWL


def meq_to_msfsc_h(meq_score: float) -> float:
    """Approximate mapping from Horne-Ostberg MEQ (19-86) to MSFsc.
    Higher MEQ -> earlier midpoint."""
    # Roenneberg 2003 cross-walk: MEQ 70 -> MSFsc ~ 03:00; MEQ 30 -> MSFsc ~ 06:00
    meq = max(19.0, min(86.0, meq_score))
    return 7.5 - 0.075 * (meq - 30)  # rough linear
