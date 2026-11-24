# BJT model provenance — `2n3904.lib`

## Why this model

ENG29 2121 Lab 04 requires a BJT model for the ngspice CE voltage-divider
reference circuit. No Instructor Starter Kit was supplied in this environment,
so this repository ships the widely published **ON Semiconductor / Motorola
2N3904** SPICE model card instead. It is the same card distributed in the
PSpice Evaluation library and reproduced in university SPICE decks.

The model is **not** fitted to the analytical Lab 03 results. It is copied
verbatim; the analytical engine (`bjt_bias/bias.py`) keeps its own fixed
`beta`/`VBE` assumptions and is labelled separately in the UI. Differences
between analytical and SPICE numbers are expected and are reported as a delta,
not hidden.

## Verification sources

Checked on 2026-11-24:

- <https://ece.mcgill.ca/~grober4/SPICE/SPICE_Decks/1st_Edition/chapter8/fig8_24.cir>
  — `Q2N3904` card with `Is=6.734f`, `Vaf=74.03`, `Bf=416.4`.
- <https://home.uncg.edu/~ehhellen/spice_stuff.html> — same card under the name
  `2N3904`.
- <https://github.com/fakuivan/ltspice-models/blob/master/2N3904.lib> — same
  parameter set, labelled as originating from the PSpice Evaluation library.

The local file uses upper-case parameter names (`IS`, `BF`, `VAF`, …); SPICE
model parameter names are case-insensitive. No value was changed.

## Integrity

Record the SHA256 of this file in `docs/validation.md` for each validated run.
`spice_engine.run_analysis()` also stores the SHA256 in every run's `meta.json`.

## If an Instructor Starter Kit is supplied later

1. Put the kit's model card in this directory under a new name (for example
   `starter-kit.lib`) — do not overwrite this file blindly.
2. Update `MODEL_NAME` and `MODEL_PATH` in `bjt_bias/spice_engine.py`, and the
   `.model <name> NPN` declaration used by `build_netlist()`.
3. Update the netlist assertions in `test_spice_engine.py`, re-run
   `python -m unittest discover`, then re-run the B1–B8 browser acceptance and
   replace every screenshot and result in `docs/evidence/lab4/`.
4. Update the model name, provenance and SHA256 in `README.md` and
   `docs/validation.md`. Do not carry old evidence forward as new results.
