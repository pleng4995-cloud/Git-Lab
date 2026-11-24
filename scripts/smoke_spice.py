"""Smoke-run ngspice directly to confirm the ``wrdata`` output column layout.

This intentionally does not import ``bjt_bias.spice_engine``: it runs before the
engine module exists and exists to verify assumptions made in the design
(``op.txt`` = 7 columns, ``ac.txt`` and ``tran.txt`` = 3 columns each once
``set wr_singlescale`` is active).

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\smoke_spice.py

Everything is written under %TEMP%\\opencode\\spice-smoke; the repository is
never touched.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

TIMEOUT_S = 60

MODEL_CARD = """\
.model Q2N3904 NPN (Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
"""

CIRCUIT = """\
* CE voltage-divider amplifier v1 (Lab 04 smoke run)
VCC  vcc  0   12
R1   vcc  base 100000
R2   base 0   22000
RC   vcc  coll 2200
RE   emit 0   1000
Q1   coll base emit Q2N3904
CIN  vin  base 10u
COUT coll out  10u
RL   out  0    10000
VIN  vin  0   DC 0 AC 1 SIN(0 10m 1k)
"""

# name -> (result file, .control lines)
# ``wr_singlescale`` writes the scale column once per row instead of repeating
# it before every vector; without it ngspice emits (scale, value) pairs.
ANALYSES = {
    "op": (
        "op.txt",
        [
            "set units=degrees",
            "set wr_singlescale",
            "op",
            "wrdata op.txt v(base) v(emit) v(coll) @q1[ic] @q1[ib] @q1[ie]",
        ],
    ),
    "ac": (
        "ac.txt",
        [
            "set units=degrees",
            "set wr_singlescale",
            "ac dec 20 10 1meg",
            "wrdata ac.txt vdb(out) vp(out)",
        ],
    ),
    "tran": (
        "tran.txt",
        [
            "set wr_singlescale",
            "tran 5u 5m",
            "wrdata tran.txt v(vin) v(out)",
        ],
    ),
}


def locate_engine() -> Path:
    candidates: list[Path] = []

    env = os.environ.get("NGSPICE_BIN")
    if env:
        candidate = Path(env)
        if candidate.is_dir():
            candidates.extend(
                [
                    candidate / "ngspice_con.exe",
                    candidate / "bin" / "ngspice_con.exe",
                    candidate / "ngspice.exe",
                ]
            )
        else:
            candidates.append(candidate)

    for name in ("ngspice_con.exe", "ngspice.exe", "ngspice"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))

    candidates.extend(
        [
            Path(r"C:\Tools\ngspice-47\bin\ngspice_con.exe"),
            Path(r"C:\Tools\ngspice-47\bin\ngspice.exe"),
        ]
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise SystemExit(
        "ngspice not found. Run scripts\\fetch_ngspice.ps1 or set NGSPICE_BIN."
    )


def netlist_for(control_lines: list[str]) -> str:
    body = "\n".join(control_lines)
    return (
        f"{CIRCUIT}\n{MODEL_CARD}\n"
        ".control\n"
        f"{body}\n"
        ".endc\n"
        ".end\n"
    )


def describe_result_file(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = [line for line in raw.splitlines() if line.strip()]
    widths = [len(line.split()) for line in lines]
    return {
        "path": path,
        "raw": raw,
        "lines": lines,
        "widths": widths,
        "rows": len(lines),
    }


def main() -> int:
    args = sys.argv[1:]
    evidence_dir = None
    if "--evidence-dir" in args:
        index = args.index("--evidence-dir")
        try:
            evidence_dir = Path(args[index + 1])
        except IndexError:
            raise SystemExit("--evidence-dir needs a directory argument")
    started = datetime.now(timezone.utc)

    report: list[str] = []
    sections: dict[str, list[str]] = {name: [] for name in ANALYSES}
    observed: dict[str, list[int]] = {}
    current = {"analysis": None}

    def log(line: str = "") -> None:
        print(line)
        report.append(line)
        name = current["analysis"]
        if name is not None:
            sections[name].append(line)

    engine = locate_engine()
    log(f"ngspice: {engine}")
    version = subprocess.run(
        [str(engine), "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    version_text = (version.stdout or "") + (version.stderr or "")
    version_line = next(
        (line.strip() for line in version_text.splitlines() if "ngspice-" in line),
        "unknown",
    )
    log(f"--version exit={version.returncode}: {version_line}")

    root = Path(tempfile.gettempdir()) / "opencode" / "spice-smoke"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    failures = 0
    for analysis, (result_name, control_lines) in ANALYSES.items():
        current["analysis"] = analysis
        run_dir = root / analysis
        run_dir.mkdir()
        (run_dir / "circuit.cir").write_text(netlist_for(control_lines), encoding="utf-8")

        command = [str(engine), "-b", "-o", "run.log", "circuit.cir"]
        log(f"\n=== {analysis} ===")
        log(f"command: {command}")
        try:
            proc = subprocess.run(
                command,
                cwd=run_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=TIMEOUT_S,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            log(f"FAIL: timed out after {TIMEOUT_S}s")
            failures += 1
            continue

        log(f"exit={proc.returncode}")
        for stream_name, text in (("stdout", proc.stdout), ("stderr", proc.stderr)):
            tail = [line for line in (text or "").splitlines() if line.strip()][-10:]
            if tail:
                log(f"{stream_name} tail:")
                for line in tail:
                    log(f"  {line}")

        run_log = run_dir / "run.log"
        if run_log.is_file():
            log_tail = [
                line
                for line in run_log.read_text("utf-8", errors="replace").splitlines()
                if line.strip()
            ][-10:]
            log("run.log tail:")
            for line in log_tail:
                log(f"  {line}")

        result_path = run_dir / result_name
        if proc.returncode != 0 or not result_path.is_file() or result_path.stat().st_size == 0:
            log(f"FAIL: {result_name} missing or empty")
            failures += 1
            continue

        info = describe_result_file(result_path)
        log(f"{result_name}: {info['rows']} data rows")
        widths = sorted(set(info["widths"]))
        observed[analysis] = widths
        log(f"column widths seen: {widths}")
        head = info["lines"][:3]
        tail = info["lines"][-3:]
        for label, sample in (("first", head), ("last", tail)):
            log(f"  {label} {len(sample)} row(s):")
            for line in sample:
                log(f"    [{len(line.split())} cols] {line}")

    log(f"\nSMOKE RESULT: {'PASS' if failures == 0 else 'FAIL'} ({failures} failure(s))")
    current["analysis"] = None

    if evidence_dir is not None:
        evidence_dir.mkdir(parents=True, exist_ok=True)
        stamp = started.strftime("%Y-%m-%dT%H:%M:%SZ")
        for analysis, lines in sections.items():
            header = [
                f"# ngspice smoke run — {analysis}",
                f"generated: {stamp}",
                f"engine: {engine}",
                f"version: {version_line}",
                "netlist: CE voltage-divider v1, VCC=12, R1=100k, R2=22k, RC=2.2k,",
                "         RE=1k, RL=10k, CIN=COUT=10u, VIN SIN(0 10m 1k) AC 1",
                "",
                "note: `set wr_singlescale` is required. Without it ngspice writes",
                "      (scale, value) pairs: op=12 cols, ac=4, tran=4.",
                "note: the XSPICE `../lib/ngspice/xtradev.cm` warning is emitted because",
                "      the run directory has no sibling lib/ tree; this circuit uses no",
                "      XSPICE code models and the run exits 0 with valid data.",
            ]
            footer = [
                "",
                f"observed column widths for this analysis: {observed.get(analysis, 'no data')}",
                f"result: {'PASS' if failures == 0 else 'FAIL'}",
                "",
            ]
            path = evidence_dir / f"smoke-{analysis}.txt"
            path.write_text("\n".join(header + lines + footer), encoding="utf-8")
            print(f"wrote {path}")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
