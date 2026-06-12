"""Figures for the SleepArchitect paper.

    fig_two_process.pdf      - Process S, C, thresholds over a day
    fig_light_prc.pdf        - light phase-response curve + dose-response
    fig_validation.pdf       - predictions vs published literature
    fig_chronotype_sweep.pdf - bedtime x chronotype score grid
    fig_interventions.pdf    - intervention ranking for 3 archetypes
    fig_clock_mock.pdf       - elegant 24-hour clock centrepiece
    fig_alertness.pdf        - SAFTE alertness curve over 24+ hours
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from sleeparchitect import (
    Person, DaySchedule, forecast_sleep,
    S_INIT, S_TAU_WAKE, circadian_C_at_phase,
    SLEEP_UPPER_THRESHOLD, SLEEP_LOWER_THRESHOLD,
    light_phase_shift_h, melatonin_suppression_pct,
    safte_alertness_curve,
)
from sleeparchitect.process_s import process_s_during_wake, process_s_during_sleep
from sleeparchitect.alertness import R_CAPACITY_UNIT_MIN


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
FIG_DIR = ROOT / "paper" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 110, "savefig.dpi": 200, "font.size": 10,
    "axes.titlesize": 11, "axes.labelsize": 10, "legend.fontsize": 8,
    "figure.constrained_layout.use": True,
    "axes.spines.top": False, "axes.spines.right": False,
})

ACCENT = "#6f95ee"; VIOLET = "#bf94f0"; GOLD = "#e6c46c"
REM = "#d36a86"; SWS = "#6f95ee"; N12 = "#98a3bf"; WAKE = "#444a5a"
GOOD = "#4cd0a0"; BAD = "#f06464"; GREY = "#5b6566"


def fig_two_process():
    """Process S, C, H_upper, H_lower over a 32-hour day."""
    fig, ax = plt.subplots(figsize=(8, 3.6))
    t = np.linspace(0, 32, 320)
    msfsc = 4.0
    bed = 23.0
    wake = 7.0
    S0 = S_INIT
    S = np.zeros_like(t)
    state = np.zeros_like(t, dtype=int)
    prev_S = S0
    for i, tt in enumerate(t):
        if i == 0:
            S[i] = prev_S; continue
        dt = t[i] - t[i-1]
        is_sleep = bed <= tt < bed + 8
        if is_sleep:
            prev_S = process_s_during_sleep(prev_S, dt)
        else:
            prev_S = process_s_during_wake(prev_S, dt)
        S[i] = prev_S
        state[i] = 0 if is_sleep else 1
    Hu = np.array([SLEEP_UPPER_THRESHOLD(tt % 24, msfsc) for tt in t])
    Hl = np.array([SLEEP_LOWER_THRESHOLD(tt % 24, msfsc) for tt in t])
    ax.fill_between(t, 0, 1, where=(t >= bed) & (t < bed + 8),
                      color="#6f95ee", alpha=0.10, label="sleep window")
    ax.plot(t, S, color=VIOLET, lw=2.4, label="Process S")
    ax.plot(t, Hu, color=GOLD, lw=1.5, label="$H_{upper}$ (sleep above)")
    ax.plot(t, Hl, color=N12, lw=1.0, label="$H_{lower}$ (wake below)")
    ax.set_xlabel("Clock hour (extending into next day)")
    ax.set_ylabel("Sleep pressure / threshold")
    ax.set_xticks([0, 6, 12, 18, 24, 30])
    ax.set_xticklabels(["00", "06", "12", "18", "00", "06"])
    ax.set_ylim(0, 1.0)
    ax.legend(loc="upper right")
    ax.set_title("Two-process model: homeostatic S + circadian thresholds")
    fig.savefig(FIG_DIR / "fig_two_process.pdf")
    plt.close(fig)


def fig_light_prc():
    """Light PRC + dose-response (Khalsa 2003 / Zeitzer 2000)."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.3))
    # Phase response curve: phase shift vs midpoint
    mids = np.linspace(0, 24, 200)
    shifts = [light_phase_shift_h(1000, 6.5, m, 4.0) for m in mids]
    ax1.fill_between(mids, 0, shifts, where=np.array(shifts) > 0,
                       color=GOOD, alpha=0.25, label="advance")
    ax1.fill_between(mids, 0, shifts, where=np.array(shifts) < 0,
                       color=BAD, alpha=0.25, label="delay")
    ax1.plot(mids, shifts, color=ACCENT, lw=2)
    ax1.axvline(3, color="grey", lw=0.8, ls="--")
    ax1.text(3.2, -1.5, "CBT$_{\\min}$", color=GREY, fontsize=8)
    ax1.set_xlabel("Clock hour of midpoint of 6.5-h, 1000 lux exposure")
    ax1.set_ylabel("Phase shift (h)")
    ax1.set_xlim(0, 24)
    ax1.set_title("Light PRC (Khalsa 2003)")
    ax1.legend()
    # Dose-response
    lux = np.logspace(0, 4, 120)
    shifts_dose = [abs(light_phase_shift_h(l, 6.5, 22.0, 4.0)) for l in lux]
    mel = [melatonin_suppression_pct(l) for l in lux]
    ax2.semilogx(lux, shifts_dose, color=VIOLET, lw=2, label="phase shift (h)")
    ax2.set_xlabel("Lux"); ax2.set_ylabel("Phase shift (h)", color=VIOLET)
    ax2.tick_params(axis='y', labelcolor=VIOLET)
    ax2.set_xlim(1, 1e4)
    ax2t = ax2.twinx()
    ax2t.semilogx(lux, mel, color=GOLD, lw=2, ls="--", label="melatonin suppression %")
    ax2t.set_ylabel("Melatonin suppression (%)", color=GOLD)
    ax2t.tick_params(axis='y', labelcolor=GOLD); ax2t.set_ylim(0, 105)
    ax2.set_title("Light dose-response (Zeitzer 2000)")
    fig.savefig(FIG_DIR / "fig_light_prc.pdf")
    plt.close(fig)


def fig_validation():
    data = json.loads((RESULTS / "validation.json").read_text())
    rows = data["per_case"]
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    y = np.arange(len(rows))
    for i, r in enumerate(rows):
        lo, hi = r.get("lo", 0), r.get("hi", 100)
        ax.barh(i, hi - lo, left=lo, color="lightgrey", edgecolor="grey",
                 label="Published range" if i == 0 else None)
        ax.plot([r["predicted"]], [i], "o", color=VIOLET, markersize=10,
                 label="SleepArchitect" if i == 0 else None)
        src = r.get("source", "")
        ax.text(98, i + 0.35, src, ha="right", va="bottom",
                  fontsize=6.5, color=GREY)
    ax.set_yticks(y); ax.set_yticklabels([r["check"][:55] for r in rows], fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Value (units vary)")
    ax.set_title("Validation of SleepArchitect against published literature")
    ax.legend(loc="lower right", fontsize=8)
    fig.savefig(FIG_DIR / "fig_validation.pdf")
    plt.close(fig)


def fig_chronotype_sweep():
    """Bedtime x chronotype grid showing sleep score."""
    msfsc_range = np.arange(2.0, 7.1, 0.5)
    bedtimes = np.arange(20.0, 26.1, 0.5)
    Z = np.zeros((len(msfsc_range), len(bedtimes)))
    for i, ms in enumerate(msfsc_range):
        for j, bt in enumerate(bedtimes):
            wake = max(4.0, bt - 8.0) if bt <= 24 else 7.0
            person = Person(chronotype_msfsc_h=ms)
            sched = DaySchedule(
                wake_time_h=wake, target_bedtime_h=bt,
                caffeine=[(wake, 95)], exercise=[(wake + 11, "moderate", 30)],
                light_lux_evening=80, last_meal_h=bt - 3,
                prev_night_sleep_h=7.5, screen_time_late=False,
            )
            Z[i, j] = forecast_sleep(person, sched).sleep_score
    fig, ax = plt.subplots(figsize=(8, 4))
    im = ax.imshow(Z, origin="lower", aspect="auto",
                     extent=(bedtimes[0], bedtimes[-1], msfsc_range[0], msfsc_range[-1]),
                     cmap="RdYlGn", vmin=70, vmax=100)
    ax.set_xlabel("Target bedtime (clock h)")
    ax.set_ylabel("Chronotype MSFsc (h)")
    ax.set_title("Sleep score vs (chronotype, bedtime) -- otherwise clean inputs")
    cbar = plt.colorbar(im, ax=ax, label="Sleep score")
    fig.savefig(FIG_DIR / "fig_chronotype_sweep.pdf")
    plt.close(fig)


def fig_interventions():
    data = json.loads((RESULTS / "interventions.json").read_text())
    archetypes = data["per_archetype"]
    fig, axes = plt.subplots(1, len(archetypes), figsize=(11, 3.5))
    if len(archetypes) == 1: axes = [axes]
    pretty = {"knowledge_worker_bad_day": "Knowledge worker, bad day",
                "weekend_bender": "Weekend bender",
                "owl_forced_to_sleep_early": "Owl, forced 22:00 bedtime"}
    for ax, spec in zip(axes, archetypes):
        rows = sorted(spec["interventions"], key=lambda r: -r["score_delta"])[:6]
        labels = [r["intervention"].replace("_", " ") for r in rows]
        deltas = [r["score_delta"] for r in rows]
        y = np.arange(len(labels))
        colors = [GOOD if d > 0.5 else (GREY if d > -0.5 else BAD) for d in deltas]
        ax.barh(y, deltas, color=colors, alpha=0.85)
        ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8)
        ax.invert_yaxis()
        ax.axvline(0, color="grey", lw=0.6)
        ax.set_xlabel("Sleep score delta")
        ax.set_title(pretty.get(spec["archetype"], spec["archetype"]),
                       fontsize=9.5)
        for i, d in enumerate(deltas):
            ax.text(d + 0.2, i, f"{d:+.1f}", va="center", fontsize=8)
        ax.set_xlim(-3, max(deltas) + 3)
    fig.suptitle("Intervention ranking by score delta")
    fig.savefig(FIG_DIR / "fig_interventions.pdf")
    plt.close(fig)


def fig_clock_mock():
    """Elegant 24-hour clock visualisation for the paper's frontend showcase."""
    fig, ax = plt.subplots(figsize=(6.5, 6.5), subplot_kw={"projection": "polar"})
    msfsc = 4.0
    cbt_min = (msfsc - 1) % 24
    dlmo = (msfsc - 7) % 24
    bedtime = 23.0; onset = 23.4; morning = 31.0  # = 7:00 next day
    # Hour angle: 00:00 at top, clockwise
    def hour_to_theta(h):
        return np.pi/2 - (h % 24) / 24 * 2 * np.pi
    # Circadian band
    thetas = np.linspace(0, 2*np.pi, 240)
    for k in range(240):
        h = (k / 240) * 24
        a1 = hour_to_theta(h)
        a2 = hour_to_theta(h + 24/240)
        dh = abs(h - cbt_min);
        if dh > 12: dh = 24 - dh
        phase = dh / 12
        cnight = np.array([25, 35, 70]) / 255
        cpeak = np.array([230, 196, 108]) / 255
        col = cnight + (cpeak - cnight) * phase
        ax.plot([a1, a2], [0.85, 0.85], color=col, linewidth=24, solid_capstyle="butt")
    # Sleep arc
    a_onset = hour_to_theta(onset); a_wake = hour_to_theta(morning)
    arc_thetas = np.linspace(a_onset, a_wake, 60) if a_wake <= a_onset else np.linspace(a_onset - 2*np.pi, a_wake, 60)
    if a_wake > a_onset:
        arc_thetas = np.linspace(a_onset, a_onset - (24 - (morning - onset))/24 * 2*np.pi, 60)
    ax.plot(arc_thetas, [0.65] * len(arc_thetas), color=ACCENT, lw=20, alpha=0.85)
    # Caffeine doses
    for t, mg in [(7.0, 95), (10.5, 95), (15.0, 200)]:
        a = hour_to_theta(t)
        ax.plot([a], [0.72], "o", color=REM, markersize=8 + np.sqrt(mg)/2.5, alpha=0.9)
    # Alcohol
    for t, n in [(20.0, 2.0)]:
        a = hour_to_theta(t)
        ax.plot([a], [0.78], "o", color=GOLD, markersize=8 + n*2.5, alpha=0.9)
    # Exercise arc
    a1 = hour_to_theta(18.0); a2 = hour_to_theta(18.5)
    ax.plot(np.linspace(a1, a2, 12), [0.42] * 12, color=GOOD, lw=8)
    # Meal
    a = hour_to_theta(20.5)
    ax.plot([a], [0.55], "o", color="#f5a37b", markersize=12)
    # CBTmin tick
    a = hour_to_theta(cbt_min)
    ax.plot([a, a], [0.85, 0.95], color=N12, lw=2)
    # DLMO tick
    a = hour_to_theta(dlmo)
    ax.plot([a, a], [0.85, 0.95], color=VIOLET, lw=2)
    # Hour labels
    for h in range(0, 24, 6):
        a = hour_to_theta(h)
        ax.text(a, 1.05, f"{h:02d}", ha="center", va="center", fontsize=10, color="#e8ecf4")
    # Centre
    ax.text(0, 0, "23:24 → 07:00\nscore 86\nTST 7.6 h",
              ha="center", va="center", fontsize=10, color="#e8ecf4")
    ax.set_facecolor("#1c2238")
    fig.patch.set_facecolor("#0f1421")
    ax.set_ylim(0, 1.1)
    ax.set_yticks([]); ax.set_xticks([])
    ax.grid(False)
    ax.spines["polar"].set_visible(False)
    fig.savefig(FIG_DIR / "fig_clock_mock.pdf",
                  facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def fig_alertness():
    """SAFTE alertness through tomorrow."""
    person = Person()
    today = DaySchedule(wake_time_h=7.0, target_bedtime_h=23.0,
                          caffeine=[(7.0, 95), (13.0, 95)],
                          alcohol_drinks=[], exercise=[(18.0, "moderate", 30)],
                          light_lux_evening=80, last_meal_h=19.0,
                          prev_night_sleep_h=7.5, screen_time_late=False)
    fc = forecast_sleep(person, today)
    alertness = fc.alertness_curve

    fig, ax = plt.subplots(figsize=(9, 3.5))
    # Sleep band
    ax.axvspan(fc.sleep_onset_clock_h, fc.morning_wake_clock_h,
                 color=ACCENT, alpha=0.10, label="sleep window")
    ax.plot(alertness.times_h, alertness.effectiveness, color=ACCENT, lw=2.4,
              label="SAFTE effectiveness (0-100)")
    ax2 = ax.twinx()
    ax2.plot(alertness.times_h, alertness.kss, color=GOLD, lw=1.8, ls="--",
                 label="KSS (1=alert, 9=sleepy)")
    ax.set_xlabel("Clock hour (extending into tomorrow)")
    ax.set_ylabel("Effectiveness", color=ACCENT)
    ax2.set_ylabel("KSS", color=GOLD)
    ax.set_xticks([7, 12, 18, 23, 31, 36, 41, 46])
    ax.set_xticklabels(["07", "12", "18", "23", "07", "12", "17", "22"])
    ax.set_title("SAFTE alertness curve over tonight + tomorrow")
    ax.legend(loc="upper right", fontsize=8); ax2.legend(loc="lower right", fontsize=8)
    fig.savefig(FIG_DIR / "fig_alertness.pdf")
    plt.close(fig)


def main():
    fig_two_process()
    fig_light_prc()
    fig_validation()
    fig_chronotype_sweep()
    fig_interventions()
    fig_clock_mock()
    fig_alertness()
    print(f"Wrote figures to {FIG_DIR}")
    for f in sorted(FIG_DIR.glob("*.pdf")):
        print(f"  {f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
