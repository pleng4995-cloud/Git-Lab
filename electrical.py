import json
import math


def _finite_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number.")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} must be finite.") from error
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite.")
    return number


def _positive_number(value, name):
    number = _finite_number(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be a finite number greater than zero.")
    return number


def analyze_dc(voltage_v, resistance_ohm):
    """Analyze a DC circuit containing one resistor."""
    voltage_v = _finite_number(voltage_v, "voltage_v")
    resistance = _positive_number(resistance_ohm, "resistance_ohm")
    current = voltage_v / resistance
    return {"current_a": current, "power_w": voltage_v * current}


def analyze_circuit(voltage_v, circuit):
    """Analyze a series/parallel circuit tree and return total and per-resistor values.

    A resistor is {"name": "R1", "resistance_ohm": 10}.
    A network is {"series": [ ... ]} or {"parallel": [ ... ]}.
    """
    voltage_v = _finite_number(voltage_v, "voltage_v")

    used_names = set()
    next_name = 1

    def equivalent_resistance(node):
        nonlocal next_name

        if not isinstance(node, dict):
            raise ValueError("Each circuit component must be an object.")

        if "resistance_ohm" in node:
            resistance = _positive_number(
                node["resistance_ohm"], "resistance_ohm"
            )
            name = node.get("name")
            if name is None:
                while f"R{next_name}" in used_names:
                    next_name += 1
                name = f"R{next_name}"
                next_name += 1
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Resistor names must be non-empty strings.")
            if name in used_names:
                raise ValueError(f"Duplicate resistor name: {name}")
            used_names.add(name)
            return resistance, ("resistor", name, resistance)

        network_keys = [key for key in ("series", "parallel") if key in node]
        if len(network_keys) != 1:
            raise ValueError(
                "A network must contain exactly one 'series' or 'parallel' key."
            )

        kind = network_keys[0]
        children = node[kind]
        if not isinstance(children, list) or not children:
            raise ValueError(f"The '{kind}' network must contain components.")

        parsed_children = [
            equivalent_resistance(child) for child in children
        ]
        resistances = [item[0] for item in parsed_children]
        if kind == "series":
            equivalent = sum(resistances)
        else:
            equivalent = 1 / sum(1 / resistance for resistance in resistances)
        return equivalent, (kind, parsed_children)

    total_resistance, parsed_circuit = equivalent_resistance(circuit)
    total_current = voltage_v / total_resistance
    resistors = {}

    def calculate(node, applied_voltage, series_current=None):
        kind = node[0]
        if kind == "resistor":
            _, name, resistance = node
            current = (
                series_current
                if series_current is not None
                else applied_voltage / resistance
            )
            resistors[name] = {
                "resistance_ohm": resistance,
                "voltage_v": applied_voltage,
                "current_a": current,
                "power_w": applied_voltage * current,
            }
            return

        _, children = node
        if kind == "series":
            current = applied_voltage / sum(item[0] for item in children)
            for child_resistance, child in children:
                calculate(child, current * child_resistance, current)
        else:
            for _, child in children:
                calculate(child, applied_voltage)

    calculate(parsed_circuit, voltage_v)
    return {
        "equivalent_resistance_ohm": total_resistance,
        "total_current_a": total_current,
        "total_power_w": voltage_v * total_current,
        "resistors": resistors,
    }


def _read_circuit():
    mode = input("Circuit type (series, parallel, mixed): ").strip().lower()
    if mode in ("series", "parallel"):
        values = input("Resistances in ohms (comma-separated): ")
        try:
            resistances = [float(value.strip()) for value in values.split(",")]
        except ValueError as error:
            raise ValueError("Enter resistances as comma-separated numbers.") from error
        if not resistances:
            raise ValueError("Enter at least one resistance.")
        return {
            mode: [
                {"name": f"R{index}", "resistance_ohm": resistance}
                for index, resistance in enumerate(resistances, start=1)
            ]
        }
    if mode == "mixed":
        print(
            'Enter a JSON circuit, e.g. {"series": [{"name": "R1", '
            '"resistance_ohm": 10}, {"parallel": [{"name": "R2", '
            '"resistance_ohm": 20}, {"name": "R3", "resistance_ohm": 30}]}]}'
        )
        try:
            return json.loads(input("Circuit JSON: "))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid circuit JSON: {error.msg}") from error
    raise ValueError("Choose series, parallel, or mixed.")


if __name__ == "__main__":
    try:
        voltage = float(input("Supply voltage in volts: "))
        result = analyze_circuit(voltage, _read_circuit())
        print(json.dumps(result, indent=2))
    except (ValueError, EOFError) as error:
        raise SystemExit(f"Error: {error}") from error
