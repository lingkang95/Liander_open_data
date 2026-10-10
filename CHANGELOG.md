# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-10

### Added

- `build_database()` / `liander-open-data build`: build a single SQLite file
  from the Liander profile CSVs and the SBI dictionary.
- `ProfileDatabase` query API: `get_profile`, `get_profiles`, `lookup`,
  `recommended_profile`, `dictionary`, `list_profiles` and `query`.
- Parser for the Liander *Overzicht met per SBI-code een aanbevolen profiel*
  workbook, with a cleaned copy bundled in the package.
- Command line interface with `build`, `info`, `list`, `lookup`, `search`,
  `export` and `dictionary` commands.
