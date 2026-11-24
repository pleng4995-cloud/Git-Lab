# Lab 04 SPICE Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ต่อยอด Flask BJT bias app ของ Lab 03 ให้รัน ngspice จริงบนวงจร CE Voltage-Divider v1 แล้วแสดง `.op` / `.ac` / `.tran` พร้อมกราฟที่สร้างจากผลรันและป้ายแยก Analytical กับ SPICE

**Architecture:** `app.py` ตรวจ input แล้ว dispatch ไป `bias.py` (Analytical เดิม) หรือ `spice_engine.py` (netlist → `subprocess.run` → parse ไฟล์ ASCII) แล้วส่ง array ให้ `plots.py` สร้าง SVG ในคำขอเดียวกัน ไม่มี cache ของผลรัน — ทุกครั้งที่กด Run จะได้ run directory ใหม่

**Tech Stack:** Python 3.14, Flask 3.1.3, ngspice-47 (portable), `unittest`, SVG ที่สร้างเอง (ไม่เพิ่ม dependency)

**Spec:** `docs/superpowers/specs/2026-11-24-lab04-spice-design.md`

## Global Constraints

- ห้ามแก้ `bjt_bias/bias.py` และห้ามเปลี่ยนผล Analytical DC Bias 3 โหมด
- เทสเดิม 62 ตัว (`test_bjt_app.py`, `test_bjt_bias.py`, `test_electrical.py`) ต้องผ่านทุกข้อ
- `analysis` ที่ไม่ส่งมาใน POST ต้องหมายถึง `analytical` และ **ห้ามเรียก ngspice**
- SPICE รับเฉพาะ `mode == "divider"`
- `subprocess.run` ต้องเป็น argument list, `shell=False`, `timeout=60`
- ค่าจากฟอร์มต้องผ่าน `float()` ก่อนเข้า netlist ห้ามต่อ string ดิบ
- ไม่เพิ่ม dependency ใน `requirements.txt` (คงมีแค่ Flask)
- ผลทุกตัวที่แสดงต้องมาจาก run ในคำขอนั้น; status ไม่ใช่ `ok` → ห้ามมีกราฟ/ตัวเลข SPICE
- BJT model ชื่อ `2N3904` จาก `bjt_bias/spice_models/2n3904.lib` เท่านั้น
- เก็บ run ที่ `runs/` (gitignore) และคัดเฉพาะหลักฐานไป `docs/evidence/lab4/`
- ห้ามแก้ h1 "Lab 02: BJT DC Bias Web App" และ "Week 2 Goal" (มีเทส assert)

## Review Focus

1. **Engine ไม่พร้อม / timeout / exit ≠ 0** — ผู้ใช้คาดเห็น error ที่บอกสาเหตุและไม่มีกราฟหรือตัวเลขค้างจากรอบก่อน (Task 5, 7)
2. **`analysis` หายจาก POST** — client/เทสเก่าต้องได้ผล Analytical เหมือน Lab 03 เป๊ะและไม่ช้า (Task 7)
3. **โหมด Fixed/Emitter สั่ง SPICE** — ต้องได้ error ที่อ่านรู้เรื่องและไม่เรียก engine (Task 7)
4. **ผล ngspice ผิดรูป** (คอลัมน์ไม่ครบ, NaN, ไฟล์ว่าง) — ต้องเป็น `parse_error` ไม่ใช่ crash หรือกราฟเปล่า (Task 4, 5)
5. **ค่าอินพุตขอบเขต** (0, ติดลบ, เกินช่วง, start ≥ stop, `5/f > 2 s`) — ต้องถูกปฏิเสธก่อนสร้าง netlist (Task 7)
6. **กราฟต้องมาจากข้อมูลจริง** — เปลี่ยน RE/amplitude แล้ว path และ `<desc>` ต้องเปลี่ยน (Task 6, 9)

---

### Task 1: ติดตั้ง ngspice portable และทำ smoke run

**Files:**
- Create: `scripts/fetch_ngspice.ps1`
- Create: `scripts/smoke_spice.py`
- Create: `docs/evidence/lab4/smoke-op.txt`, `smoke-ac.txt`, `smoke-tran.txt` (ผลจากรอบจริง)
- Modify: `.gitignore`

**Interfaces:**
- Produces: path ของ `ngspice.exe` ที่ใช้ได้จริง + รูปแบบคอลัมน์ของ `wrdata` ที่ Task 4 จะ parse

- [ ] **Step 1: เขียน `scripts/fetch_ngspice.ps1`**

ต้องทำ: ตรวจว่ามี `C:\Tools\ngspice-47\` แล้วหรือยัง → ดาวน์โหลด
`https://sourceforge.net/projects/ngspice/files/ng-spice-rework/47/ngspice-47_64.7z`
ด้วย `Invoke-WebRequest` → แตกด้วย `tar -xf` → ถ้าล้มเหลว ดาวน์โหลด `https://www.7-zip.org/a/7zr.exe`
แล้วแตกด้วย `7zr.exe` → หา `ngspice.exe` ใต้โฟลเดอร์ที่แตก → พิมพ์ path และ SHA256
ของ archive → ไม่เขียนอะไรลง repo

- [ ] **Step 2: รันสคริปต์และยืนยันเวอร์ชัน**

Run: `powershell -ExecutionPolicy Bypass -File scripts\fetch_ngspice.ps1`
Expected: จบด้วยบรรทัด `ngspice path: C:\Tools\ngspice-47\...\ngspice.exe`

Run: `& "C:\Tools\ngspice-47\<path>\ngspice.exe" --version`
Expected: บรรทัดแรกมีคำว่า `ngspice-47`

- [ ] **Step 3: เขียน `scripts/smoke_spice.py`**

สคริปต์สร้าง netlist ชั่วคราวใน `%TEMP%\opencode\spice-smoke\` (ไม่ใช้ `bjt_bias.spice_engine`
เพราะยังไม่มี) แล้วรัน ngspice สามครั้ง (`op`, `ac dec 20 10 1meg`, `tran 5u 5m`)
ด้วย `subprocess.run([...], cwd=run_dir, timeout=60)` และ `wrdata` ตามลำดับ
จากนั้นพิมพ์จำนวนคอลัมน์ของ 3 บรรทัดแรกและ 3 บรรทัดสุดท้ายของแต่ละไฟล์

- [ ] **Step 4: รัน smoke และบันทึกหลักฐาน**

Run: `.\.venv\Scripts\python.exe scripts\smoke_spice.py`
Expected: ไฟล์ `op.txt` (7 คอลัมน์), `ac.txt` (3 คอลัมน์), `tran.txt` (3 คอลัมน์)
ถ้าจำนวนคอลัมน์ไม่ตรง ให้แก้ parser ใน Task 4 ตามที่เห็นจริง แล้วจดไว้ใน
`docs/evidence/lab4/smoke-*.txt`

คัดลอก output ของ smoke (หัวไฟล์ + ท้ายไฟล์ + จำนวนบรรทัด) ไปไว้ใน
`docs/evidence/lab4/smoke-op.txt`, `smoke-ac.txt`, `smoke-tran.txt`

- [ ] **Step 5: เพิ่ม `runs/` ใน `.gitignore` และ commit**

```powershell
Add-Content .gitignore "runs/"
git add .gitignore scripts/fetch_ngspice.ps1 scripts/smoke_spice.py docs/evidence/lab4
git commit -m "chore: add portable ngspice fetch script and layout smoke run"
```

---

### Task 2: BJT model file พร้อม provenance

**Files:**
- Create: `bjt_bias/spice_models/2n3904.lib`
- Create: `bjt_bias/spice_models/README.md`
- Test: `test_spice_engine.py`

**Interfaces:**
- Produces: `bjt_bias/spice_models/2n3904.lib` ที่ประกาศ `.model Q2N3904 NPN (...)` และ
  `spice_engine.MODEL_PATH` ชี้ไฟล์นี้

- [ ] **Step 1: เขียนเทสที่ยังไม่ผ่านใน `test_spice_engine.py`**

```python
import unittest
from pathlib import Path

from bjt_bias import spice_engine


class TestModelFile(unittest.TestCase):
    def test_model_file_defines_q2n3904(self):
        text = spice_engine.MODEL_PATH.read_text(encoding="utf-8")
        self.assertIn(".model Q2N3904 NPN", text)
        for param in ("IS=6.734f", "BF=416.4", "VAF=74.03"):
            self.assertIn(param, text)

    def test_model_path_is_inside_package(self):
        self.assertTrue(spice_engine.MODEL_PATH.is_file())
        self.assertEqual(spice_engine.MODEL_PATH.parent.name, "spice_models")
```

- [ ] **Step 2: รันเทสให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_spice_engine -v`
Expected: FAIL — `ModuleNotFoundError: bjt_bias.spice_engine`

- [ ] **Step 3: สร้างโมเดลและ README ที่มาของโมเดล**

`2n3904.lib` ต้องมีหัวคอมเมนต์: ชื่อ, ผู้ผลิตต้นทาง (ON Semiconductor 2N3904),
วันที่ดึง, ชื่อไฟล์อ้างอิงที่ใช้ตรวจ, และข้อความว่า "parameters copied verbatim;
do not tune to match analytical results" ตามด้วย:

```
.model Q2N3904 NPN (Is=6.734f Xti=3 Eg=1.11 Vaf=74.03 Bf=416.4 Ne=1.259
+ Ise=6.734f Ikf=66.78m Xtb=1.5 Br=.7371 Nc=2 Isc=0 Ikr=0 Rc=1
+ Cjc=3.638p Mjc=.3085 Vjc=.75 Fc=.5 Cje=4.493p Mje=.2593 Vje=.75
+ Tr=239.5n Tf=301.2p Itf=.4 Vtf=4 Xtf=2 Rb=10)
```

`spice_models/README.md` อธิบายว่าทำไมจึงเลือกโมเดลนี้ (ไม่มี Instructor Starter Kit),
URL/แหล่งที่ตรวจ, และวิธีเปลี่ยนโมเดลถ้าผู้สอนแจก Starter Kit ภายหลัง

- [ ] **Step 4: สร้าง `spice_engine.py` โครงเปล่าให้ import ได้**

```python
"""Adapter for running ngspice on the CE voltage-divider reference circuit."""

from pathlib import Path

MODEL_NAME = "2N3904"
MODEL_PATH = Path(__file__).with_name("spice_models") / "2n3904.lib"
```

- [ ] **Step 5: รันเทสให้ผ่าน และ commit**

Run: `.\.venv\Scripts\python.exe -m unittest test_spice_engine -v`
Expected: 2 tests PASS

```powershell
git add bjt_bias/spice_models bjt_bias/spice_engine.py test_spice_engine.py
git commit -m "feat: add 2N3904 model with provenance"
```

---

### Task 3: ตัวเลข SI และ netlist builder

**Files:**
- Modify: `bjt_bias/spice_engine.py`
- Test: `test_spice_engine.py`

**Interfaces:**
- Produces:
  - `format_spice_number(value: float) -> str`
  - `build_netlist(circuit: dict, analysis: str, *, model_path: Path = MODEL_PATH) -> str`
  - `CIRCUIT_DEFAULTS: dict` (คีย์: `vcc, r1, r2, rc, re, rl, cin, cout, amplitude_v, frequency_hz, ac_start_hz, ac_stop_hz, ac_points_dec`)
  - `ANALYSES = ("dc", "ac", "tran")`

- [ ] **Step 1: เขียนเทส netlist**

```python
class TestNetlist(unittest.TestCase):
    def circuit(self, **overrides):
        values = dict(spice_engine.CIRCUIT_DEFAULTS)
        values.update(overrides)
        return values

    def test_number_formatting_is_spice_safe(self):
        self.assertEqual(spice_engine.format_spice_number(100000.0), "100000")
        self.assertEqual(spice_engine.format_spice_number(2200.0), "2200")
        self.assertEqual(spice_engine.format_spice_number(0.01), "0.01")
        self.assertNotIn("e+", spice_engine.format_spice_number(1e6))

    def test_dc_netlist_contains_reference_circuit(self):
        text = spice_engine.build_netlist(self.circuit(re=2000.0), "dc")
        for fragment in ("VCC  vcc  0", "R1   vcc  base", "RE   emit 0   2000",
                         "Q1   coll base emit Q2N3904", "CIN  vin  base",
                         "COUT coll out", "RL   out  0", ".include"):
            self.assertIn(fragment, text)
        self.assertIn("op", text)
        self.assertIn("wrdata op.txt", text)
        self.assertNotIn("ac dec", text)
        self.assertNotIn("tran", text)

    def test_ac_netlist_has_sweep_and_no_transient(self):
        text = spice_engine.build_netlist(self.circuit(), "ac")
        self.assertIn("ac dec 20 10 1e+06", text)
        self.assertIn("wrdata ac.txt vdb(out) vp(out)", text)
        self.assertNotIn("wrdata tran.txt", text)

    def test_tran_netlist_uses_five_cycles(self):
        text = spice_engine.build_netlist(self.circuit(frequency_hz=1000.0), "tran")
        self.assertIn("tran 5e-06 0.005", text)
        self.assertIn("SIN(0 0.01 1000)", text)

    def test_unknown_analysis_rejected(self):
        with self.assertRaises(ValueError):
            spice_engine.build_netlist(self.circuit(), "noise")
```

- [ ] **Step 2: รันให้ fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_spice_engine.TestNetlist -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'CIRCUIT_DEFAULTS'`

- [ ] **Step 3: implement `format_spice_number`, `CIRCUIT_DEFAULTS`, `build_netlist`**

- `format_spice_number` ใช้ `f"{value:.12g}"` แล้วถ้ามี `e+` ให้แปลงเป็นรูปแบบที่ ngspice รับ
  (เช่น `1e+06` → `1e+06` ใช้ได้; ห้ามมี comma)
- `build_netlist` ประกอบตามลำดับอุปกรณ์ใน design (ข้อ 3) แล้วต่อ `.control` ตาม analysis:
  - `dc`: `set units=degrees` + `op` + `wrdata op.txt v(base) v(emit) v(coll) @q1[ic] @q1[ib] @q1[ie]`
  - `ac`: `set units=degrees` + `ac dec <points> <fstart> <fstop>` + `wrdata ac.txt vdb(out) vp(out)`
  - `tran`: `tran <step> <stop>` + `wrdata tran.txt v(vin) v(out)` โดย `stop = 5/f`,
    `step = stop/1000`, ค่ามาจาก `circuit["frequency_hz"]`
- ใช้ `model_path.as_posix()` ใน `.include`

- [ ] **Step 4: รันเทสทั้งไฟล์**

Run: `.\.venv\Scripts\python.exe -m unittest test_spice_engine -v`
Expected: ทุกข้อ PASS (รวมของ Task 2)

- [ ] **Step 5: commit**

```powershell
git add bjt_bias/spice_engine.py test_spice_engine.py
git commit -m "feat: build ngspice netlists for dc, ac and transient"
```

---

### Task 4: Parsers สำหรับผล `.op` / `.ac` / `.tran`

**Files:**
- Modify: `bjt_bias/spice_engine.py`
- Test: `test_spice_engine.py`

**Interfaces:**
- Produces:
  - `class SpiceParseError(ValueError)`
  - `parse_op(text: str) -> dict` → `{"v_b_v","v_e_v","v_c_v","v_ce_v","i_b_a","i_c_a","i_e_a"}`
  - `parse_ac(text: str) -> dict` → `{"freq_hz": list, "gain_db": list, "phase_deg": list}`
  - `parse_tran(text: str) -> dict` → `{"time_s": list, "vin_v": list, "vout_v": list}`
  - `parse_ac_safe(text: str) -> dict` / `parse_tran_safe(text: str) -> dict` (เพิ่มการตรวจจำนวนแถวขั้นต่ำและ monotonic)

- [ ] **Step 1: เขียนเทสด้วย fixture จาก Task 1**

สร้าง fixture ในเทส (ตัดจาก `docs/evidence/lab4/smoke-*.txt` 3–4 บรรทัด):

```python
OP_OK = "0\t2.101\t1.452\t8.806\t0.00145\t0.00342\t0.00146\n"
AC_OK = "1.000000e+01\t4.9\t178.2\n1.000000e+03\t5.1\t179.0\n"
TRAN_OK = "0.000000e+00\t0.0\t0.0\n1.000000e-06\t0.0006\t-0.0011\n"

class TestParsers(unittest.TestCase):
    def test_op_values(self):
        data = spice_engine.parse_op(OP_OK)
        self.assertAlmostEqual(data["v_b_v"], 2.101)
        self.assertAlmostEqual(data["v_ce_v"], 8.806 - 1.452)
        self.assertAlmostEqual(data["i_c_a"], 0.00145)

    def test_ac_arrays(self):
        data = spice_engine.parse_ac(AC_OK)
        self.assertEqual(data["freq_hz"], [10.0, 1000.0])
        self.assertEqual(data["gain_db"], [4.9, 5.1])
        self.assertEqual(data["phase_deg"], [178.2, 179.0])

    def test_tran_arrays(self):
        data = spice_engine.parse_tran(TRAN_OK)
        self.assertEqual(len(data["time_s"]), 2)
        self.assertEqual(data["vout_v"][1], -0.0011)

    def test_wrong_column_count_raises(self):
        with self.assertRaises(spice_engine.SpiceParseError):
            spice_engine.parse_ac_safe("10 4.9\n")

    def test_nan_and_empty_raise(self):
        for bad in ("", "nan nan nan\n", "abc def ghi\n"):
            with self.subTest(bad=bad):
                with self.assertRaises(spice_engine.SpiceParseError):
                    spice_engine.parse_ac_safe(bad)

    def test_non_increasing_sweep_raises(self):
        with self.assertRaises(spice_engine.SpiceParseError):
            spice_engine.parse_ac_safe("1000 5 180\n10 5 180\n")
```

> `parse_ac_safe` เป็นตัวห่อที่ใช้ร่วมกัน (ตรวจแถวขั้นต่ำ + monotonic) และเป็นตัวที่
> `run_analysis` เรียก — `parse_ac` เองตรวจเฉพาะรูปแบบคอลัมน์

- [ ] **Step 2: รันให้ fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_spice_engine.TestParsers -v`
Expected: FAIL — ไม่มี `SpiceParseError`

- [ ] **Step 3: implement parser**

- `_rows(text)` → list ของ list[float]; ข้ามบรรทัดว่าง; บรรทัดที่มี `#` หรือตัวอักษรอื่นให้
  ทิ้งเฉพาะเมื่ออยู่ต้นไฟล์หรือขึ้นต้นด้วย `*`; ค่าที่ parse ไม่ได้ → `SpiceParseError`
  พร้อมเลขบรรทัด
- `parse_op` ต้องได้ความกว้าง 7 (scale + 6) หรือ 6 (ไม่มี scale) มิฉะนั้น error
  พร้อมข้อความ `expected 6 values per row, saw <n>`
- `parse_ac` / `parse_tran` ต้องได้ความกว้าง 3 (หรือ 1 + n ตาม layout ที่ Task 1 ยืนยัน)
- `parse_ac_safe`: ต้องมี ≥ 10 แถว, freq เพิ่มขึ้นทุกแถว
- `parse_tran_safe`: ต้องมี ≥ 100 แถว, time เพิ่มขึ้นทุกแถว
- ทุกค่าต้อง `math.isfinite`

- [ ] **Step 4: รันเทสและ commit**

Run: `.\.venv\Scripts\python.exe -m unittest test_spice_engine -v`
Expected: PASS ทุกข้อ

```powershell
git add bjt_bias/spice_engine.py test_spice_engine.py
git commit -m "feat: parse ngspice op, ac and tran output with strict checks"
```

---

### Task 5: `run_analysis` — engine discovery, run directory, error contract

**Files:**
- Modify: `bjt_bias/spice_engine.py`
- Test: `test_spice_engine.py`

**Interfaces:**
- Produces:
  - `locate_engine(timeout: float = 10.0) -> dict` → `{"available","path","version","source","error"}`
  - `run_analysis(circuit: dict, analysis: str, *, runs_root: Path = RUNS_ROOT, engine: dict | None = None, timeout: float = 60.0) -> dict`
  - ผลลัพธ์มีคีย์: `status, analysis, run_id, run_dir, netlist, command, returncode, duration_s, engine, model, data, warnings, stdout_tail, stderr_tail`
  - `status ∈ {"ok","engine_missing","failed","timeout","parse_error"}` และ `data == {}` เสมอเมื่อ status ≠ ok

- [ ] **Step 1: เขียนเทส contract**

```python
class TestRunContract(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.circuit = dict(spice_engine.CIRCUIT_DEFAULTS)

    def test_engine_missing_status(self):
        result = spice_engine.run_analysis(
            self.circuit, "dc", runs_root=self.tmp,
            engine={"available": False, "path": None, "version": None,
                    "source": "none", "error": "ngspice not found"},
        )
        self.assertEqual(result["status"], "engine_missing")
        self.assertEqual(result["data"], {})
        self.assertIn("not found", result["stderr_tail"])

    def test_bad_binary_reports_failed(self):
        result = spice_engine.run_analysis(
            self.circuit, "dc", runs_root=self.tmp,
            engine={"available": True, "path": sys.executable, "version": "x",
                    "source": "test", "error": None},
            timeout=20,
        )
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["data"], {})
        self.assertNotEqual(result["returncode"], 0)

    def test_timeout_reports_timeout(self):
        with mock.patch("bjt_bias.spice_engine.subprocess.run",
                        side_effect=subprocess.TimeoutExpired("ngspice", 1)):
            result = spice_engine.run_analysis(
                self.circuit, "dc", runs_root=self.tmp,
                engine={"available": True, "path": "ngspice", "version": "x",
                        "source": "test", "error": None}, timeout=1,
            )
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["data"], {})

    def test_run_directory_holds_netlist_and_meta(self):
        result = spice_engine.run_analysis(
            self.circuit, "dc", runs_root=self.tmp,
            engine={"available": True, "path": sys.executable, "version": "x",
                    "source": "test", "error": None}, timeout=20,
        )
        run_dir = Path(result["run_dir"])
        self.assertTrue((run_dir / "circuit.cir").is_file())
        self.assertTrue((run_dir / "meta.json").is_file())
        self.assertEqual(json.loads((run_dir / "meta.json").read_text("utf-8"))
                         ["analysis"], "dc")
```

- [ ] **Step 2: รันให้ fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_spice_engine.TestRunContract -v`
Expected: FAIL — ไม่มี `run_analysis`

- [ ] **Step 3: implement**

- `locate_engine`: env `NGSPICE_BIN` → `shutil.which("ngspice")` → path ที่รู้จัก
  (`C:\Tools\ngspice-47`), เรียก `[exe, "--version"]` timeout 10 แล้ว parse บรรทัดแรก
  ที่มี `ngspice`; เก็บ cache ด้วย `functools.lru_cache` และมี `clear_engine_cache()`
- `run_analysis`:
  1. ถ้า engine ไม่ available → คืน status `engine_missing` (ไม่สร้าง run dir)
  2. สร้าง `runs_root/<UTC %Y%m%dT%H%M%S>-<secrets.token_hex(3)>/`
  3. เขียน `circuit.cir`, `meta.json` (input, analysis, engine path/version, model sha256,
     command, started_at)
  4. `subprocess.run([exe, "-b", "-o", "run.log", "circuit.cir"], cwd=run_dir,
     capture_output=True, text=True, encoding="utf-8", errors="replace",
     timeout=timeout, shell=False)`
  5. `TimeoutExpired` → `timeout`; return code ≠ 0 → `failed`
  6. อ่านไฟล์ผล, ตรวจขนาด ≤ 20 MB, เรียก `parse_*_safe` → `parse_error` เมื่อพัง
  7. `ok`: เติม `data`, `warnings` (เช่น IC cross-check ต่าง > 2%)
- เก็บ `stdout_tail`/`stderr_tail` 40 บรรทัดท้าย (ของ ngspice ให้อ่าน `run.log` ด้วย)
- prune run เก่าเมื่อมีเกิน 50 โฟลเดอร์ (`shutil.rmtree`)

- [ ] **Step 4: เพิ่ม integration test ที่ข้ามได้**

```python
@unittest.skipUnless(spice_engine.locate_engine()["available"], "ngspice not installed")
class TestRealEngine(unittest.TestCase):
    def test_dc_run_matches_reference_within_twenty_percent(self):
        result = spice_engine.run_analysis(dict(spice_engine.CIRCUIT_DEFAULTS), "dc")
        self.assertEqual(result["status"], "ok")
        data = result["data"]
        self.assertAlmostEqual(data["i_c_a"], 1.45e-3, delta=0.3e-3)
        self.assertGreater(data["v_ce_v"], 5.0)
```

- [ ] **Step 5: รันเทสทั้งหมดและ commit**

Run: `.\.venv\Scripts\python.exe -m unittest test_spice_engine -v`
Expected: PASS (integration test ผ่านถ้าติดตั้ง ngspice แล้ว)

```powershell
git add bjt_bias/spice_engine.py test_spice_engine.py
git commit -m "feat: run ngspice with timeout, run directories and error contract"
```

---

### Task 6: SVG plots จาก array จริง

**Files:**
- Create: `bjt_bias/plots.py`
- Test: `test_plots.py`

**Interfaces:**
- Produces:
  - `bode_svg(freq_hz, gain_db, phase_deg, *, run_id="", width=720) -> str`
  - `transient_svg(time_s, vin_v, vout_v, *, run_id="", width=720) -> str`
  - ทั้งคู่ raise `ValueError` เมื่อ list ว่างหรือยาวไม่เท่ากัน

- [ ] **Step 1: เขียนเทส**

```python
class TestPlots(unittest.TestCase):
    def test_bode_has_axes_units_and_run_id(self):
        svg = plots.bode_svg([10, 100, 1000], [4.8, 5.0, 5.1], [178, 179, 179.5],
                             run_id="abc123")
        for fragment in ("Frequency (Hz)", "Gain (dB)", "Phase (deg)",
                         "abc123", "<path"):
            self.assertIn(fragment, svg)

    def test_bode_changes_with_data(self):
        a = plots.bode_svg([10, 1000], [0, 5], [180, 180], run_id="r1")
        b = plots.bode_svg([10, 1000], [0, 15], [180, 180], run_id="r1")
        self.assertNotEqual(a, b)

    def test_transient_has_two_traces_and_units(self):
        svg = plots.transient_svg([0, 1e-3, 2e-3], [0, 0.01, 0], [0, -0.018, 0],
                                  run_id="t1")
        self.assertIn("Time (ms)", svg)
        self.assertIn("mV", svg)
        self.assertIn("Vin", svg)
        self.assertIn("Vout", svg)

    def test_empty_data_rejected(self):
        with self.assertRaises(ValueError):
            plots.bode_svg([], [], [])
        with self.assertRaises(ValueError):
            plots.transient_svg([0, 1], [0], [0, 1])
```

- [ ] **Step 2: รันให้ fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_plots -v`
Expected: FAIL — ไม่มีโมดูล `bjt_bias.plots`

- [ ] **Step 3: implement**

- viewBox `0 0 {width} {height}`, margin ซ้าย 64 ขวา 24 บน 24 ล่าง 44
- Bode: panel บน (magnitude) 60% สูง, panel ล่าง (phase) 40%, แกน x log10
  ร่วมกัน, tick 10/100/1k/10k/100k/1M, phase ช่วง −180..180
- Transient: x เป็น ms, y เป็น mV, `vin` เส้นประ (`stroke-dasharray`), `vout` เส้นทึบ
- ถ้าจุด > 1200 ให้ลดแบบ min/max ต่อ bucket ก่อนวาด (ข้อมูลเต็มไม่ถูกแก้)
- `<desc>` ต้องมี `run {run_id}, {n} points, max/min` เพื่อให้ตรวจย้อนได้

- [ ] **Step 4: รันเทสและ commit**

Run: `.\.venv\Scripts\python.exe -m unittest test_plots -v`
Expected: PASS

```powershell
git add bjt_bias/plots.py test_plots.py
git commit -m "feat: render bode and transient SVG from simulation arrays"
```

---

### Task 7: Validation และ dispatch ใน `app.py`

**Files:**
- Modify: `bjt_bias/app.py`
- Test: `test_spice_app.py`

**Interfaces:**
- Produces:
  - `ANALYSES = (("analytical","Analytical DC only"),("dc","Run SPICE DC"),("ac","Run AC sweep"),("tran","Run Transient"))`
  - `_resolve_analysis(raw) -> (analysis, error)`
  - `_read_source(form, analysis) -> (values, parsed, errors)`
  - `_spice_circuit(parsed, source) -> dict`
  - `run_spice_simulation(circuit: dict, analysis: str) -> dict` — wrapper บาง ๆ
    รอบ `spice_engine.run_analysis` เพื่อให้เทส patch ได้
  - `engine_status() -> dict` (ห่อ `spice_engine.locate_engine`)
  - `page_context(...)` รับ keyword เพิ่ม: `analysis`, `analysis_options`, `source_fields`,
    `source_values`, `engine`, `spice`, `spice_plots`
- Consumes: `spice_engine.run_analysis`, `plots.bode_svg`, `plots.transient_svg`

- [ ] **Step 1: เขียนเทส**

```python
class TestAnalysisValidation(unittest.TestCase):
    def test_missing_analysis_means_analytical(self):
        self.assertEqual(app_module._resolve_analysis(None), ("analytical", None))

    def test_unknown_analysis_rejected(self):
        analysis, error = app_module._resolve_analysis("noise")
        self.assertEqual(analysis, "analytical")
        self.assertIn("Unknown analysis", error)

    def test_dc_ignores_source_fields(self):
        values, parsed, errors = app_module._read_source(
            {"amplitude_mv": "0", "frequency_hz": "0"}, "dc")
        self.assertEqual((values, parsed, errors), ({}, {}, []))

    def test_tran_rejects_zero_amplitude_and_frequency(self):
        _, _, errors = app_module._read_source(
            {"amplitude_mv": "0", "frequency_hz": "0"}, "tran")
        self.assertEqual(len(errors), 2)

    def test_tran_rejects_too_slow_frequency(self):
        _, _, errors = app_module._read_source(
            {"amplitude_mv": "10", "frequency_hz": "1"}, "tran")
        self.assertIn("5 cycles", errors[0])

    def test_ac_rejects_reversed_sweep(self):
        _, _, errors = app_module._read_source(
            {"ac_start_hz": "1000", "ac_stop_hz": "10", "ac_points_dec": "20"}, "ac")
        self.assertTrue(any("greater than" in e for e in errors))
```

```python
class TestRouteDispatch(unittest.TestCase):
    def setUp(self):
        self.client = app_module.create_app().test_client()
        self.form = {"mode": "divider", "vcc": "12", "r1": "100", "r1_unit": "kohm",
                     "r2": "22", "r2_unit": "kohm", "rc": "2.2", "rc_unit": "kohm",
                     "re": "1", "re_unit": "kohm", "beta": "100", "vbe": "0.7"}

    def test_default_post_never_calls_engine(self):
        with mock.patch.object(app_module, "run_spice_simulation",
                               side_effect=AssertionError("engine called")):
            body = self.client.post("/", data=self.form).get_data(as_text=True)
        self.assertIn("1.230", body)

    def test_spice_in_fixed_mode_is_rejected(self):
        body = self.client.post("/", data={**self.form, "mode": "fixed", "rb": "1",
                                           "rb_unit": "mohm", "analysis": "dc"}
                                ).get_data(as_text=True)
        self.assertIn("Voltage Divider reference only", body)

    def test_engine_missing_shows_status_without_plots(self):
        with mock.patch.object(app_module, "run_spice_simulation",
                               return_value=FAKE_ENGINE_MISSING):
            body = self.client.post("/", data={**self.form, "analysis": "dc"}
                                    ).get_data(as_text=True)
        self.assertIn("ngspice not found", body)
        self.assertNotIn('class="spice-plot"', body)

    def test_ok_dc_shows_both_provenances_and_delta(self):
        with mock.patch.object(app_module, "run_spice_simulation",
                               return_value=FAKE_DC_OK):
            body = self.client.post("/", data={**self.form, "analysis": "dc"}
                                    ).get_data(as_text=True)
        self.assertIn("ANALYTICAL", body)
        self.assertIn("SPICE", body)
        for text in ("1.450", "Delta", "2N3904", "run-ok-1"):
            self.assertIn(text, body)
```

`FAKE_ENGINE_MISSING` / `FAKE_DC_OK` เป็น dict หน้าตาเหมือนผล `run_analysis`
(ประกาศในไฟล์เทส พร้อม `data` ตามสัญญา Task 5)

- [ ] **Step 2: รันให้ fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_spice_app -v`
Expected: FAIL — ไม่มี `_resolve_analysis`

- [ ] **Step 3: implement**

- `_resolve_analysis`: `None`/ว่าง → analytical; รู้จัก → ค่านั้น; อื่น → `(analytical, "Unknown analysis: '<raw>'.")`
- `_read_source`: ตารางตาม design ข้อ 7; ตรวจเฉพาะ analysis; ใช้ `parse_number`
  แล้วเทียบช่วง; ข้อความ error ระบุชื่อช่อง + ช่วง
- `_spice_circuit`: เอา `vcc, r1, r2, rc, re` จาก `parsed` + ค่าคงที่ `rl=10e3, cin=cout=10e-6`
  + `source` (ถ้า ac/tran ไม่ได้ส่งมาใช้ค่า default ของ `CIRCUIT_DEFAULTS`)
- `run_spice_simulation`: เรียก `spice_engine.run_analysis(circuit, analysis)` แล้วถ้า ok และ analysis
  เป็น `ac`/`tran` สร้าง `spice_plots` ด้วย `plots.bode_svg`/`plots.transient_svg`
- `engine_status`: ห่อ `locate_engine()` เพื่อให้เทส patch ได้
- route: เพิ่มการอ่าน `analysis`, `source`, ตรวจ mode/analysis, เรียก `run_spice_simulation`
  ผ่าน helper เฉพาะเมื่อไม่มี error และ analysis เป็น SPICE, ส่งทุกอย่างเข้า `page_context`

- [ ] **Step 4: รันเทสใหม่ + เทสเดิมทั้งหมด**

Run: `.\.venv\Scripts\python.exe -m unittest test_spice_app -v`
Expected: PASS

Run: `.\.venv\Scripts\python.exe -m unittest discover -v`
Expected: PASS ทุกข้อ (62 เดิม + ใหม่)

- [ ] **Step 5: commit**

```powershell
git add bjt_bias/app.py test_spice_app.py
git commit -m "feat: dispatch analytical and spice analyses with validated inputs"
```

---

### Task 8: UI — engine bar, ปุ่ม Run, SPICE panel

**Files:**
- Modify: `bjt_bias/templates/index.html`
- Modify: `bjt_bias/static/style.css`
- Test: `test_spice_app.py`

**Interfaces:**
- Consumes: context จาก Task 7 (`analysis`, `analysis_options`, `source_fields`, `engine`, `spice`, `spice_plots`)

- [ ] **Step 1: เขียนเทส DOM**

```python
class TestSpiceUi(unittest.TestCase):
    def setUp(self):
        self.client = app_module.create_app().test_client()
        self.form = {...}  # ชุดเดียวกับ TestRouteDispatch

    def test_engine_bar_always_rendered(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('class="engine-bar', body)

    def test_spice_buttons_hidden_for_fixed_mode(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertNotIn('name="analysis" value="dc"', body)
        self.assertIn("Voltage Divider reference only", body)

    def test_spice_buttons_shown_for_divider(self):
        body = self.client.get("/").get_data(as_text=True)
        for value in ("dc", "ac", "tran", "analytical"):
            self.assertIn(f'name="analysis" value="{value}"', body)

    def test_ok_ac_shows_svg_and_units(self):
        with mock.patch.object(app_module, "run_spice_simulation",
                               return_value=FAKE_AC_OK):
            body = self.client.post("/", data={**self.form, "analysis": "ac"}
                                    ).get_data(as_text=True)
        self.assertIn('class="spice-plot"', body)
        self.assertIn("Gain (dB)", body)
        self.assertIn("Phase (deg)", body)
```

- [ ] **Step 2: รันให้ fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_spice_app.TestSpiceUi -v`
Expected: FAIL

- [ ] **Step 3: แก้เทมเพลต**

- ใต้ `<header>`: engine bar — ถ้า `engine.available` แสดง `ngspice {{ engine.version }}`
  + path (เขียว) ไม่งั้นแสดง `ngspice not found` + วิธีติดตั้ง (แดง) พร้อมลิงก์ README
- กลุ่ม "Source & Sweep" ใต้ field-list: ฟิลด์ `amplitude_mv`, `frequency_hz`,
  `ac_start_hz`, `ac_stop_hz`, `ac_points_dec` พร้อม hint ว่าใช้กับ analysis ไหน
- ปุ่ม: `Analytical DC only` (ค่าเริ่มต้น), `Run SPICE DC`, `Run AC sweep`,
  `Run Transient` โดยตั้ง `name="analysis" value="..."` ที่ตัวปุ่ม
- ปุ่ม SPICE ทั้งสามห่อด้วย `{% if mode == "divider" %}`; โหมดอื่นแสดงข้อความ
  "SPICE is available for the Voltage Divider reference only"
- Panel ผลลัพธ์: คงตาราง analytical เดิม + badge `ANALYTICAL · bias.py`
- Panel SPICE (แสดงเมื่อ `spice`): badge `SPICE · ngspice {{ spice.engine.version }} ·
  run {{ spice.run_id }}`; ถ้า `spice.status == "ok"` แสดงตารางค่าตาม analysis,
  กราฟ `{{ spice_plots.bode|safe }}` / `transient`, และ `<details>` netlist + command
  + log tail; ถ้าไม่ ok แสดง error card ตาม status และ **ไม่แสดงกราฟ**
- DC compare table: `Quantity | Analytical | SPICE (.op) | Delta`
- ห้ามแตะ h1/title/"Week 2 Goal"

- [ ] **Step 4: เพิ่ม CSS**

`.engine-bar`, `.engine-bar.ok`, `.engine-bar.bad`, `.provenance-badge`,
`.source-group`, `.spice-plot svg { max-width: 100%; height: auto; }`,
`.compare-table` (เลื่อนแนวนอนได้), และ `@media (max-width: 640px)` ให้
`.source-group`, `.compare-table` เป็นคอลัมน์เดียว/เลื่อนได้

- [ ] **Step 5: รันเทสทั้งหมดและตรวจหน้าจริงด้วยตา**

Run: `.\.venv\Scripts\python.exe -m unittest discover -v`
Expected: PASS

Run: `.\start.bat` แล้วเปิด <http://127.0.0.1:5000/> ด้วย Edge
Expected: engine bar เขียว, ปุ่ม 4 ปุ่ม, กด Run SPICE DC ได้ผลจริง

- [ ] **Step 6: commit**

```powershell
git add bjt_bias/templates/index.html bjt_bias/static/style.css test_spice_app.py
git commit -m "feat: show engine status, spice panels and provenance badges"
```

---

### Task 9: Browser acceptance B1–B8 + หลักฐาน

**Files:**
- Create: `scripts/browser_acceptance_lab4.py`
- Create: `docs/evidence/lab4/b1.png` … `b8-desktop.png`, `b8-mobile.png`

**Interfaces:**
- Consumes: หน้าเว็บที่รันจาก Task 8

- [ ] **Step 1: เขียนสคริปต์**

โครงเดียวกับ `scripts/browser_acceptance.py` (Edge headless, ฟอร์ม HTML auto-submit POST,
อ่าน DOM + screenshot) เพิ่ม:
- ฟิลด์ `analysis` ใน payload ของแต่ละเคส
- ดึง `data-run-id` หรือ regex `run ([0-9]{8}T[0-9]{6}-[0-9a-f]{6})` เพื่อยืนยันว่า
  run เปลี่ยนระหว่าง B3/B6
- เก็บข้อความ error ของ B7(a) และภาพ B8 สองขนาด (`--window-size=1280,1400`
  และ `390,900`)

- [ ] **Step 2: รัน B1–B6, B7(a), B8**

Run: `.\.venv\Scripts\python.exe -m bjt_bias.app` (แยกหน้าต่าง)
Run: `.\.venv\Scripts\python.exe scripts\browser_acceptance_lab4.py`
Expected: ทุกเคสมี screenshot และค่าที่อ่านได้; B3/B6 run id ต่างกัน

- [ ] **Step 3: ทดสอบ B7(b) engine ไม่พร้อม**

Run (หน้าต่างใหม่): `$env:NGSPICE_BIN="C:\does-not-exist\ngspice.exe"; .\.venv\Scripts\python.exe -m bjt_bias.app`
Expected: engine bar แดง "ngspice not found"; กด Run SPICE DC → error card ไม่มีกราฟ
บันทึก screenshot เป็น `b7b.png` แล้วปิดเซิร์ฟเวอร์และล้าง env

- [ ] **Step 4: ตรวจ UI แบบ manual audit (แทน Impeccable)**

ไล่ checklist: อ่านค่า/หน่วยได้, ฟอร์มไม่บังคับค่าที่ไม่ใช้, error state ชัด,
กราฟไม่ถูกตัดที่ 390 px, ปุ่มไม่ล้น, contrast อ่านได้ บันทึกสิ่งที่แก้ (ถ้ามี)
และสิ่งที่ยังค้างลง `docs/validation.md`

- [ ] **Step 5: commit**

```powershell
git add scripts/browser_acceptance_lab4.py docs/evidence/lab4
git commit -m "test: add lab 04 browser acceptance evidence"
```

---

### Task 10: เอกสาร, ตาราง B1–B8 และการส่งงาน

**Files:**
- Modify: `README.md`
- Modify: `docs/validation.md`
- Create: `AGENTS.md`

- [ ] **Step 1: เขียน `docs/validation.md` ส่วน Lab 04**

คง A1–A5 เดิมไว้ทั้งส่วน แล้วเพิ่ม:
- environment: Windows 11 build 26300, Python 3.14.10, Flask 3.1.3,
  ngspice version จาก `--version`, model 2N3904 + sha256 ของ `.lib`
- ตาราง B1–B8 คอลัมน์ `Case | Method | Input | Expected/Reference | Observed |
  Evidence | Status`
- เหตุผลที่ใช้ Edge headless แทน Playwright MCP และ manual audit แทน Impeccable
- ค่า reference ของ AC/Transient พร้อมสมการ และหมายเหตุว่า analytical ใช้สมมติฐาน
  β/VBE คงที่ จึงไม่ต้องเท่ากับ SPICE

- [ ] **Step 2: เขียน `AGENTS.md`**

กฎ: ห้าม fabricate ผล, ห้าม hard-code กราฟ, ห้ามแตะ `bias.py`, ห้าม `shell=True`,
ต้องมี timeout, ต้องบันทึก NOT RUN ตามจริง, ที่มาของ model, วิธีรัน acceptance,
และคำสั่งที่ใช้ตรวจ (`unittest discover`, `scripts/browser_acceptance_lab4.py`)

- [ ] **Step 3: อัปเดต `README.md`**

เพิ่ม: วิธีติดตั้ง ngspice (portable + `NGSPICE_BIN`), วิธีรัน Lab 04, ตาราง analysis
และจุดวัด Vin, dependency (ยังมีแค่ Flask), tested environment, repo URL,
commit SHA ของ Lab 04, AI provenance (ไฟล์/ฟังก์ชันที่ AI เขียน vs นักศึกษาตรวจ),
ลิงก์ `docs/validation.md` และ `AGENTS.md`

- [ ] **Step 4: ตรวจขั้นสุดท้าย**

Run: `.\.venv\Scripts\python.exe -m unittest discover -v`
Expected: PASS ทุกข้อ

Run: `git diff` และ `git diff --staged`
Expected: ไม่มี `.venv`, `.env`, `runs/`, ไบนารี ngspice หรือ credential

- [ ] **Step 5: commit และ push**

```powershell
git add README.md AGENTS.md docs/validation.md
git commit -m "docs: record lab 04 spice validation and submission details"
git push origin master:main
```

---

## Self-Review Notes

- Spec §1–§13 ครอบด้วย Task 2–8; §14 (B1–B8) ครอบด้วย Task 9–10
- ชื่อฟังก์ชันที่ใช้ซ้ำ: `run_analysis`, `parse_op/ac/tran`, `bode_svg`, `transient_svg`,
  `_resolve_analysis`, `_read_source`, `_spice_circuit`, `run_spice_simulation`, `engine_status`
- Review Focus ทั้ง 6 ข้อมีเทสอยู่ใน Task 4, 5, 6, 7, 9
- ไม่มี task ใดแก้ `bjt_bias/bias.py`
