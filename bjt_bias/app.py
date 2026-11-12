"""Flask web interface for the BJT common-emitter DC bias analysis."""

from flask import Flask, render_template, request

from bjt_bias.bias import OPERATING_POINT_FIELDS, VCE_SAT_V, analyze_bias

RESISTOR_UNITS = (("Ω", "ohm"), ("kΩ", "kohm"), ("MΩ", "mohm"))
VOLT_UNITS = (("V", "v"),)
GAIN_UNITS = (("–", "none"),)

FIELDS = (
    {
        "name": "vcc",
        "label": "VCC",
        "display": "V<sub>CC</sub>",
        "description": "Supply Voltage",
        "units": VOLT_UNITS,
        "default_value": "12",
        "default_unit": "v",
    },
    {
        "name": "r1",
        "label": "R1",
        "display": "R<sub>1</sub>",
        "description": "Upper Divider",
        "units": RESISTOR_UNITS,
        "default_value": "100",
        "default_unit": "kohm",
    },
    {
        "name": "r2",
        "label": "R2",
        "display": "R<sub>2</sub>",
        "description": "Lower Divider",
        "units": RESISTOR_UNITS,
        "default_value": "22",
        "default_unit": "kohm",
    },
    {
        "name": "rc",
        "label": "RC",
        "display": "R<sub>C</sub>",
        "description": "Collector Resistor",
        "units": RESISTOR_UNITS,
        "default_value": "2.2",
        "default_unit": "kohm",
    },
    {
        "name": "re",
        "label": "RE",
        "display": "R<sub>E</sub>",
        "description": "Emitter Resistor",
        "units": RESISTOR_UNITS,
        "default_value": "1",
        "default_unit": "kohm",
    },
    {
        "name": "beta",
        "label": "beta",
        "display": "β",
        "description": "Current Gain",
        "units": GAIN_UNITS,
        "default_value": "100",
        "default_unit": "none",
    },
    {
        "name": "vbe",
        "label": "VBE",
        "display": "V<sub>BE</sub>",
        "description": "Base–Emitter Voltage",
        "units": VOLT_UNITS,
        "default_value": "0.7",
        "default_unit": "v",
    },
)

RESISTANCE_FIELDS = ("r1", "r2", "rc", "re")

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


def circuit_labels(parsed):
    """Labels for the schematic, from the submitted values (defaults fill gaps)."""
    inputs = {**DEFAULT_INPUTS, **parsed}
    return {
        "vcc": format_volts(inputs["vcc"]),
        "r1": format_ohms(inputs["r1"]),
        "r2": format_ohms(inputs["r2"]),
        "rc": format_ohms(inputs["rc"]),
        "re": format_ohms(inputs["re"]),
        "beta": trim_number(inputs["beta"]),
    }


def _form_fields(values, units):
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
        for spec in FIELDS
    ]


def _read_form(form):
    values = {}
    units = {}
    parsed = {}
    errors = []
    for spec in FIELDS:
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


def page_context(fields, errors, result, parsed):
    """Build the template context shared by the GET and POST responses."""
    return {
        "fields": fields,
        "errors": errors,
        "result": result,
        "op_fields": OPERATING_POINT_FIELDS,
        "result_fields": ordered_operating_point_fields(),
        "circuit": circuit_labels(parsed),
        "vce_sat": VCE_SAT_V,
        "symbol_html": format_symbol,
        "fmt": format_value,
    }


def create_app():
    """Build the Flask application."""
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "GET":
            values = {spec["name"]: spec["default_value"] for spec in FIELDS}
            units = {spec["name"]: spec["default_unit"] for spec in FIELDS}
            return render_template(
                "index.html",
                **page_context(_form_fields(values, units), [], None, DEFAULT_INPUTS),
            )

        values, units, parsed, errors = _read_form(request.form)
        result = None
        if not errors:
            try:
                result = analyze_bias(**parsed)
            except ValueError as error:
                errors.append(str(error))
        return render_template(
            "index.html",
            **page_context(_form_fields(values, units), errors, result, parsed),
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
