"""Pure SVG renderers for ngspice arrays.

No dependency beyond the standard library. Every coordinate comes from the
arrays passed in; the only optional input is a run id used in the caption.
"""

from __future__ import annotations

import html
import math

LEFT = 64
RIGHT_MARGIN = 24
TOP = 24
BOTTOM_MARGIN = 44
MAX_POINTS = 1200


def _validate(*series: object) -> int:
    lengths = [len(series_item) for series_item in series]  # type: ignore[arg-type]
    if not lengths or any(length == 0 for length in lengths):
        raise ValueError("plot data must not be empty")
    if len(set(lengths)) != 1:
        raise ValueError(f"plot arrays must have equal lengths, got {lengths}")
    return lengths[0]


def _decimate(xs: list[float], ys_list: list[list[float]]) -> tuple[list[float], list[list[float]]]:
    """Keep per-bucket min/max points so the shape survives downsampling."""
    count = len(xs)
    if count <= MAX_POINTS:
        return xs, ys_list
    buckets = max(1, MAX_POINTS // 4)
    size = math.ceil(count / buckets)
    indices: list[int] = []
    for start in range(0, count, size):
        end = min(start + size, count)
        candidates: set[int] = set()
        for ys in ys_list:
            segment = ys[start:end]
            candidates.add(start + min(range(len(segment)), key=segment.__getitem__))
            candidates.add(start + max(range(len(segment)), key=segment.__getitem__))
        indices.extend(sorted(candidates))
    return [xs[index] for index in indices], [[ys[index] for index in indices] for ys in ys_list]


def _frame(width: int, height: int, desc: str, label: str) -> list[str]:
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{html.escape(label, quote=True)}">',
        f"<desc>{html.escape(desc)}</desc>",
    ]


def _path(
    xs: list[float],
    ys: list[float],
    project_x,
    project_y,
    colour: str,
    *,
    dashed: bool = False,
) -> str:
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    points = " ".join(
        f"{'M' if index == 0 else 'L'}{project_x(x):.2f},{project_y(y):.2f}"
        for index, (x, y) in enumerate(zip(xs, ys))
    )
    return f'<path d="{points}" fill="none" stroke="{colour}" stroke-width="1.8"{dash}/>'


def _line(x1: float, y1: float, x2: float, y2: float, colour: str = "#d8dee9") -> str:
    return (
        f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
        f'stroke="{colour}" stroke-width="1"/>'
    )


def _text(x: float, y: float, value: str, *, anchor: str = "start", size: int = 11) -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" '
        f'font-size="{size}" fill="#4b5563">{html.escape(value)}</text>'
    )


def _y_title(x: float, y: float, value: str) -> str:
    """Vertical y-axis title, kept clear of the right-aligned tick labels."""
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="middle" '
        f'font-size="11" fill="#4b5563" '
        f'transform="rotate(-90 {x:.2f} {y:.2f})">'
        f"{html.escape(value)}</text>"
    )


def _decade_label(exponent: int) -> str:
    value = 10**exponent
    if value >= 1_000_000:
        return f"{value // 1_000_000}M"
    if value >= 1_000:
        return f"{value // 1_000}k"
    return str(value)


def bode_svg(
    freq_hz,
    gain_db,
    phase_deg,
    *,
    run_id: str = "",
    width: int = 720,
) -> str:
    """Draw magnitude and phase panels sharing a logarithmic frequency axis."""
    count = _validate(freq_hz, gain_db, phase_deg)
    freqs = [float(value) for value in freq_hz]
    if any(value <= 0 for value in freqs):
        raise ValueError("bode frequencies must be positive")
    gains = [float(value) for value in gain_db]
    phases = [float(value) for value in phase_deg]

    drawn_x, (drawn_gain, drawn_phase) = _decimate(freqs, [gains, phases])
    log_min = math.floor(math.log10(min(drawn_x)))
    log_max = math.ceil(math.log10(max(drawn_x)))
    if log_max <= log_min:
        log_max = log_min + 1

    height = 420
    right = width - RIGHT_MARGIN
    plot_width = right - LEFT
    inner_height = height - TOP - BOTTOM_MARGIN
    gap = 28
    mag_height = (inner_height - gap) * 0.6
    phase_height = (inner_height - gap) * 0.4
    mag_top = TOP
    mag_bottom = mag_top + mag_height
    phase_top = mag_bottom + gap
    phase_bottom = phase_top + phase_height

    def project_x(frequency: float) -> float:
        position = (math.log10(frequency) - log_min) / (log_max - log_min)
        return LEFT + position * plot_width

    g_min, g_max = min(drawn_gain), max(drawn_gain)
    if g_max - g_min < 1e-9:
        g_min -= 1.0
        g_max += 1.0
    g_pad = (g_max - g_min) * 0.08
    g_min -= g_pad
    g_max += g_pad

    def project_gain(value: float) -> float:
        return mag_bottom - (value - g_min) / (g_max - g_min) * mag_height

    def project_phase(value: float) -> float:
        clamped = min(180.0, max(-180.0, value))
        return phase_bottom - (clamped + 180.0) / 360.0 * phase_height

    parts = _frame(
        width,
        height,
        (
            f"run {run_id}, {count} points, "
            f"max {max(gains):.3g} dB, min {min(gains):.3g} dB, "
            f"phase max {max(phases):.3g} deg, min {min(phases):.3g} deg"
        ),
        "Bode plot from ngspice AC sweep",
    )

    for panel_top, panel_bottom in ((mag_top, mag_bottom), (phase_top, phase_bottom)):
        parts.append(
            f'<rect x="{LEFT}" y="{panel_top:.2f}" width="{plot_width}" '
            f'height="{panel_bottom - panel_top:.2f}" fill="#ffffff" '
            'stroke="#cbd5e1"/>'
        )

    for exponent in range(log_min, log_max + 1):
        x_value = LEFT + (exponent - log_min) / (log_max - log_min) * plot_width
        parts.append(_line(x_value, mag_top, x_value, phase_bottom))
        parts.append(_text(x_value, phase_bottom + 15, _decade_label(exponent), anchor="middle"))

    for step in range(1, 5):
        y_value = mag_top + mag_height * step / 4
        parts.append(_line(LEFT, y_value, right, y_value))
        level = g_max - (g_max - g_min) * step / 4
        parts.append(_text(LEFT - 8, y_value + 4, f"{level:.1f}", anchor="end"))

    for level in (-180, -90, 0, 90, 180):
        y_value = project_phase(level)
        parts.append(_line(LEFT, y_value, right, y_value))
        parts.append(_text(LEFT - 8, y_value + 4, str(level), anchor="end"))

    parts.append(_path(drawn_x, drawn_gain, project_x, project_gain, "#dc2626"))
    parts.append(_path(drawn_x, drawn_phase, project_x, project_phase, "#2563eb"))
    parts.append(_y_title(16, mag_top + mag_height / 2, "Gain (dB)"))
    parts.append(_y_title(16, phase_top + phase_height / 2, "Phase (deg)"))
    parts.append(
        _text(
            LEFT + plot_width / 2,
            height - 8,
            "Frequency (Hz)",
            anchor="middle",
            size=12,
        )
    )
    parts.append(_text(LEFT + 8, mag_top + 14, f"{count} points · run {run_id}"))
    parts.append("</svg>")
    return "\n".join(parts)


def transient_svg(
    time_s,
    vin_v,
    vout_v,
    *,
    run_id: str = "",
    width: int = 720,
) -> str:
    """Draw vin and vout on shared millisecond / millivolt axes."""
    count = _validate(time_s, vin_v, vout_v)
    times_ms = [float(value) * 1000.0 for value in time_s]
    vin_mv = [float(value) * 1000.0 for value in vin_v]
    vout_mv = [float(value) * 1000.0 for value in vout_v]

    drawn_x, (drawn_vin, drawn_vout) = _decimate(times_ms, [vin_mv, vout_mv])
    x_min, x_max = min(drawn_x), max(drawn_x)
    if x_max - x_min < 1e-12:
        x_min -= 1.0
        x_max += 1.0
    all_y = drawn_vin + drawn_vout
    y_min, y_max = min(all_y), max(all_y)
    if y_max - y_min < 1e-12:
        y_min -= 1.0
        y_max += 1.0
    y_pad = (y_max - y_min) * 0.08
    y_min -= y_pad
    y_max += y_pad

    height = 300
    right = width - RIGHT_MARGIN
    bottom = height - BOTTOM_MARGIN
    plot_width = right - LEFT
    plot_height = bottom - TOP

    def project_x(value: float) -> float:
        return LEFT + (value - x_min) / (x_max - x_min) * plot_width

    def project_y(value: float) -> float:
        return bottom - (value - y_min) / (y_max - y_min) * plot_height

    parts = _frame(
        width,
        height,
        (
            f"run {run_id}, {count} points, "
            f"max {max(vout_mv):.3g} mV, min {min(vout_mv):.3g} mV"
        ),
        "Transient plot from ngspice",
    )
    parts.append(
        f'<rect x="{LEFT}" y="{TOP}" width="{plot_width}" height="{plot_height}" '
        'fill="#ffffff" stroke="#cbd5e1"/>'
    )
    for step in range(1, 5):
        x_value = LEFT + plot_width * step / 4
        parts.append(_line(x_value, TOP, x_value, bottom))
        parts.append(
            _text(
                x_value,
                bottom + 15,
                f"{x_min + (x_max - x_min) * step / 4:.2f}",
                anchor="middle",
            )
        )
    for step in range(0, 5):
        y_value = TOP + plot_height * step / 4
        parts.append(_line(LEFT, y_value, right, y_value))
        parts.append(
            _text(
                LEFT - 8,
                y_value + 4,
                f"{y_max - (y_max - y_min) * step / 4:.1f}",
                anchor="end",
            )
        )

    parts.append(_path(drawn_x, drawn_vin, project_x, project_y, "#0891b2", dashed=True))
    parts.append(_path(drawn_x, drawn_vout, project_x, project_y, "#dc2626"))
    parts.append(_y_title(16, TOP + plot_height / 2, "Voltage (mV)"))
    parts.append(
        _text(LEFT + plot_width / 2, height - 8, "Time (ms)", anchor="middle", size=12)
    )
    parts.append(_text(LEFT + 8, TOP + 14, f"Vin  ·  Vout  ·  run {run_id}"))
    parts.append("</svg>")
    return "\n".join(parts)
