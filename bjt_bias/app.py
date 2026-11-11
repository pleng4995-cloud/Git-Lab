"""Flask web interface for the BJT common-emitter DC bias analysis."""

from flask import Flask, render_template, request

from bjt_bias.bias import OPERATING_POINT_FIELDS, analyze_bias

FIELDS = (
    ("vcc", "VCC", "V", "12"),
    ("r1", "R1", "Ω", "47k"),
    ("r2", "R2", "Ω", "10k"),
    ("rc", "RC", "Ω", "2.2k"),
    ("re", "RE", "Ω", "1k"),
    ("beta", "beta", "", "150"),
    ("vbe", "VBE", "V", "0.7"),
)

RESISTANCE_FIELDS = ("r1", "r2", "rc", "re")

MULTIPLIERS = {"k": 1e3, "K": 1e3, "M": 1e6}


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


def _form_fields(values):
    return [
        {
            "name": name,
            "label": label,
            "unit": unit,
            "value": values.get(name, default),
        }
        for name, label, unit, default in FIELDS
    ]


def _read_form(form):
    values = {}
    parsed = {}
    errors = []
    for name, label, _unit, _default in FIELDS:
        raw = form.get(name, "")
        values[name] = raw
        try:
            if name in RESISTANCE_FIELDS:
                parsed[name] = parse_resistance(raw, label)
            else:
                parsed[name] = parse_number(raw, label)
        except ValueError as error:
            errors.append(str(error))
    return values, parsed, errors


def create_app():
    """Build the Flask application."""
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "GET":
            values = {name: default for name, _l, _u, default in FIELDS}
            return render_template(
                "index.html",
                fields=_form_fields(values),
                errors=[],
                result=None,
                op_fields=OPERATING_POINT_FIELDS,
                fmt=format_value,
            )

        values, parsed, errors = _read_form(request.form)
        result = None
        if not errors:
            try:
                result = analyze_bias(**parsed)
            except ValueError as error:
                errors.append(str(error))
        return render_template(
            "index.html",
            fields=_form_fields(values),
            errors=errors,
            result=result,
            op_fields=OPERATING_POINT_FIELDS,
            fmt=format_value,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
