"""Flask web interface for the BJT common-emitter DC bias analysis."""

import math

from flask import Flask, render_template, request

from bjt_bias import plots as plot_module
from bjt_bias import spice_engine
from bjt_bias.bias import (
    OPERATING_POINT_FIELDS,
    VCE_SAT_V,
    analyze_bias,
    analyze_emitter_bias,
    analyze_fixed_bias,
)

RESISTOR_UNITS = (("Ω", "ohm"), ("kΩ", "kohm"), ("MΩ", "mohm"))
VOLT_UNITS = (("V", "v"),)
GAIN_UNITS = (("–", "none"),)

MODE_LABELS = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}
DEFAULT_MODE = "divider"

# (value, label). The button itself submits ``analysis`` so no JavaScript is
# needed, and a POST without the field stays analytical (Lab 03 behaviour).
ANALYSES = (
    ("analytical", "Analytical DC only"),
    ("dc", "Run SPICE DC"),
    ("ac", "Run AC sweep"),
    ("tran", "Run Transient"),
)

SOURCE_SPECS = (
    {
        "name": "amplitude_mv",
        "label": "Amplitude (mV peak)",
        "default": "10",
        "hint": "Transient only",
        "min": 0.001,
        "max": 1000.0,
        "analyses": ("tran",),
    },
    {
        "name": "frequency_hz",
        "label": "Frequency (Hz)",
        "default": "1000",
        "hint": "Transient only",
        "min": 1.0,
        "max": 1e6,
        "analyses": ("tran",),
    },
    {
        "name": "ac_start_hz",
        "label": "AC start (Hz)",
        "default": "10",
        "hint": "AC sweep only",
        "min": 0.1,
        "max": 1e9,
        "analyses": ("ac",),
    },
    {
        "name": "ac_stop_hz",
        "label": "AC stop (Hz)",
        "default": "1000000",
        "hint": "AC sweep only",
        "min": 0.1,
        "max": 1e9,
        "analyses": ("ac",),
    },
    {
        "name": "ac_points_dec",
        "label": "AC points/decade",
        "default": "20",
        "hint": "AC sweep only",
        "min": 5.0,
        "max": 200.0,
        "analyses": ("ac",),
    },
)
DEFAULT_SOURCE_VALUES = {spec["name"]: spec["default"] for spec in SOURCE_SPECS}

FIELDS = (
    {
        "name": "vcc",
        "label": "VCC",
        "display": "V<sub>CC</sub>",
        "description": "Supply Voltage",
        "units": VOLT_UNITS,
        "default_value": "12",
        "default_unit": "v",
        "modes": ("divider", "fixed", "emitter"),
    },
    {
        "name": "r1",
        "label": "R1",
        "display": "R<sub>1</sub>",
        "description": "Upper Divider",
        "units": RESISTOR_UNITS,
        "default_value": "100",
        "default_unit": "kohm",
        "modes": ("divider",),
    },
    {
        "name": "r2",
        "label": "R2",
        "display": "R<sub>2</sub>",
        "description": "Lower Divider",
        "units": RESISTOR_UNITS,
        "default_value": "22",
        "default_unit": "kohm",
        "modes": ("divider",),
    },
    {
        "name": "rb",
        "label": "RB",
        "display": "R<sub>B</sub>",
        "description": "Base Resistor",
        "units": RESISTOR_UNITS,
        "default_value": "1",
        "default_unit": "mohm",
        "modes": ("fixed", "emitter"),
    },
    {
        "name": "rc",
        "label": "RC",
        "display": "R<sub>C</sub>",
        "description": "Collector Resistor",
        "units": RESISTOR_UNITS,
        "default_value": "2.2",
        "default_unit": "kohm",
        "modes": ("divider", "fixed", "emitter"),
    },
    {
        "name": "re",
        "label": "RE",
        "display": "R<sub>E</sub>",
        "description": "Emitter Resistor",
        "units": RESISTOR_UNITS,
        "default_value": "1",
        "default_unit": "kohm",
        "modes": ("divider", "emitter"),
    },
    {
        "name": "beta",
        "label": "beta",
        "display": "β",
        "description": "Current Gain",
        "units": GAIN_UNITS,
        "default_value": "100",
        "default_unit": "none",
        "modes": ("divider", "fixed", "emitter"),
    },
    {
        "name": "vbe",
        "label": "VBE",
        "display": "V<sub>BE</sub>",
        "description": "Base–Emitter Voltage",
        "units": VOLT_UNITS,
        "default_value": "0.7",
        "default_unit": "v",
        "modes": ("divider", "fixed", "emitter"),
    },
)

MODES = {
    mode: {
        "label": label,
        "fields": tuple(
            spec["name"] for spec in FIELDS if mode in spec["modes"]
        ),
    }
    for mode, label in MODE_LABELS.items()
}

RESISTANCE_FIELDS = ("r1", "r2", "rb", "rc", "re")

MULTIPLIERS = {"k": 1e3, "K": 1e3, "M": 1e6}

UNIT_MULTIPLIERS = {
    "": 1.0,
    "ohm": 1.0,
    "kohm": 1e3,
    "mohm": 1e6,
    "v": 1.0,
    "none": 1.0,
}


def unit_multiplier(unit):
    """Return the multiplier for a unit key; unknown or absent keys mean base units."""
    return UNIT_MULTIPLIERS.get((unit or "").strip().lower(), 1.0)


def parse_resistance(text, label):
    """Parse a resistance in ohms, allowing a ``k`` or ``M`` suffix."""
    cleaned = (text or "").strip()
    multiplier = 1.0
    if cleaned and cleaned[-1] in MULTIPLIERS:
        multiplier = MULTIPLIERS[cleaned[-1]]
        cleaned = cleaned[:-1].strip()
    try:
        return float(cleaned) * multiplier
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(
            f"{label} must be a number in ohms (e.g. 47000, 47k)."
        ) from error


def parse_number(text, label):
    """Parse a plain decimal number, with a friendly error message."""
    try:
        return float((text or "").strip())
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{label} must be a number.") from error


def format_value(value, scale):
    """Render a raw SI value in its display unit with three decimals."""
    return f"{value * scale:.3f}"


RESULT_ORDER = ("v_b_v", "v_e_v", "v_c_v", "v_ce_v", "i_b_a", "i_c_a", "i_e_a")


def ordered_operating_point_fields():
    """Return the operating-point fields in the lab's display order."""
    by_key = {field[0]: field for field in OPERATING_POINT_FIELDS}
    return tuple(by_key[key] for key in RESULT_ORDER)


def trim_number(number):
    """Format with up to three decimals and no trailing zeros."""
    text = f"{number:.3f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def format_ohms(value):
    """Format a resistance in ohms, auto-scaling to kΩ or MΩ."""
    if abs(value) >= 1e6:
        return f"{trim_number(value / 1e6)} MΩ"
    if abs(value) >= 1e3:
        return f"{trim_number(value / 1e3)} kΩ"
    return f"{trim_number(value)} Ω"


def format_volts(value):
    """Format a voltage in volts."""
    return f"{trim_number(value)} V"


def format_symbol(symbol):
    """Render ``V_CE`` as ``V<sub>CE</sub>``."""
    head, _, tail = symbol.partition("_")
    return f"{head}<sub>{tail}</sub>"


def _default_value(spec):
    if spec["name"] in RESISTANCE_FIELDS:
        value = parse_resistance(spec["default_value"], spec["label"])
    else:
        value = parse_number(spec["default_value"], spec["label"])
    return value * unit_multiplier(spec["default_unit"])


DEFAULT_INPUTS = {spec["name"]: _default_value(spec) for spec in FIELDS}


def circuit_labels(parsed, mode=DEFAULT_MODE):
    """Labels for the schematic, from the submitted values (defaults fill gaps)."""
    inputs = {**DEFAULT_INPUTS, **parsed}
    labels = {
        "vcc": format_volts(inputs["vcc"]),
        "rc": format_ohms(inputs["rc"]),
        "beta": trim_number(inputs["beta"]),
    }
    if mode == "divider":
        labels["r1"] = format_ohms(inputs["r1"])
        labels["r2"] = format_ohms(inputs["r2"])
    else:
        labels["rb"] = format_ohms(inputs["rb"])
    if mode in ("divider", "emitter"):
        labels["re"] = format_ohms(inputs["re"])
    return labels


def _mode_fields(mode):
    """Return the field specs used by ``mode``, in form order."""
    return [spec for spec in FIELDS if mode in spec["modes"]]


def _resolve_mode(raw):
    """Return ``(mode, error)`` for a raw mode value from the request."""
    value = (raw or "").strip().lower()
    if not value:
        return DEFAULT_MODE, None
    if value in MODES:
        return value, None
    return DEFAULT_MODE, f"Unknown bias mode: '{raw}'."


def _form_fields(values, units, mode=DEFAULT_MODE):
    return [
        {
            "name": spec["name"],
            "label": spec["label"],
            "display": spec["display"],
            "description": spec["description"],
            "units": spec["units"],
            "selected_unit": units.get(spec["name"], ""),
            "value": values.get(spec["name"], spec["default_value"]),
        }
        for spec in _mode_fields(mode)
    ]


def _read_form(form, mode=DEFAULT_MODE):
    values = {}
    units = {}
    parsed = {}
    errors = []
    for spec in _mode_fields(mode):
        name = spec["name"]
        label = spec["label"]
        raw = form.get(name, "")
        values[name] = raw
        units[name] = form.get(f"{name}_unit", "")
        multiplier = unit_multiplier(form.get(f"{name}_unit", ""))
        if (
            name in RESISTANCE_FIELDS
            and multiplier != 1.0
            and (raw or "").strip()
            and (raw or "").strip()[-1] in MULTIPLIERS
        ):
            errors.append(
                f"{label}: use either a unit selector or a k/M suffix, not both."
            )
            continue
        try:
            if name in RESISTANCE_FIELDS:
                parsed[name] = parse_resistance(raw, label) * multiplier
            else:
                parsed[name] = parse_number(raw, label) * multiplier
        except ValueError as error:
            errors.append(str(error))
    return values, units, parsed, errors


def _bounded_source_number(form, spec):
    raw = form.get(spec["name"], "")
    label = spec["label"]
    value = parse_number(raw, label)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number.")
    if value < spec["min"] or value > spec["max"]:
        raise ValueError(
            f"{label} must be between {spec['min']:g} and {spec['max']:g}."
        )
    return value


def _resolve_analysis(raw):
    """Return ``(analysis, error)``; a missing value means analytical."""
    value = (raw or "").strip().lower()
    if not value:
        return "analytical", None
    if value in {key for key, _label in ANALYSES}:
        return value, None
    return "analytical", f"Unknown analysis: '{raw}'."


def _read_source(form, analysis):
    """Validate only the source/sweep fields used by ``analysis``."""
    if analysis not in ("ac", "tran"):
        return {}, {}, []

    specs = [spec for spec in SOURCE_SPECS if analysis in spec["analyses"]]
    values = {}
    parsed = {}
    errors = []
    for spec in specs:
        values[spec["name"]] = form.get(spec["name"], "")
        try:
            parsed[spec["name"]] = _bounded_source_number(form, spec)
        except ValueError as error:
            errors.append(str(error))

    if analysis == "tran":
        frequency = parsed.get("frequency_hz")
        if frequency and frequency > 0:
            stop_s = 5.0 / frequency
            if stop_s > 2.0:
                errors.append(
                    f"At {frequency:g} Hz, 5 cycles would take {stop_s:.3f} s; "
                    "increase frequency so 5/f is at most 2 s."
                )
        if not errors:
            parsed = {
                "amplitude_v": parsed["amplitude_mv"] / 1000.0,
                "frequency_hz": parsed["frequency_hz"],
            }
    else:
        start = parsed.get("ac_start_hz")
        stop = parsed.get("ac_stop_hz")
        if start and stop and stop <= start:
            errors.append(
                f"ac_stop_hz must be greater than ac_start_hz ({start:g} Hz)."
            )

    return values, parsed, errors


def _spice_circuit(parsed, source):
    """Build the SPICE circuit from validated bias values and source settings."""
    circuit = dict(spice_engine.CIRCUIT_DEFAULTS)
    for key in ("vcc", "r1", "r2", "rc", "re"):
        if key in parsed:
            circuit[key] = float(parsed[key])
    for key in (
        "amplitude_v",
        "frequency_hz",
        "ac_start_hz",
        "ac_stop_hz",
        "ac_points_dec",
    ):
        if source and key in source:
            circuit[key] = float(source[key])
    return circuit


def engine_status():
    """Return the cached ngspice discovery result for the status bar."""
    return spice_engine.locate_engine()


def run_spice_simulation(circuit, analysis):
    """Run one SPICE analysis and attach plots only for a fully valid result."""
    result = spice_engine.run_analysis(circuit, analysis)
    drawings = {}
    if result["status"] == "ok":
        data = result["data"]
        try:
            if analysis == "ac":
                drawings["bode"] = plot_module.bode_svg(
                    data["freq_hz"], data["gain_db"], data["phase_deg"],
                    run_id=result["run_id"],
                )
            elif analysis == "tran":
                drawings["transient"] = plot_module.transient_svg(
                    data["time_s"], data["vin_v"], data["vout_v"],
                    run_id=result["run_id"],
                )
        except (KeyError, ValueError) as error:
            result["status"] = "parse_error"
            result["data"] = {}
            result["stderr_tail"] = (
                result["stderr_tail"] + f"\nplot render failed: {error}"
            ).strip()
    result["plots"] = drawings
    return result


def _analyze(mode, parsed):
    """Dispatch to the model selected by ``mode``."""
    if mode == "divider":
        return analyze_bias(**parsed)
    if mode == "fixed":
        return analyze_fixed_bias(**parsed)
    if mode == "emitter":
        return analyze_emitter_bias(**parsed)
    raise ValueError(f"Unknown bias mode: '{mode}'.")


def page_context(
    fields,
    errors,
    result,
    parsed,
    mode=DEFAULT_MODE,
    *,
    analysis="analytical",
    analysis_options=ANALYSES,
    source_fields=SOURCE_SPECS,
    source_values=None,
    engine=None,
    spice=None,
    spice_plots=None,
):
    """Build the template context shared by the GET and POST responses."""
    return {
        "fields": fields,
        "errors": errors,
        "result": result,
        "op_fields": OPERATING_POINT_FIELDS,
        "result_fields": ordered_operating_point_fields(),
        "circuit": circuit_labels(parsed, mode),
        "vce_sat": VCE_SAT_V,
        "symbol_html": format_symbol,
        "fmt": format_value,
        "mode": mode,
        "mode_label": MODES[mode]["label"],
        "mode_options": [
            (key, spec["label"]) for key, spec in MODES.items()
        ],
        "analysis": analysis,
        "analysis_options": analysis_options,
        "source_fields": source_fields,
        "source_values": source_values or dict(DEFAULT_SOURCE_VALUES),
        "engine": engine,
        "spice": spice,
        "spice_plots": spice_plots or {},
    }


def create_app():
    """Build the Flask application."""
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "GET":
            mode, mode_error = _resolve_mode(request.args.get("mode"))
            analysis, analysis_error = _resolve_analysis(request.args.get("analysis"))
            values = {spec["name"]: spec["default_value"] for spec in FIELDS}
            units = {spec["name"]: spec["default_unit"] for spec in FIELDS}
            errors = [error for error in (mode_error, analysis_error) if error]
            return render_template(
                "index.html",
                **page_context(
                    _form_fields(values, units, mode),
                    errors,
                    None,
                    DEFAULT_INPUTS,
                    mode,
                    analysis=analysis,
                    engine=engine_status(),
                ),
            )

        mode, mode_error = _resolve_mode(request.form.get("mode"))
        analysis, analysis_error = _resolve_analysis(request.form.get("analysis"))
        source_values, source, source_errors = _read_source(request.form, analysis)
        errors = [error for error in (mode_error, analysis_error) if error]
        errors.extend(source_errors)

        if mode_error:
            values = {
                spec["name"]: request.form.get(spec["name"], "")
                for spec in FIELDS
            }
            units = {
                spec["name"]: request.form.get(f"{spec['name']}_unit", "")
                for spec in FIELDS
            }
            parsed = {}
        else:
            values, units, parsed, form_errors = _read_form(request.form, mode)
            errors.extend(form_errors)

        if analysis != "analytical" and mode != "divider":
            errors.append(
                "SPICE analysis is available for the Voltage Divider reference only."
            )

        result = None
        spice = None
        spice_plots = {}
        if not errors:
            try:
                result = _analyze(mode, parsed)
            except ValueError as error:
                errors.append(str(error))
            if analysis != "analytical" and not errors:
                spice = run_spice_simulation(
                    _spice_circuit(parsed, source), analysis
                )
                spice_plots = spice.get("plots", {}) or {}

        return render_template(
            "index.html",
            **page_context(
                _form_fields(values, units, mode),
                errors,
                result,
                parsed,
                mode,
                analysis=analysis,
                source_values=source_values,
                engine=engine_status(),
                spice=spice,
                spice_plots=spice_plots,
            ),
        )

    return app


app = create_app()


if __name__ == "__main__":
    # The reloader spawns a second process; disabling it keeps one process so
    # stopping the server always releases port 5000.
    app.run(debug=True, use_reloader=False)
