# Changelog

All notable changes to DBNT will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.3] - 2026-07-02
### Fixed
- `lastrowid` null-safety in `LearningStore.add()` — returns `-1` instead of `None` on insert failure
### Changed
- Classifier promoted from `Development Status :: 3 - Alpha` to `4 - Beta`

## [0.5.2] - 2026-03-20
### Added
- `--limit` flag on `dbnt patterns` and `dbnt promote` (default 200) to cap SequenceMatcher comparisons
### Fixed
- O(n²) hang in `dbnt patterns` / `dbnt promote` with 2500+ entries — SequenceMatcher over full store now capped
- `_load_state` migrates legacy score events with `delta` key to current `points` schema at load time
- KeyError: 'points' when loading legacy score events with `delta` key schema
- Learning contamination: filter added to reject system-reminder and tool-suggestion text

## [0.5.1] - 2026-03-17
### Added
- Session-level dedup in LearningStore.add()
- pyrightconfig.json for Pyright static analysis
### Fixed
- Pyright diagnostic on __exit__ signature

## [0.5.0] - 2026-03-15

### Added
- FSRS-based spaced repetition decay for learning rules
- Claude Code plugin packaging (`.claude-plugin/`)
- CI workflow (GitHub Actions, Python 3.10-3.13 matrix)
- `dbnt rules` and `dbnt show` CLI commands
- DBGT (Do Better Good Time) success protocol
- Adapter plugin system (`dbnt.adapters` entry points)
- llms.txt for agent discovery
- AGENTS.md for AI developer onboarding
- 84 tests (up from 17)

### Changed
- README rewritten for intermediate autonomous developers
- pyproject.toml expanded (12 keywords, classifiers, URLs)
- Architecture: BYOK model, Level 1-4 adoption path

### Fixed
- Signal detection accuracy improvements
- Rule encoding weight calibration

## [0.2.0] - 2026-01-06

### Added
- Initial DBNT/DBGT protocol implementation
- Signal detection (positive/negative/neutral)
- Weighted encoding (success 1.5x, failure 1.0x)
- Dissonance calculator
- Claude Code adapter
- Generic file-based adapter
- CLI with detect, success, failure, dissonance commands

## [0.1.0] - 2026-01-06

### Added
- Core signal detection module
- Rule encoding (success/failure categories)
- Dissonance monitoring with 60/40 target
- Claude Code hook integration
- CLI interface (`dbnt` command)
- 17 passing tests

### Philosophy
- Success signals weight 1.5x over failure (inverted from typical)
- Target: 60% success rules, 40% failure rules
- No anger required - mild feedback works
- The Ralph Wiggum Problem: knowing 100 ways to fail doesn't teach you how to succeed
