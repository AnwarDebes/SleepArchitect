// SleepArchitect frontend. Mirrors the Python library physics.

"use strict";

// ============================================================ physics ==

const S_TAU_WAKE = 18.2;
const S_TAU_SLEEP = 4.2;
const S_INIT = 0.40;
const SLEEP_UPPER_BASE = 0.60;
const SLEEP_LOWER_BASE = 0.17;
const C_A1 = 0.12, C_A2 = 0.04;

function processS_during_wake(S0, dt_h) {
  return 1.0 - (1.0 - S0) * Math.exp(-dt_h / S_TAU_WAKE);
}
function processS_during_sleep(S0, dt_h) {
  return S0 * Math.exp(-dt_h / S_TAU_SLEEP);
}
function circadian_C(clock_h, msfsc_h) {
  const nadir = msfsc_h - 1.0;
  const t_rel = ((clock_h - nadir) % 24 + 24) % 24;
  return C_A1 * Math.sin(2*Math.PI*t_rel/24) + C_A2 * Math.sin(4*Math.PI*t_rel/24);
}
function H_upper(clock_h, msfsc_h) { return SLEEP_UPPER_BASE + 0.1 * circadian_C(clock_h, msfsc_h); }
function H_lower(clock_h, msfsc_h) { return SLEEP_LOWER_BASE + 0.1 * circadian_C(clock_h, msfsc_h); }

// caffeine PK
function _caf_half_life(p) {
  let f = 1.0;
  if (p.smoker)          f *= 0.50;
  if (p.pregnant)        f *= 1.59;
  if (p.hc)              f *= 1.65;
  if (p.age >= 65)       f *= 1.30;
  if (p.cyp1a2 === "fast") f *= 0.85;
  else if (p.cyp1a2 === "slow") f *= 1.30;
  return Math.max(1.0, Math.min(100, 5.0 * f));
}
function caffeine_burden_at_bedtime(p, doses, bedtime_h) {
  if (!doses.length) return 0;
  const t12 = _caf_half_life(p);
  const k_e = Math.log(2) / t12;
  const k_a = 5.0;
  const F = 1.0;
  const V_L = 0.5 * p.weight_kg;
  let total_C = 0;
  for (const [t_dose, mg] of doses) {
    const dt = bedtime_h - t_dose;
    if (dt <= 0) continue;
    const pre = (F * mg * k_a) / (V_L * (k_a - k_e));
    total_C += pre * (Math.exp(-k_e * dt) - Math.exp(-k_a * dt));
  }
  return total_C * V_L;
}
function caffeine_sol_delay_min(burden_mg) {
  return Math.max(0, 0.10 * (burden_mg - 50));
}
function caffeine_sws_suppression_pct(burden_mg) {
  return Math.max(0, Math.min(40, 0.07 * (burden_mg - 50)));
}

// alcohol PK
function BAC_at_time(weight, sex, drinks, t_h) {
  const r = sex === "M" ? 0.68 : 0.55;
  let bac = 0;
  for (const [t_drink, n] of drinks) {
    if (t_h <= t_drink) continue;
    const eth_g = n * 14;
    const peak = eth_g / (weight * r * 10);
    const elapsed = Math.max(0, t_h - t_drink - 0.5);
    bac += Math.max(0, peak - 0.015 * elapsed);
  }
  return bac;
}
function alcohol_rem_suppression_first_half_pct(bac) { return Math.max(0, Math.min(40, 320 * bac)); }
function alcohol_rem_rebound_pct(bac) { return Math.max(0, Math.min(20, 200 * bac)); }
function alcohol_sol_change_min(bac) { return -10 * Math.min(0.05, bac) * 20; }

// exercise
function exercise_sol_delay_min(bouts, bedtime_h) {
  let total = 0;
  for (const [start, intensity, dur_min] of bouts) {
    const gap = bedtime_h - (start + dur_min / 60);
    const factor = { light: 0.3, moderate: 1.0, vigorous: 1.8 }[intensity] || 1.0;
    if (gap < 0) { total += 10 * factor; continue; }
    if (gap < 1) total += 8 * factor * (1 - gap);
    else if (gap < 3) total += 2 * factor * (1 - (gap - 1) / 2);
    else total += -2 * factor * Math.min(1, (gap - 3) / 6);
  }
  return total;
}
function exercise_sws_boost_pp(bouts) {
  let total = 0;
  for (const [, intensity, dur_min] of bouts) {
    const f = { light: 0.3, moderate: 1.0, vigorous: 1.5 }[intensity] || 1.0;
    total += 1.3 * f * Math.min(1, dur_min / 30);
  }
  return Math.min(5, total);
}

// meal
function meal_sol_delay_min(last_meal_h, bedtime_h, size) {
  const gap = bedtime_h - last_meal_h;
  if (gap >= 3 || gap < 0) return 0;
  const f = { light: 0.4, medium: 1.0, heavy: 1.8 }[size] || 1.0;
  return f * 20 * (1 - gap / 3);
}
function meal_rem_reduction_pp(last_meal_h, bedtime_h, size) {
  const gap = bedtime_h - last_meal_h;
  if (gap >= 3 || gap < 0) return 0;
  const f = { light: 0.5, medium: 1.0, heavy: 1.6 }[size] || 1.0;
  return Math.min(5, f * 3 * (1 - gap / 3));
}

// light
function logistic_lux(lux, half_max=100, k=1.5) {
  if (lux <= 0) return 0;
  return 1 / (1 + Math.pow(half_max / lux, k));
}
function light_phase_shift_h(lux, dur_h, mid_h, msfsc_h) {
  const cbtmin = ((msfsc_h - 1) % 24 + 24) % 24;
  const resp = logistic_lux(lux);
  let dt = (mid_h - cbtmin) % 24;
  if (dt > 12) dt -= 24;
  const shape = dt > 0
    ? Math.max(0, Math.sin(Math.PI * dt / 12))
    : -Math.max(0, Math.sin(Math.PI * (-dt) / 12));
  return 2.0 * resp * (dur_h / 6.5) * shape;
}
function melatonin_suppression_pct(lux) {
  if (lux <= 0) return 0;
  return 100 * (1 - Math.exp(-lux / 100));
}

// chronotype
function classify_chronotype(msfsc) {
  if (msfsc < 2.5) return "extreme lark";
  if (msfsc < 3.5) return "moderate lark";
  if (msfsc < 4.5) return "intermediate";
  if (msfsc < 5.5) return "moderate owl";
  return "extreme owl";
}

// ============================================================ forecast =

function forecastSleep(person, schedule) {
  const wake = schedule.wake_h;
  const bed = schedule.bed_h;
  const target_TST = 8;
  const morning_wake = bed + target_TST;

  // S0 scaled by previous sleep
  const S0 = Math.max(0.05, Math.min(0.60, S_INIT * (8 / Math.max(schedule.prev_sleep_h, 4))));
  const hours_awake = bed - wake;
  const S_bed = processS_during_wake(S0, Math.max(0, hours_awake));
  const C_bed = circadian_C(bed % 24, person.msfsc);
  const H_up = H_upper(bed % 24, person.msfsc);

  // SOL components
  let sol_base = 12;
  if (S_bed < H_up) sol_base += 30 * (H_up - S_bed) / Math.max(0.05, H_up);
  const burden = caffeine_burden_at_bedtime(person, schedule.caffeine, bed);
  const sol_caf = caffeine_sol_delay_min(burden);
  const bac_b = BAC_at_time(person.weight_kg, person.sex, schedule.alcohol, bed);
  const sol_alc = alcohol_sol_change_min(bac_b);
  const sol_ex = exercise_sol_delay_min(schedule.exercise, bed);
  const sol_meal = meal_sol_delay_min(schedule.last_meal_h, bed, schedule.meal_size);
  const sol_screen = schedule.screen_late ? 8 : 0;
  const mel = melatonin_suppression_pct(schedule.light_lux);
  const sol_light = 0.30 * mel / 10;
  const sol_total = Math.max(2, sol_base + sol_caf + sol_alc + sol_ex + sol_meal + sol_screen + sol_light);

  const onset_h = bed + sol_total / 60;
  const tst_h = Math.max(0.5, morning_wake - onset_h);
  const waso_caf  = burden * 0.05;
  const waso_alc  = 35 * bac_b;
  const waso_meal = sol_meal * 0.2;
  const waso_min = Math.max(8, 12 + waso_caf + waso_alc + waso_meal);
  const time_in_bed_min = (morning_wake - bed) * 60;
  const se = Math.min(100, Math.max(40, 100 * (tst_h * 60 - waso_min) / time_in_bed_min));

  // architecture
  const sws_mod_caf = -caffeine_sws_suppression_pct(burden);
  const sws_mod_ex  = exercise_sws_boost_pp(schedule.exercise);
  const sws_mod = sws_mod_caf + sws_mod_ex;
  const rem_first = -alcohol_rem_suppression_first_half_pct(bac_b)
                    - meal_rem_reduction_pp(schedule.last_meal_h, bed, schedule.meal_size);
  const rem_second = alcohol_rem_rebound_pct(bac_b)
                    - 0.3 * meal_rem_reduction_pp(schedule.last_meal_h, bed, schedule.meal_size);

  const hyp = simulateHypnogram(tst_h * 60, sws_mod, rem_first, rem_second, waso_min - 12);
  const props = sleepProportions(hyp);

  // sleep score (0-100)
  let score = 100;
  score -= Math.max(0, sol_total - 15) * 0.6;
  score -= Math.max(0, 7.5 - tst_h) * 8;
  score -= Math.max(0, 85 - se) * 1.0;
  score -= Math.max(0, -sws_mod) * 0.4;
  score = Math.max(0, Math.min(100, score));

  let interp;
  if (score >= 80) interp = "Predicted sleep should be restorative.";
  else if (score >= 65) interp = "Sleep should be acceptable but suboptimal.";
  else if (score >= 50) interp = "Significant sleep disruption likely.";
  else interp = "Severe sleep disruption likely; consider interventions.";

  return {
    person, schedule,
    sol_min: sol_total, tst_h, se,
    onset_h, morning_wake_h: morning_wake,
    sws_pct: props.sws, rem_pct: props.rem, n12_pct: props.n12,
    waso_min, hypnogram: hyp,
    S_at_bedtime: S_bed, H_upper_at_bedtime: H_up, C_at_bedtime: C_bed,
    caffeine_burden_mg: burden, bac_at_bedtime: bac_b,
    phase_shift_h: light_phase_shift_h(schedule.light_lux, 2,
                                        bed - 2, person.msfsc),
    melatonin_suppression: mel,
    sleep_score: score, interpretation: interp,
  };
}

const CYCLE_MIN = 95;
function _stage_dist(cycle_i, n_cycles) {
  const progress = cycle_i / Math.max(1, n_cycles - 1);
  const sws = Math.max(0.05, 0.45 - 0.40 * progress);
  const rem = Math.min(0.45, 0.08 + 0.32 * progress);
  const residual = Math.max(0.05, 1 - sws - rem);
  const n1 = 0.10;
  const n2 = Math.max(0.05, residual - n1);
  return [n1, n2, sws, rem];
}
function simulateHypnogram(tst_min, sws_mod_pp, rem_first_pp, rem_second_pp, waso_min) {
  const n_cycles = Math.max(2, Math.round(tst_min / CYCLE_MIN));
  const cycle_dur = tst_min / n_cycles;
  const n_t = Math.floor(tst_min) + 1;
  const times = new Array(n_t);
  const stage = new Array(n_t).fill(0);
  for (let i = 0; i < n_t; i++) times[i] = i;
  let cum_sws = 0, cum_rem = 0, cum_n12 = 0;
  for (let c = 0; c < n_cycles; c++) {
    let frac = _stage_dist(c, n_cycles);
    let frac_sws = Math.max(0, frac[2] + sws_mod_pp/100);
    const first_half = c < n_cycles / 2;
    const rem_mod = first_half ? rem_first_pp/100 : rem_second_pp/100;
    let frac_rem = Math.max(0, frac[3] + rem_mod);
    let frac_n1 = frac[0], frac_n2 = frac[1];
    const total = frac_n1 + frac_n2 + frac_sws + frac_rem;
    if (total <= 0) continue;
    frac_n1 /= total; frac_n2 /= total; frac_sws /= total; frac_rem /= total;
    const c_start = c * cycle_dur, c_end = (c + 1) * cycle_dur;
    const durs = [frac_n1, frac_n2 * 0.4, frac_sws, frac_n2 * 0.6, frac_rem];
    const codes = [1, 2, 3, 2, 4];
    let t_s = c_start;
    for (let i = 0; i < durs.length; i++) {
      const t_e = t_s + durs[i] * cycle_dur;
      for (let k = Math.max(0, Math.floor(t_s)); k < Math.min(n_t, Math.floor(t_e)); k++)
        stage[k] = codes[i];
      t_s = t_e;
    }
    cum_sws += frac_sws * cycle_dur;
    cum_rem += frac_rem * cycle_dur;
    cum_n12 += (frac_n1 + frac_n2) * cycle_dur;
  }
  // WASO inserts (deterministic positions)
  if (waso_min > 0) {
    const n = Math.max(1, Math.floor(waso_min / 3));
    for (let i = 0; i < n; i++) {
      const idx = Math.floor(0.55 * n_t + (0.40 * n_t) * (i / Math.max(1, n - 1)));
      for (let k = idx; k < Math.min(n_t, idx + 3); k++) stage[k] = 0;
    }
  }
  return { times, stage, sws_min: cum_sws, rem_min: cum_rem, n12_min: cum_n12, waso_min };
}
function sleepProportions(hyp) {
  const total = hyp.sws_min + hyp.rem_min + hyp.n12_min;
  if (total <= 0) return { sws: 0, rem: 0, n12: 0 };
  return { sws: 100*hyp.sws_min/total, rem: 100*hyp.rem_min/total, n12: 100*hyp.n12_min/total };
}

// SAFTE alertness
const R_CAP = 2880;
function safteAlertness(wake_h, bed_h, morning_wake, R0, msfsc, end_h, sleep_intensity) {
  end_h = end_h || morning_wake + 17;
  const dt = 0.1;
  const n = Math.max(2, Math.round((end_h - wake_h) / dt));
  const times = new Array(n);
  const R = new Array(n);
  const E = new Array(n);
  R[0] = R0;
  for (let k = 0; k < n; k++) {
    const t = wake_h + k * dt;
    times[k] = t;
    if (k > 0) {
      const prev_sleep = bed_h <= times[k - 1] && times[k - 1] < morning_wake;
      if (prev_sleep) R[k] = Math.min(R_CAP, R[k-1] + 264 * dt * sleep_intensity);
      else R[k] = Math.max(0, R[k-1] - 30 * dt);
    }
    const clock = ((t % 24) + 24) % 24;
    const C = 80 * circadian_C(clock, msfsc);
    let inertia = 0;
    if (t - wake_h >= 0 && t - wake_h < 2) inertia = -12 * Math.exp(-(t - wake_h) * 60 / 30);
    else if (t - morning_wake >= 0 && t - morning_wake < 2)
      inertia = -12 * Math.exp(-(t - morning_wake) * 60 / 30);
    E[k] = 100 * R[k] / R_CAP + C + inertia;
  }
  const kss = E.map(e => Math.max(1, Math.min(9, 9 - 0.07 * e)));
  return { times, E, kss };
}

// interventions
const INTERVENTIONS = [
  { key: "no_screens", label: "No bright screens within 1 h of bed",
    desc: "Smartphone/tablet at the face delivers ~50-100 lux.",
    apply: s => ({...s, screen_late: false}) },
  { key: "eat_earlier", label: "Eat last meal 1 hour earlier",
    desc: "Meals within 2 h of bed delay SOL by 10-30 min (Crispim 2011).",
    apply: s => ({...s, last_meal_h: s.last_meal_h - 1}) },
  { key: "dim_evening_light", label: "Dim ambient light below 30 lux 2 h pre-bed",
    desc: "Reduces melatonin suppression; promotes sleep onset.",
    apply: s => ({...s, light_lux: Math.min(s.light_lux, 30)}) },
  { key: "delay_bedtime", label: "Delay bedtime by 30 minutes",
    desc: "Lets sleep pressure build above threshold (anti-insomnia).",
    apply: s => ({...s, bed_h: s.bed_h + 0.5}) },
  { key: "advance_bedtime", label: "Go to bed 30 minutes earlier",
    desc: "Extends sleep window if TST is the bottleneck.",
    apply: s => ({...s, bed_h: s.bed_h - 0.5}) },
  { key: "skip_last_caffeine", label: "Skip your last caffeinated drink",
    desc: "Removes residual caffeine that suppresses SWS and delays SOL.",
    apply: s => ({...s, caffeine: s.caffeine.slice(0, -1)}) },
  { key: "halve_last_caffeine", label: "Halve your last caffeinated drink",
    desc: "Cuts the bedtime caffeine burden contribution in half.",
    apply: s => {
      if (!s.caffeine.length) return s;
      const nc = s.caffeine.slice();
      nc[nc.length - 1] = [nc[nc.length - 1][0], nc[nc.length - 1][1] / 2];
      return {...s, caffeine: nc};
    }},
  { key: "skip_alcohol", label: "Skip the alcoholic drinks tonight",
    desc: "Removes first-half-night REM suppression + second-half fragmentation.",
    apply: s => ({...s, alcohol: []}) },
  { key: "exercise_earlier", label: "Move evening exercise 3 h earlier",
    desc: "Vigorous within 1 h of bed adds 6-10 min SOL.",
    apply: s => ({...s, exercise: s.exercise.map(([t,i,d])=>[t-3,i,d])}) },
];
function rankInterventions(person, schedule) {
  const base = forecastSleep(person, schedule);
  const rows = INTERVENTIONS.map(intv => {
    const s2 = intv.apply(schedule);
    const fc = forecastSleep(person, s2);
    return {
      key: intv.key, label: intv.label, desc: intv.desc,
      score_delta: fc.sleep_score - base.sleep_score,
      sol_delta: fc.sol_min - base.sol_min,
      tst_delta: fc.tst_h - base.tst_h,
      sws_delta: fc.sws_pct - base.sws_pct,
      rem_delta: fc.rem_pct - base.rem_pct,
      base_score: base.sleep_score, after_score: fc.sleep_score,
    };
  });
  rows.sort((a, b) => b.score_delta - a.score_delta);
  return { base, rows };
}

// ============================================================ DOM =====

const els = {};
const ids = ["msfsc","msfsc_readout","age","weight_kg","sex","cyp1a2","smoker","hc",
              "wake_time_h","bedtime_h","prev_sleep_h","last_meal_h","meal_size",
              "light_lux","light_readout","screen_late",
              "caffeine_list","alcohol_list","exercise_list",
              "add_caffeine","add_alcohol","add_exercise",
              "recompute","saveProfile","loadProfile",
              "score_value","score_ring_arc","interpretation",
              "m_sol","m_tst","m_se","m_sws","m_rem","m_waso",
              "hypno_chart","archi_donut","two_process",
              "clock_chart","alertness_chart",
              "best_focus_time","worst_focus_time","energy_peak",
              "opt_table"];
for (const id of ids) els[id] = document.getElementById(id);

function fmt2(x) { const h = Math.floor(x); const m = Math.round((x-h)*60); return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}`; }

// Tab switching
document.querySelectorAll(".tab").forEach(b => b.addEventListener("click", () => {
  const tab = b.dataset.tab;
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t === b));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.toggle("active", p.dataset.panel === tab));
  // redraw the relevant tab
  if (LAST_FC) {
    if (tab === "tonight") renderTonight(LAST_FC);
    else if (tab === "clock") renderClock(LAST_FC);
    else if (tab === "tomorrow") renderTomorrow(LAST_FC);
    else if (tab === "optimize") renderOptimize();
  }
}));

// Dynamic lists -- caffeine / alcohol / exercise rows
function makeRow(type, t=null, val=null, intensity=null, dur=null) {
  const row = document.createElement("div");
  row.className = "item-row" + (type === "exercise" ? " three" : "");
  const tInput = document.createElement("input");
  tInput.type = "number"; tInput.min = 0; tInput.max = 32; tInput.step = 0.25;
  tInput.value = t ?? (type === "exercise" ? 18.0 : type === "alcohol" ? 20.0 : 7.0);
  tInput.placeholder = "Hour";
  row.appendChild(_wrapLabel(tInput, "Time (h)"));
  if (type === "exercise") {
    const iSel = document.createElement("select");
    for (const v of ["light", "moderate", "vigorous"]) {
      const o = document.createElement("option"); o.value = v; o.textContent = v;
      if (v === (intensity || "moderate")) o.selected = true;
      iSel.appendChild(o);
    }
    row.appendChild(_wrapLabel(iSel, "Intensity"));
    const dInput = document.createElement("input");
    dInput.type = "number"; dInput.min = 5; dInput.max = 180; dInput.step = 5;
    dInput.value = dur ?? 30;
    row.appendChild(_wrapLabel(dInput, "Duration (min)"));
  } else {
    const vInput = document.createElement("input");
    vInput.type = "number"; vInput.min = 0; vInput.step = type === "caffeine" ? 5 : 0.5;
    vInput.value = val ?? (type === "caffeine" ? 95 : 1);
    row.appendChild(_wrapLabel(vInput, type === "caffeine" ? "mg caffeine" : "Drinks"));
  }
  const rm = document.createElement("button");
  rm.className = "remove-btn"; rm.textContent = "×";
  rm.addEventListener("click", () => { row.remove(); computeAndRender(); });
  row.appendChild(rm);
  // Wire inputs
  row.querySelectorAll("input, select").forEach(el =>
    el.addEventListener("input", computeAndRender));
  return row;
}
function _wrapLabel(input, lbl) {
  const w = document.createElement("label");
  const span = document.createElement("span");
  span.textContent = lbl;
  w.appendChild(span); w.appendChild(input);
  return w;
}
els.add_caffeine.addEventListener("click", () => { els.caffeine_list.appendChild(makeRow("caffeine", 14, 95)); computeAndRender(); });
els.add_alcohol.addEventListener("click", () => { els.alcohol_list.appendChild(makeRow("alcohol")); computeAndRender(); });
els.add_exercise.addEventListener("click", () => { els.exercise_list.appendChild(makeRow("exercise")); computeAndRender(); });

function readList(container) {
  return Array.from(container.children).map(row => {
    const inputs = row.querySelectorAll("input, select");
    return Array.from(inputs).map(x =>
      x.type === "number" ? parseFloat(x.value) : x.value);
  });
}

function readPersonAndSchedule() {
  const person = {
    msfsc: parseFloat(els.msfsc.value),
    age: parseInt(els.age.value, 10),
    sex: els.sex.value,
    weight_kg: parseFloat(els.weight_kg.value),
    smoker: els.smoker.value === "true",
    hc: els.hc.value === "true",
    cyp1a2: els.cyp1a2.value,
  };
  const schedule = {
    wake_h: parseFloat(els.wake_time_h.value),
    bed_h: parseFloat(els.bedtime_h.value),
    prev_sleep_h: parseFloat(els.prev_sleep_h.value),
    last_meal_h: parseFloat(els.last_meal_h.value),
    meal_size: els.meal_size.value,
    light_lux: parseFloat(els.light_lux.value),
    screen_late: els.screen_late.checked,
    caffeine: readList(els.caffeine_list).map(([t, mg]) => [t, mg]),
    alcohol: readList(els.alcohol_list).map(([t, n]) => [t, n]),
    exercise: readList(els.exercise_list).map(([t, i, d]) => [t, i, d]),
  };
  return { person, schedule };
}

let LAST_FC = null;

function computeAndRender() {
  els.msfsc_readout.textContent = `${fmt2(parseFloat(els.msfsc.value))} - ${classify_chronotype(parseFloat(els.msfsc.value))}`;
  els.light_readout.textContent = `${els.light_lux.value} lux`;
  const { person, schedule } = readPersonAndSchedule();
  LAST_FC = forecastSleep(person, schedule);
  renderTonight(LAST_FC);
  // Other tabs re-render on tab switch.
}

function colorForScore(s) {
  if (s >= 80) return "var(--good)";
  if (s >= 65) return "var(--warn)";
  return "var(--bad)";
}

function renderTonight(fc) {
  els.score_value.textContent = Math.round(fc.sleep_score);
  els.score_value.style.color = colorForScore(fc.sleep_score);
  els.score_ring_arc.setAttribute("stroke-dasharray", `${fc.sleep_score} ${100 - fc.sleep_score}`);
  els.interpretation.textContent = fc.interpretation;
  els.m_sol.textContent = `${fc.sol_min.toFixed(0)} min`;
  els.m_tst.textContent = `${fc.tst_h.toFixed(2)} h`;
  els.m_se.textContent  = `${fc.se.toFixed(0)}%`;
  els.m_sws.textContent = `${fc.sws_pct.toFixed(0)}%`;
  els.m_rem.textContent = `${fc.rem_pct.toFixed(0)}%`;
  els.m_waso.textContent = `${fc.waso_min.toFixed(0)} min`;
  drawHypnogram(fc); drawArchiDonut(fc); drawTwoProcess(fc);
}

// ============================================================ charts ===

function setupCanvas(c) {
  if (!c || typeof c.getContext !== "function") return null;
  const dpr = window.devicePixelRatio || 1;
  const cssW = c.clientWidth || 800; const cssH = c.clientHeight || 240;
  c.width = cssW * dpr; c.height = cssH * dpr;
  const ctx = c.getContext("2d"); if (!ctx) return null;
  ctx.scale(dpr, dpr); ctx.clearRect(0, 0, cssW, cssH);
  return { ctx, W: cssW, H: cssH };
}

function drawHypnogram(fc) {
  const r = setupCanvas(els.hypno_chart); if (!r) return;
  const { ctx, W, H } = r;
  const padL = 36, padR = 16, padT = 12, padB = 28;
  const w = W - padL - padR, h = H - padT - padB;
  const tst = fc.hypnogram.times.length;
  const stage = fc.hypnogram.stage;
  // 5 stages: Wake / N1 / N2 / SWS / REM -> 4 rows visualised: Wake, REM, light NREM, deep NREM
  const xOf = i => padL + (i / tst) * w;
  const yMap = { 0: padT + 0.05 * h, 4: padT + 0.30 * h, 1: padT + 0.55 * h, 2: padT + 0.55 * h, 3: padT + 0.85 * h };
  const colorMap = { 0: "#444a5a", 4: "#d36a86", 1: "#98a3bf", 2: "#98a3bf", 3: "#6f95ee" };
  // Draw filled blocks
  let i = 0;
  while (i < tst) {
    const s = stage[i]; let j = i;
    while (j < tst && stage[j] === s) j++;
    const x0 = xOf(i), x1 = xOf(j);
    ctx.fillStyle = colorMap[s];
    const y = yMap[s];
    ctx.fillRect(x0, y, Math.max(1, x1 - x0), 18);
    i = j;
  }
  // Axes
  ctx.strokeStyle = "rgba(152,163,191,0.25)"; ctx.lineWidth = 1;
  for (let pct = 0; pct <= 1.0; pct += 0.25) {
    const x = padL + pct * w;
    ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, H - padB); ctx.stroke();
  }
  ctx.fillStyle = "#98a3bf"; ctx.font = "11px -apple-system, sans-serif";
  ctx.textAlign = "center";
  for (let pct = 0; pct <= 1.0; pct += 0.25) {
    const t_min = pct * tst;
    const x = padL + pct * w;
    ctx.fillText(`+${(t_min/60).toFixed(1)} h`, x, H - padB + 14);
  }
  ctx.textAlign = "right";
  ["Wake","REM","Light","Deep"].forEach((lab, idx) => {
    const y_lvls = [0.05, 0.30, 0.55, 0.85];
    ctx.fillText(lab, padL - 4, padT + y_lvls[idx] * h + 13);
  });
}

function drawArchiDonut(fc) {
  const r = setupCanvas(els.archi_donut); if (!r) return;
  const { ctx, W, H } = r;
  const cx = W / 2, cy = H / 2;
  const radius = Math.min(W, H) / 2 - 30;
  const slices = [
    { v: fc.rem_pct, c: "#d36a86", label: "REM" },
    { v: fc.sws_pct, c: "#6f95ee", label: "SWS" },
    { v: fc.n12_pct, c: "#98a3bf", label: "N1+N2" },
  ];
  let start = -Math.PI / 2;
  for (const s of slices) {
    const ang = (s.v / 100) * 2 * Math.PI;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, start, start + ang);
    ctx.arc(cx, cy, radius * 0.65, start + ang, start, true);
    ctx.closePath();
    ctx.fillStyle = s.c; ctx.fill();
    const mid = start + ang / 2;
    const lx = cx + Math.cos(mid) * radius * 0.82;
    const ly = cy + Math.sin(mid) * radius * 0.82;
    ctx.fillStyle = "#e8ecf4"; ctx.font = "11px -apple-system, sans-serif";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    ctx.fillText(`${s.label}`, lx, ly - 5);
    ctx.fillText(`${s.v.toFixed(0)}%`, lx, ly + 8);
    start += ang;
  }
  // Centre label
  ctx.fillStyle = "#98a3bf"; ctx.font = "11px -apple-system, sans-serif";
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillText(`${fc.tst_h.toFixed(1)} h`, cx, cy - 6);
  ctx.fillText("sleep", cx, cy + 8);
}

function drawTwoProcess(fc) {
  const r = setupCanvas(els.two_process); if (!r) return;
  const { ctx, W, H } = r;
  const padL = 36, padR = 16, padT = 14, padB = 28;
  const w = W - padL - padR, h = H - padT - padB;
  // Compute S trajectory through the 24-h day, with sleep window
  const dt = 0.1;
  const t_start = fc.schedule.wake_h;
  const t_end = fc.morning_wake_h;
  const n = Math.floor((t_end - t_start) / dt);
  const times = new Array(n);
  const S = new Array(n);
  const Hu = new Array(n); const Hl = new Array(n);
  const sleeping = new Array(n);
  let prev_S = Math.max(0.05, Math.min(0.60, S_INIT * (8 / Math.max(fc.schedule.prev_sleep_h, 4))));
  for (let k = 0; k < n; k++) {
    const t = t_start + k * dt;
    times[k] = t;
    const isSleep = fc.onset_h <= t && t < fc.morning_wake_h;
    sleeping[k] = isSleep ? 1 : 0;
    prev_S = isSleep ? processS_during_sleep(prev_S, dt) : processS_during_wake(prev_S, dt);
    S[k] = prev_S;
    Hu[k] = H_upper(t % 24, fc.person.msfsc);
    Hl[k] = H_lower(t % 24, fc.person.msfsc);
  }
  const yOf = v => padT + (1 - v) * h;
  const xOf = t => padL + ((t - t_start) / (t_end - t_start)) * w;
  // Sleep window band
  ctx.fillStyle = "rgba(111,149,238,0.12)";
  ctx.fillRect(xOf(fc.onset_h), padT, xOf(fc.morning_wake_h) - xOf(fc.onset_h), h);
  // Grid
  ctx.strokeStyle = "rgba(152,163,191,0.18)"; ctx.lineWidth = 1;
  for (let v = 0; v <= 1.0; v += 0.2) {
    const y = yOf(v);
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + w, y); ctx.stroke();
    ctx.fillStyle = "#98a3bf"; ctx.font = "10px -apple-system, sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(v.toFixed(1), padL - 4, y + 3);
  }
  // x ticks
  ctx.fillStyle = "#98a3bf"; ctx.textAlign = "center";
  for (let h_clock = Math.ceil(t_start); h_clock < t_end; h_clock += 4) {
    const x = xOf(h_clock); ctx.fillText(fmt2(h_clock % 24), x, H - padB + 14);
  }
  // upper/lower threshold
  function drawLine(arr, color, lw) {
    ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.beginPath();
    for (let k = 0; k < n; k++) {
      const x = xOf(times[k]); const y = yOf(arr[k]);
      if (k === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  drawLine(Hu, "#e6c46c", 1.5);
  drawLine(Hl, "rgba(152,163,191,0.7)", 1.0);
  drawLine(S,  "#bf94f0", 2.6);
}

function drawClock(fc) {
  const r = setupCanvas(els.clock_chart); if (!r) return;
  const { ctx, W, H } = r;
  const cx = W / 2, cy = H / 2;
  const R_OUT = Math.min(W, H) / 2 - 30;
  const R_HOUR = R_OUT * 0.94;
  const R_RING = R_OUT * 0.85;
  // 24-hour clock: 12 at top is "00:00 / midnight"
  function angleAtHour(h) {
    // Wrap to [0, 24)
    h = ((h % 24) + 24) % 24;
    return -Math.PI / 2 + (h / 24) * 2 * Math.PI;
  }
  function xy(a, r) { return [cx + Math.cos(a) * r, cy + Math.sin(a) * r]; }

  // Circadian gradient ring (cool blue at night/CBTmin, warm at day peak)
  const cbtmin = ((fc.person.msfsc - 1) % 24 + 24) % 24;
  for (let k = 0; k < 240; k++) {
    const h = (k / 240) * 24;
    const a1 = angleAtHour(h); const a2 = angleAtHour(h + 24/240);
    // Distance from CBTmin (0 = at nadir, 1 = opposite, 12 h away)
    let dh = Math.abs(h - cbtmin);
    if (dh > 12) dh = 24 - dh;
    const phase = dh / 12;
    // Cool dark blue at nadir; warm gold at peak
    const cnight = [25, 35, 70];
    const cpeak  = [230, 196, 108];
    const col = cnight.map((c, i) => Math.round(c + (cpeak[i] - c) * phase));
    ctx.strokeStyle = `rgba(${col[0]}, ${col[1]}, ${col[2]}, 0.85)`;
    ctx.lineWidth = 18;
    ctx.beginPath();
    ctx.arc(cx, cy, R_RING, a1, a2);
    ctx.stroke();
  }

  // Sleep window arc (predicted)
  const a_onset = angleAtHour(fc.onset_h); const a_wake = angleAtHour(fc.morning_wake_h);
  ctx.strokeStyle = "rgba(111,149,238,0.80)";
  ctx.lineWidth = 22;
  ctx.beginPath();
  ctx.arc(cx, cy, R_OUT * 0.65, a_onset, a_wake);
  ctx.stroke();

  // CBTmin marker
  const [cx1, cy1] = xy(angleAtHour(cbtmin), R_RING + 4);
  const [cx2, cy2] = xy(angleAtHour(cbtmin), R_RING + 18);
  ctx.strokeStyle = "#98a3bf"; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(cx1, cy1); ctx.lineTo(cx2, cy2); ctx.stroke();
  ctx.fillStyle = "#98a3bf"; ctx.font = "10px -apple-system, sans-serif";
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.fillText("CBTmin", cx + Math.cos(angleAtHour(cbtmin))*(R_RING+30),
                          cy + Math.sin(angleAtHour(cbtmin))*(R_RING+30));

  // DLMO (~ 2 h before MSFsc earlier; we approximate at MSFsc - 7)
  const dlmo = ((fc.person.msfsc - 7) % 24 + 24) % 24;
  const [dx1, dy1] = xy(angleAtHour(dlmo), R_RING + 4);
  const [dx2, dy2] = xy(angleAtHour(dlmo), R_RING + 18);
  ctx.strokeStyle = "#bf94f0"; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(dx1, dy1); ctx.lineTo(dx2, dy2); ctx.stroke();
  ctx.fillStyle = "#bf94f0";
  ctx.fillText("DLMO", cx + Math.cos(angleAtHour(dlmo))*(R_RING+30),
                          cy + Math.sin(angleAtHour(dlmo))*(R_RING+30));

  // Hour ticks + labels
  for (let h = 0; h < 24; h++) {
    const a = angleAtHour(h);
    const [x1, y1] = xy(a, R_OUT);
    const [x2, y2] = xy(a, R_OUT - (h % 6 === 0 ? 12 : 6));
    ctx.strokeStyle = "rgba(232,236,244,0.40)";
    ctx.lineWidth = h % 6 === 0 ? 2 : 1;
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    if (h % 6 === 0) {
      const [tx, ty] = xy(a, R_OUT - 26);
      ctx.fillStyle = "#e8ecf4"; ctx.font = "11px -apple-system, sans-serif";
      ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(String(h).padStart(2, "0"), tx, ty);
    }
  }

  // Events: caffeine
  for (const [t, mg] of fc.schedule.caffeine) {
    const a = angleAtHour(t);
    const [x, y] = xy(a, R_OUT * 0.72);
    const r_dot = 4 + Math.min(10, Math.sqrt(mg) / 2);
    ctx.fillStyle = "rgba(211, 106, 134, 0.95)";
    ctx.beginPath(); ctx.arc(x, y, r_dot, 0, 2*Math.PI); ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.5)"; ctx.lineWidth = 1; ctx.stroke();
  }
  // Alcohol
  for (const [t, n] of fc.schedule.alcohol) {
    const a = angleAtHour(t);
    const [x, y] = xy(a, R_OUT * 0.78);
    const r_dot = 4 + n * 2;
    ctx.fillStyle = "rgba(230, 196, 108, 0.95)";
    ctx.beginPath(); ctx.arc(x, y, r_dot, 0, 2*Math.PI); ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.5)"; ctx.lineWidth = 1; ctx.stroke();
  }
  // Exercise: an arc
  for (const [t, intensity, dur_min] of fc.schedule.exercise) {
    const a1 = angleAtHour(t);
    const a2 = angleAtHour(t + dur_min / 60);
    ctx.strokeStyle = "rgba(76, 208, 160, 0.95)";
    ctx.lineWidth = { light: 4, moderate: 6, vigorous: 9 }[intensity] || 6;
    ctx.beginPath(); ctx.arc(cx, cy, R_OUT * 0.42, a1, a2); ctx.stroke();
  }
  // Last meal
  const am = angleAtHour(fc.schedule.last_meal_h);
  const [mx, my] = xy(am, R_OUT * 0.55);
  ctx.fillStyle = "rgba(245, 163, 123, 0.95)";
  ctx.beginPath(); ctx.arc(mx, my, 6, 0, 2*Math.PI); ctx.fill();
  // Evening light if > 100
  if (fc.schedule.light_lux > 100) {
    const al1 = angleAtHour(fc.schedule.bed_h - 2);
    const al2 = angleAtHour(fc.schedule.bed_h);
    ctx.strokeStyle = `rgba(240, 227, 168, ${Math.min(0.9, fc.schedule.light_lux/1000)})`;
    ctx.lineWidth = 6;
    ctx.beginPath(); ctx.arc(cx, cy, R_OUT * 0.49, al1, al2); ctx.stroke();
  }

  // Centre label: time-of-sleep
  ctx.fillStyle = "#e8ecf4";
  ctx.font = "16px -apple-system, sans-serif"; ctx.textAlign = "center";
  ctx.fillText(`${fmt2(fc.onset_h)} → ${fmt2(fc.morning_wake_h)}`, cx, cy - 12);
  ctx.fillStyle = "#98a3bf"; ctx.font = "12px -apple-system, sans-serif";
  ctx.fillText(`sleep score ${Math.round(fc.sleep_score)}`, cx, cy + 8);
  ctx.fillText(`TST ${fc.tst_h.toFixed(1)} h`, cx, cy + 24);
}

function renderClock(fc) { drawClock(fc); }

function renderTomorrow(fc) {
  const intensity = 1 - Math.max(0, -caffeine_sws_suppression_pct(fc.caffeine_burden_mg))/100;
  const alertness = safteAlertness(
    fc.schedule.wake_h, fc.onset_h, fc.morning_wake_h,
    Math.min(R_CAP, R_CAP * fc.schedule.prev_sleep_h / 8),
    fc.person.msfsc, fc.morning_wake_h + 17, intensity);
  // Find peaks
  // Best focus: max E during 9-13 tomorrow (relative to wake)
  let best_idx = -1, best_E = -Infinity;
  let worst_idx = -1, worst_E = Infinity;
  let second_idx = -1, second_E = -Infinity;
  for (let k = 0; k < alertness.times.length; k++) {
    const t = alertness.times[k];
    const after_wake = t - fc.morning_wake_h;
    if (after_wake >= 2 && after_wake <= 5) {
      if (alertness.E[k] > best_E) { best_E = alertness.E[k]; best_idx = k; }
    }
    if (after_wake >= 6 && after_wake <= 9) {
      if (alertness.E[k] < worst_E) { worst_E = alertness.E[k]; worst_idx = k; }
    }
    if (after_wake >= 10 && after_wake <= 14) {
      if (alertness.E[k] > second_E) { second_E = alertness.E[k]; second_idx = k; }
    }
  }
  function clockOf(idx) {
    if (idx < 0) return "n/a";
    return fmt2(alertness.times[idx] % 24);
  }
  els.best_focus_time.textContent = clockOf(best_idx);
  els.worst_focus_time.textContent = clockOf(worst_idx);
  els.energy_peak.textContent = clockOf(second_idx);

  // Draw alertness curve
  const r = setupCanvas(els.alertness_chart); if (!r) return;
  const { ctx, W, H } = r;
  const padL = 50, padR = 20, padT = 14, padB = 32;
  const w = W - padL - padR, h_ = H - padT - padB;
  const t0 = alertness.times[0], t1 = alertness.times[alertness.times.length-1];
  const Emax = 110, Emin = 0;
  const xOf = t => padL + ((t - t0)/(t1 - t0)) * w;
  const yOf = E => padT + (1 - (E - Emin)/(Emax - Emin)) * h_;
  // Sleep band
  ctx.fillStyle = "rgba(111,149,238,0.12)";
  ctx.fillRect(xOf(fc.onset_h), padT, xOf(fc.morning_wake_h) - xOf(fc.onset_h), h_);
  // Grid
  ctx.strokeStyle = "rgba(152,163,191,0.18)";
  for (let E = 0; E <= 100; E += 25) {
    const y = yOf(E);
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + w, y); ctx.stroke();
    ctx.fillStyle = "#98a3bf"; ctx.font = "10px -apple-system, sans-serif"; ctx.textAlign = "right";
    ctx.fillText(`${E}`, padL - 4, y + 3);
  }
  // x ticks
  for (let t = Math.ceil(t0); t < t1; t += 4) {
    const x = xOf(t);
    ctx.strokeStyle = "rgba(152,163,191,0.18)";
    ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, padT + h_); ctx.stroke();
    ctx.fillStyle = "#98a3bf"; ctx.textAlign = "center"; ctx.font = "10px -apple-system, sans-serif";
    ctx.fillText(fmt2(t % 24), x, H - padB + 12);
  }
  // Alertness line
  ctx.strokeStyle = "#6f95ee"; ctx.lineWidth = 2.4; ctx.beginPath();
  for (let k = 0; k < alertness.times.length; k++) {
    const x = xOf(alertness.times[k]), y = yOf(alertness.E[k]);
    if (k === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.stroke();
  // KSS (right-axis, 9 down to 1)
  ctx.strokeStyle = "#e6c46c"; ctx.lineWidth = 1.6; ctx.beginPath();
  ctx.setLineDash([4, 4]);
  for (let k = 0; k < alertness.times.length; k++) {
    const x = xOf(alertness.times[k]);
    const y = padT + (alertness.kss[k] - 1) / 8 * h_;
    if (k === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.setLineDash([]);
  // Mark best / worst with dots
  function dot(idx, color) {
    if (idx < 0) return;
    const x = xOf(alertness.times[idx]); const y = yOf(alertness.E[idx]);
    ctx.fillStyle = color; ctx.beginPath(); ctx.arc(x, y, 6, 0, 2*Math.PI); ctx.fill();
    ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5; ctx.stroke();
  }
  dot(best_idx, "var(--good)" === "var(--good)" ? "#4cd0a0" : "#4cd0a0");
  dot(worst_idx, "#f06464");
  dot(second_idx, "#bf94f0");
}

function renderOptimize() {
  if (!LAST_FC) return;
  const { rows } = rankInterventions(LAST_FC.person, LAST_FC.schedule);
  let html = `<table class="opt-table"><thead><tr>
    <th>Intervention</th>
    <th style="text-align:right">Score Δ</th>
    <th style="text-align:right">SOL Δ</th>
    <th style="text-align:right">TST Δ</th>
    <th style="text-align:right">SWS Δ</th>
    <th style="text-align:right">REM Δ</th>
  </tr></thead><tbody>`;
  for (const r of rows) {
    const cls = (v) => v > 0.5 ? "delta" : (v < -0.5 ? "delta neg" : "delta zero");
    html += `<tr>
      <td><div class="iname">${r.label}</div><div class="idesc">${r.desc}</div></td>
      <td style="text-align:right"><span class="${cls(r.score_delta)}">${r.score_delta >= 0 ? "+" : ""}${r.score_delta.toFixed(1)}</span></td>
      <td style="text-align:right"><span class="${cls(-r.sol_delta)}">${r.sol_delta >= 0 ? "+" : ""}${r.sol_delta.toFixed(1)} min</span></td>
      <td style="text-align:right"><span class="${cls(r.tst_delta)}">${r.tst_delta >= 0 ? "+" : ""}${r.tst_delta.toFixed(2)} h</span></td>
      <td style="text-align:right"><span class="${cls(r.sws_delta)}">${r.sws_delta >= 0 ? "+" : ""}${r.sws_delta.toFixed(1)} pp</span></td>
      <td style="text-align:right"><span class="${cls(r.rem_delta)}">${r.rem_delta >= 0 ? "+" : ""}${r.rem_delta.toFixed(1)} pp</span></td>
    </tr>`;
  }
  html += "</tbody></table>";
  els.opt_table.innerHTML = html;
}

// ============================================================ persistence

const STORAGE_KEY = "sleeparchitect.profile.v1";
function saveProfile() {
  const profile = {
    msfsc: els.msfsc.value, age: els.age.value, weight_kg: els.weight_kg.value,
    sex: els.sex.value, cyp1a2: els.cyp1a2.value, smoker: els.smoker.value, hc: els.hc.value,
    wake_time_h: els.wake_time_h.value, bedtime_h: els.bedtime_h.value,
    prev_sleep_h: els.prev_sleep_h.value, last_meal_h: els.last_meal_h.value,
    meal_size: els.meal_size.value, light_lux: els.light_lux.value,
    screen_late: els.screen_late.checked,
    caffeine: readList(els.caffeine_list),
    alcohol: readList(els.alcohol_list),
    exercise: readList(els.exercise_list),
  };
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(profile)); }
  catch (_) {}
}
function loadProfile() {
  try {
    const p = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (!p) return false;
    for (const id of ["msfsc","age","weight_kg","sex","cyp1a2","smoker","hc",
                       "wake_time_h","bedtime_h","prev_sleep_h","last_meal_h",
                       "meal_size","light_lux"]) {
      if (p[id] != null) els[id].value = p[id];
    }
    if (typeof p.screen_late === "boolean") els.screen_late.checked = p.screen_late;
    while (els.caffeine_list.firstChild) els.caffeine_list.firstChild.remove();
    (p.caffeine || []).forEach(([t, mg]) => els.caffeine_list.appendChild(makeRow("caffeine", t, mg)));
    while (els.alcohol_list.firstChild) els.alcohol_list.firstChild.remove();
    (p.alcohol || []).forEach(([t, n]) => els.alcohol_list.appendChild(makeRow("alcohol", t, n)));
    while (els.exercise_list.firstChild) els.exercise_list.firstChild.remove();
    (p.exercise || []).forEach(([t, i, d]) => els.exercise_list.appendChild(makeRow("exercise", t, null, i, d)));
    return true;
  } catch (_) { return false; }
}

// ============================================================ bindings ==

els.recompute.addEventListener("click", computeAndRender);
els.saveProfile.addEventListener("click", saveProfile);
els.loadProfile.addEventListener("click", () => { if (loadProfile()) computeAndRender(); });
for (const id of ["msfsc","age","weight_kg","sex","cyp1a2","smoker","hc",
                  "wake_time_h","bedtime_h","prev_sleep_h","last_meal_h",
                  "meal_size","light_lux","screen_late"]) {
  els[id].addEventListener("input", computeAndRender);
  els[id].addEventListener("change", computeAndRender);
}
window.addEventListener("resize", () => {
  if (!LAST_FC) return;
  renderTonight(LAST_FC);
  if (document.querySelector(".tab-panel.active")?.dataset.panel === "clock")
    renderClock(LAST_FC);
  if (document.querySelector(".tab-panel.active")?.dataset.panel === "tomorrow")
    renderTomorrow(LAST_FC);
});

// Default seed schedule
els.caffeine_list.appendChild(makeRow("caffeine", 7.0, 95));
els.caffeine_list.appendChild(makeRow("caffeine", 13.0, 95));
els.exercise_list.appendChild(makeRow("exercise", 18.0, null, "moderate", 30));

if (!loadProfile()) computeAndRender();
else computeAndRender();
