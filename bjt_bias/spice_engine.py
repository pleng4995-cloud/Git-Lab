"""Adapter for running ngspice on the CE voltage-divider reference circuit."""

from pathlib import Path

MODEL_NAME = "2N3904"
MODEL_PATH = Path(__file__).with_name("spice_models") / "2n3904.lib"
