# AskSia × Apple Notes — growth-hack MVP (internal)

**What:** a second exit next to "Download PDF" on every Library bible — a structured cheat-note that lands in the student's own Apple Notes (facts · formulas · bilingual key terms · exam traps · the card image · the visual Sia drew).

**Flow:** Library page → 📝 *Add to Apple Notes* → (desktop) QR → iPhone Safari note page (no login) → *Add to Apple Notes* → iOS Share Sheet → **Notes**.
Fallbacks on the note page: *Copy as rich text* (paste into Notes keeps headings/tables) · *Share text only* · *Save image*.

**Build:** `python3 build.py` (needs `qrcode[pil]` + Playwright Chromium) → `docs/`. Content lives in `content.py`; every fact is lifted from the shipped bibles (BUSS1020 · ECB1101 · SAT).

**Metric to test:** Notes clicks ÷ PDF clicks on the same page (hypothesis ≥ 2×). The MVP counts per browser in `localStorage`; production needs one event endpoint.

Owner: Kai (growth) · 2026-08-30
