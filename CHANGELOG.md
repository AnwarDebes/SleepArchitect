# Changelog

All notable changes to SleepArchitect are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-06-12

First public release.

### Added

- Predictive sleep model composing Process S (Borbely 1982 / Daan 1984),
  Process C (Skeldon 2017), light PRC (Khalsa 2003) with melatonin
  suppression (Brainard 2001), caffeine PK with SWS suppression
  (Drake 2013), alcohol PK with REM suppression (Ebrahim 2013),
  exercise (Stutz 2019), meal timing (Crispim 2011, Iao 2021), and
  chronotype (MCTQ MSFsc, Roenneberg 2003).
- Single-night forecast: sleep score, sleep-onset latency, total sleep
  time, SWS/REM percentages, and a synthesized hypnogram.
- SAFTE alertness curve for the next day (Hursh / Mallis 2004) with
  best-focus window.
- Ranked interventions for tonight's schedule.
- Validation against 11 published quantitative checks.
- Static browser frontend with a 24-hour clock face: 65 KB raw,
  18.7 KB gzipped, no build step, no network calls, profile stored in
  `localStorage` only.
- Validation, chronotype sweep, and intervention experiments with JSON
  outputs.
- LaTeX paper with figures.
- 29 unit tests.

[0.1.0]: https://github.com/AnwarDebes/SleepArchitect/releases/tag/v0.1.0
