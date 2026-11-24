"""Lab 04 browser acceptance cases B1-B8 with Microsoft Edge.

Edge headless is used instead of Playwright MCP / npx because this machine has
no Node.js. Each case is a real browser form POST (auto-submitted from a local
HTML file), followed by DOM assertions and a screenshot.

Usage (normal server on port 5000):
    .\\.venv\\Scripts\\python.exe -m bjt_bias.app
    .\\.venv\\Scripts\\python.exe scripts\\browser_acceptance_lab4.py

Usage (B7(b), server started with an invalid NGSPICE_BIN on port 5001):
    $env:NGSPICE_BIN="C:\\does-not-exist\\ngspice.exe"
    .\\.venv\\Scripts\\python.exe -c "from bjt_bias.app import app; app.run(port=5001)"
    .\\.venv\\Scripts\\python.exe scripts\\browser_acceptance_lab4.py --b7b
"""

from __future__ import annotations

import itertools
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

EDGE = os.environ.get(
    "EDGE_PATH",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)
BASE = os.environ.get("APP_URL", "http://127.0.0.1:5000/")
ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "evidence" / "lab4"
TMP = Path(tempfile.gettempdir()) / "bjt_acceptance_lab4"
RUNS = ROOT / "runs"
PROFILE = TMP / "edgeprofile"
RUN_ID_RE = re.compile(r"run (\d{8}T\d{6}-[0-9a-f]{6})")

DIVIDER = {
    "mode": "divider",
    "vcc": "12",
    "r1": "100", "r1_unit": "kohm",
    "r2": "22", "r2_unit": "kohm",
    "rc": "2.2", "rc_unit": "kohm",
    "re": "1", "re_unit": "kohm",
    "beta": "100", "vbe": "0.7",
}
FIXED = {
    "mode": "fixed",
    "vcc": "12",
    "rb": "1", "rb_unit": "mohm",
    "rc": "2.2", "rc_unit": "kohm",
    "beta": "100", "vbe": "0.7",
}
EMITTER = {
    "mode": "emitter",
    "vcc": "12",
    "rb": "1", "rb_unit": "mohm",
    "rc": "2.2", "rc_unit": "kohm",
    "re": "1", "re_unit": "kohm",
    "beta": "100", "vbe": "0.7",
}
SOURCE = {
    "amplitude_mv": "10",
    "frequency_hz": "1000",
    "ac_start_hz": "10",
    "ac_stop_hz": "1000000",
    "ac_points_dec": "20",
}

# B1 must reproduce all four analytical result sets from Lab 03 (A1-A4).
B1_ANALYTICAL = {
    "B1": ({**DIVIDER, "analysis": "analytical"},
           {"IC": "1.230", "VCE": "8.052"}),
    "B1-A2": ({**FIXED, "analysis": "analytical"},
              {"IC": "1.130", "VCE": "9.514"}),
    "B1-A3": ({**EMITTER, "analysis": "analytical"},
              {"IC": "1.026", "VCE": "8.705"}),
    "B1-A4": ({**EMITTER, "re": "2", "analysis": "analytical"},
              {"IC": "0.940", "VCE": "8.033"}),
}

CASES = [
    ("B1", {**DIVIDER, "analysis": "analytical"}, "1280,1400"),
    ("B1-A2", {**FIXED, "analysis": "analytical"}, "1280,1400"),
    ("B1-A3", {**EMITTER, "analysis": "analytical"}, "1280,1400"),
    ("B1-A4", {**EMITTER, "re": "2", "analysis": "analytical"}, "1280,1400"),
    ("B2", {**DIVIDER, "analysis": "dc", **SOURCE}, "1280,1400"),
    ("B3", {**DIVIDER, "re": "2", "analysis": "dc", **SOURCE}, "1280,1400"),
    ("B4", {**DIVIDER, "analysis": "ac", **SOURCE}, "1280,1400"),
    ("B5", {**DIVIDER, "analysis": "tran", **SOURCE}, "1280,1400"),
    ("B6", {**DIVIDER, "analysis": "tran", **SOURCE,
            "amplitude_mv": "20"}, "1280,1400"),
    ("B7A", {**DIVIDER, "re": "0", "analysis": "dc", **SOURCE}, "1280,1400"),
    ("B8-DESKTOP", {**DIVIDER, "analysis": "ac", **SOURCE}, "1280,1400"),
    ("B8-MOBILE", {**DIVIDER, "analysis": "ac", **SOURCE}, "390,900"),
]

B7B = ("B7B", {**DIVIDER, "analysis": "dc", **SOURCE}, "1280,1400")


def form_html(case_id: str, fields: dict, action: str = BASE) -> str:
    inputs = "\n".join(
        f'  <input name="{key}" value="{value}">' for key, value in fields.items()
    )
    return f"""<!doctype html>
<meta charset="utf-8">
<title>{case_id}</title>
<form id="f" method="post" action="{action}">
{inputs}
</form>
<script>document.getElementById('f').submit();</script>
"""


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).replace("&middot;", "·").strip()


def screenshot_snapshot(dom: str, path: Path, base: str) -> Path:
    """Save the rendered DOM so the screenshot needs no second POST/run.

    Reloading the auto-submitting form for `--screenshot` would start a second
    ngspice run whose run id differs from the one recorded in the JSON. Using
    the dumped page keeps the screenshot and the recorded values on the same
    run. The stylesheet is re-pointed at the live server (file:// cannot
    resolve the app's absolute /static path).
    """
    html = dom.replace(
        'href="/static/style.css"', f'href="{base}static/style.css"'
    )
    path.write_text(html, encoding="utf-8")
    return path


def save_run_artifacts(run_dir: Path, case_id: str) -> None:
    """Copy the real netlist and data excerpts into the evidence directory."""
    if not run_dir.is_dir():
        return
    name = case_id.lower()
    netlist = run_dir / "circuit.cir"
    if netlist.is_file():
        (EVIDENCE / f"{name}-netlist.cir").write_text(
            netlist.read_text(encoding="utf-8", errors="replace"),
            encoding="utf-8",
        )
    for data_name in ("op.txt", "ac.txt", "tran.txt"):
        source = run_dir / data_name
        if not source.is_file():
            continue
        lines = source.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines()
        excerpt = lines[:12] + (["..."] + lines[-3:] if len(lines) > 15 else [])
        (EVIDENCE / f"{name}-{data_name}").write_text(
            f"# run {run_dir.name}: first {min(12, len(lines))} lines "
            f"+ last {min(3, max(0, len(lines) - 12))} lines of {data_name}\n"
            + "\n".join(excerpt) + "\n",
            encoding="utf-8",
        )


def save_error_evidence(case_id: str, parsed: dict) -> None:
    """Keep the browser-visible error text for the two B7 cases."""
    text = "\n".join(
        [
            f"=== {case_id} browser error text ===",
            parsed["spice_error"] or "\n".join(parsed["errors"]),
            f"engine_ok={parsed['engine_ok']} engine_bad={parsed['engine_bad']}",
            f"run_id={parsed['run_id']} plots={parsed['plot_count']}",
        ]
    )
    (EVIDENCE / f"{case_id.lower()}-error.txt").write_text(
        text + "\n", encoding="utf-8"
    )


_PROFILE_IDS = itertools.count()


def run_edge(args: list[str]) -> str:
    """Run Edge with a fresh profile; retry an empty dump once (profile lock)."""
    for _attempt in range(3):
        profile = TMP / "profiles" / str(next(_PROFILE_IDS))
        cmd = [
            EDGE, "--headless=new", "--disable-gpu", "--no-first-run",
            "--allow-file-access-from-files",
            f"--user-data-dir={profile}",
            "--virtual-time-budget=12000",
            *args,
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=180,
        )
        if proc.stdout.strip() or "--dump-dom" not in args:
            return proc.stdout
    return ""


def table_rows(dom: str, css_class: str) -> list[list[str]]:
    match = re.search(
        rf'<table class="{css_class}">(.*?)</table>', dom, re.S
    )
    if not match:
        return []
    rows = []
    for row in re.findall(r"<tr>(.*?)</tr>", match.group(1), re.S):
        cells = [
            strip_tags(cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        ]
        if cells:
            rows.append(cells)
    return rows


def parse(dom: str) -> dict:
    out: dict = {}
    out["results"] = table_rows(dom, "results")
    out["compare"] = table_rows(dom, "compare-table")
    out["run_id"] = (RUN_ID_RE.search(dom) or [None, None])[1]
    out["engine_ok"] = 'class="engine-bar ok"' in dom
    out["engine_bad"] = 'class="engine-bar bad"' in dom
    out["spice_panel"] = "panel-spice" in dom
    out["spice_badge"] = "provenance-badge spice" in dom
    out["analytical_badge"] = "ANALYTICAL" in dom
    out["plot_count"] = dom.count('<svg xmlns="http://www.w3.org/2000/svg"')
    out["plot_has_bode_units"] = (
        "Gain (dB)" in dom and "Phase (deg)" in dom and "Frequency (Hz)" in dom
    )
    out["plot_has_tran_units"] = (
        "Time (ms)" in dom and "Vin" in dom and "Vout" in dom
    )
    err = re.search(r'<section class="errors".*?</section>', dom, re.S)
    out["errors"] = (
        [strip_tags(item) for item in re.findall(r"<li>(.*?)</li>", err.group(0), re.S)]
        if err else []
    )
    spice_err = re.search(r'<div class="spice-error".*?</div>', dom, re.S)
    out["spice_error"] = (
        strip_tags(spice_err.group(0)) if spice_err else ""
    )
    out["model_visible"] = "2N3904" in dom
    out["mode"] = re.search(r"DC Bias Results &mdash; ([^<]+)", dom)
    out["mode"] = out["mode"].group(1).strip() if out["mode"] else None
    return out


def run_data(run_id: str | None) -> tuple[Path, dict]:
    if not run_id:
        return Path(), {}
    meta = RUNS / run_id / "meta.json"
    if not meta.is_file():
        return Path(), {}
    return RUNS / run_id, json.loads(meta.read_text(encoding="utf-8"))


def read_columns(path: Path) -> list[list[float]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.lstrip().startswith("*"):
            continue
        try:
            rows.append([float(token) for token in line.split()])
        except ValueError:
            continue
    return rows


def peak_to_peak(values: list[float], tail: int) -> float:
    segment = values[-tail:]
    return max(segment) - min(segment) if segment else 0.0


def correlation(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    a, b = left[-size:], right[-size:]
    if size < 2:
        return 0.0
    mean_a, mean_b = sum(a) / size, sum(b) / size
    cov = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    var_a = sum((x - mean_a) ** 2 for x in a)
    var_b = sum((y - mean_b) ** 2 for y in b)
    if var_a == 0 or var_b == 0:
        return 0.0
    return cov / math.sqrt(var_a * var_b)


def get_dom(url: str) -> str:
    return run_edge(["--dump-dom", url])


def check(results: list[str], condition: bool, message: str) -> None:
    results.append(("PASS " if condition else "FAIL ") + message)


def main() -> int:
    if not Path(EDGE).exists():
        print(f"Edge not found at {EDGE}; set EDGE_PATH.")
        return 2
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    summary: dict = {}
    checks: list[str] = []

    if "--b7b" in sys.argv:
        cases = [B7B]
        base = os.environ.get("APP_URL", "http://127.0.0.1:5001/")
    else:
        cases = CASES
        base = BASE
        # B1 also checks that switching bias mode changes the schematic/heading.
        for mode, label in (
            ("divider", "Voltage Divider Bias"),
            ("fixed", "Fixed Bias"),
            ("emitter", "Emitter Bias"),
        ):
            dom = get_dom(f"{base}?mode={mode}")
            check(checks, label in dom, f"B1 GET ?mode={mode} heading")
            if mode == "divider":
                check(
                    checks,
                    'name="analysis" value="dc"' in dom,
                    "B1 GET ?mode=divider shows SPICE buttons",
                )
            else:
                check(
                    checks,
                    "SPICE is available for the Voltage Divider reference only" in dom,
                    f"B1 GET ?mode={mode} hides SPICE buttons",
                )

    for case_id, fields, window in cases:
        html_path = TMP / f"lab4_{case_id}.html"
        html_path.write_text(form_html(case_id, fields, base), encoding="utf-8")
        uri = html_path.as_uri()
        dom = get_dom(uri)
        parsed = parse(dom)
        snapshot = screenshot_snapshot(
            dom, TMP / f"lab4_{case_id}_snapshot.html", base
        )
        shot = EVIDENCE / f"{case_id.lower()}.png"
        run_edge([
            f"--screenshot={shot}", f"--window-size={window}", snapshot.as_uri()
        ])
        run_dir, meta = run_data(parsed["run_id"])
        parsed["run_dir"] = str(run_dir)
        parsed["engine_version"] = (meta.get("engine") or {}).get("version")
        parsed["screenshot"] = str(shot.relative_to(ROOT))
        parsed["screenshot_exists"] = shot.is_file()
        parsed["screenshot_source"] = "dom snapshot of this run (no second POST)"
        summary[case_id] = parsed
        check(checks, shot.is_file(), f"{case_id} screenshot saved")
        save_run_artifacts(run_dir, case_id)
        if case_id in ("B7A", "B7B"):
            save_error_evidence(case_id, parsed)

        if case_id in B1_ANALYTICAL:
            values = {row[0]: row[1] for row in parsed["results"]}
            summary[case_id]["parsed_values"] = values
            expected = B1_ANALYTICAL[case_id][1]
            for key, value in expected.items():
                check(checks, value in values.get(key, ""),
                      f"{case_id} {key} = {value}")
            check(checks, parsed["analytical_badge"],
                  f"{case_id} analytical badge")
            check(checks, not parsed["spice_panel"], f"{case_id} no SPICE panel")

        if case_id == "B2":
            compare = {row[0]: row[1:] for row in parsed["compare"]}
            summary[case_id]["compare"] = compare
            check(checks, parsed["spice_badge"], "B2 SPICE provenance badge")
            check(checks, parsed["model_visible"], "B2 model 2N3904 visible")
            check(checks, bool(parsed["run_id"]), "B2 run id visible")
            check(checks, (run_dir / "op.txt").is_file(), "B2 op.txt exists")
            check(checks, len(compare) == 7, "B2 seven compare rows")
            ic = compare.get("IC", ["", ""])[1]
            vce = compare.get("VCE", ["", ""])[1]
            try:
                check(checks, 1.2 <= float(ic.split()[0]) <= 1.5,
                      "B2 SPICE IC in 1.2-1.5 mA")
                check(checks, float(vce.split()[0]) > 5.0,
                      "B2 SPICE VCE > 5 V")
            except ValueError:
                check(checks, False, "B2 numeric compare values")

        if case_id == "B3":
            compare = {row[0]: row[1:] for row in parsed["compare"]}
            summary[case_id]["compare"] = compare
            before = summary.get("B2", {}).get("compare", {})
            check(checks, bool(parsed["run_id"]), "B3 new run id")
            check(checks, parsed["run_id"] != summary.get("B2", {}).get("run_id"),
                  "B3 run id differs from B2")
            try:
                ic_b3 = float(compare.get("IC", ["", ""])[1].split()[0])
                ic_b2 = float(before.get("IC", ["", ""])[1].split()[0])
                check(checks, abs(ic_b3 - ic_b2) > 0.05 * ic_b2,
                      "B3 SPICE IC changed by >5%")
            except ValueError:
                check(checks, False, "B3 numeric compare values")

        if case_id in ("B4", "B5", "B6", "B8-DESKTOP", "B8-MOBILE"):
            check(checks, parsed["spice_panel"], f"{case_id} SPICE panel")
            check(checks, parsed["plot_count"] >= 1, f"{case_id} SVG plot rendered")
            if case_id in ("B4", "B8-DESKTOP", "B8-MOBILE"):
                check(checks, parsed["plot_has_bode_units"], f"{case_id} Bode units")
            check(checks, bool(parsed["run_id"]), f"{case_id} run id")
            if case_id in ("B4", "B8-DESKTOP", "B8-MOBILE"):
                rows = read_columns(run_dir / "ac.txt")
                summary[case_id]["ac_rows"] = len(rows)
                check(checks, len(rows) >= 100, f"{case_id} ac.txt >= 100 rows")
            if case_id in ("B5", "B6"):
                rows = read_columns(run_dir / "tran.txt")
                summary[case_id]["tran_rows"] = len(rows)
                check(checks, len(rows) >= 100, f"{case_id} tran.txt >= 100 rows")
                check(checks, parsed["plot_has_tran_units"], f"{case_id} transient units")
                if len(rows) >= 200:
                    vin = [row[1] for row in rows]
                    vout = [row[2] for row in rows]
                    summary[case_id]["vout_pp_v"] = peak_to_peak(vout, 200)
                    if case_id == "B5":
                        rho = correlation(vin, vout)
                        summary[case_id]["vin_vout_correlation"] = round(rho, 3)
                        check(checks, rho < -0.5,
                              "B5 Vin/Vout show ~180 deg phase inversion")
                    else:
                        before_rows = read_columns(
                            run_data(summary.get("B5", {}).get("run_id"))[0] / "tran.txt"
                        )
                        if before_rows:
                            before_pp = peak_to_peak([row[2] for row in before_rows], 200)
                            after_pp = peak_to_peak(vout, 200)
                            summary[case_id]["vout_pp_before_v"] = before_pp
                            check(checks, after_pp > 1.5 * before_pp,
                                  "B6 Vout amplitude ~doubled")
            if case_id == "B6":
                check(
                    checks,
                    parsed["run_id"] != summary.get("B5", {}).get("run_id"),
                    "B6 run id differs from B5",
                )

        if case_id == "B7A":
            check(checks, any("RE" in error for error in parsed["errors"]),
                  "B7(a) error names RE")
            check(checks, not parsed["spice_panel"], "B7(a) no SPICE panel")
            check(checks, not parsed["run_id"], "B7(a) engine not called")
            check(checks, parsed["plot_count"] == 0, "B7(a) no plot")

        if case_id == "B7B":
            check(checks, parsed["engine_bad"], "B7(b) red engine bar")
            check(checks, "ngspice not found" in dom, "B7(b) engine-not-found text")
            check(checks, parsed["spice_panel"], "B7(b) error card shown")
            check(checks, "engine_missing" in parsed["spice_error"].lower()
                  or "ngspice not found" in parsed["spice_error"].lower(),
                  "B7(b) error status visible")
            check(checks, parsed["plot_count"] == 0, "B7(b) no plot")
            check(checks, not parsed["run_id"], "B7(b) no run id")

        print(f"=== {case_id} ===")
        print("  run      :", parsed["run_id"])
        print("  engine   :", parsed["engine_version"])
        print("  errors   :", parsed["errors"] or parsed["spice_error"][:120])
        print("  plots    :", parsed["plot_count"])
        print("  shot     :", parsed["screenshot_exists"])

    mode = "b7b" if "--b7b" in sys.argv else "main"
    out_json = EVIDENCE / f"acceptance-{mode}.json"
    out_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (EVIDENCE / f"checks-{mode}.txt").write_text(
        "\n".join(checks) + "\n", encoding="utf-8"
    )
    failures = [line for line in checks if line.startswith("FAIL")]
    print(f"\n{len(checks) - len(failures)}/{len(checks)} checks PASS")
    for line in failures:
        print(line)
    print("saved", out_json)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
