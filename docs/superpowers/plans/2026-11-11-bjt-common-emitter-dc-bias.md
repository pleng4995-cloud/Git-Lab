# BJT Common-Emitter DC Bias Web App — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flask web app ที่รับค่าไบอัส 7 ตัวของ BJT common-emitter แล้วรายงาน DC operating point พร้อมหน่วย เตือน region และพิสูจน์ผลด้วยการคำนวณอิสระอีกวิธีที่แสดงเทียบกันบนหน้าเว็บ

**Architecture:** `bjt_bias/bias.py` เป็น pure Python engineering logic (ไม่มี Flask) ประกอบจาก 3 หน่วยที่ทดสอบแยกได้ — linear solver, Method 1 (Thevenin sequential), Method 2 (nodal KCL) — แล้ว `analyze_bias()` รวมผล จัด region และสร้าง verification block. `bjt_bias/app.py` เป็นชั้น Flask บาง ๆ ที่แปลง string → number, เรียก `analyze_bias()`, แล้วส่ง dict ให้ template

**Tech Stack:** Python 3.14.10, Flask 3.x, `unittest` (stdlib), vanilla HTML/CSS

**Spec:** `docs/superpowers/specs/2026-11-11-bjt-common-emitter-dc-bias-design.md`

## Global Constraints

- dependency ทั้งโปรเจกต์มีเพียง `flask` (pin เวอร์ชันจริงหลังติดตั้ง) — ห้ามเพิ่ม numpy/scipy/pytest
- เทสใช้ `unittest` เท่านั้น รันด้วย `python -m unittest`
- ทุกคำสั่งรันจาก repo root `C:\Phatcharakan\GitLab1` ด้วย `.\.venv\Scripts\python.exe`
- ห้ามแก้ `electrical.py` หรือ `test_electrical.py` — โค้ดใหม่ทั้งหมดอยู่ใน `bjt_bias/` และไฟล์เทสใหม่ที่ root
- ค่าคงที่: `VCE_SAT_V = 0.2`, `AGREEMENT_TOLERANCE = 1e-6`, ช่วง VBE ที่สมจริง `0.5–0.9 V`
- กฎ region ตามลำดับ: `i_b_a <= 0` → `cutoff`; `v_ce_v < 0.2` → `saturation`; ไม่เช่นนั้น `active`
- Method 2 **ห้ามใช้ `V_BB` หรือ `R_B`** — ต้องแก้จากระบบสมการ KCL เท่านั้น
- `bias.py` รับเฉพาะ `int`/`float` (ไม่รับ string); การแปลง string เป็นหน้าที่ของ route
- การแสดงผล: ทศนิยม 3 ตำแหน่ง, `I_B` หน่วย µA, `I_C`/`I_E` หน่วย mA, แรงดันหน่วย V
- commit message ขึ้นต้นด้วย `feat:` / `test:` / `docs:` / `chore:` ตามประวัติ repo
- ห้าม commit ไฟล์ untracked เดิม: `B6811938-Phatcharakan_G01.zip`, `git-evidence.pdf`, `github-repo-url.txt.txt`, `reflection.txt.txt`

## Review Focus

1. **ตัวเลขที่ผู้ใช้พิมพ์จริง** — `12,5` (ลูกน้ำทศนิยม), ` 47k ` (มีช่องว่าง), `2.2 k` → ต้องได้ข้อความ error ที่อ่านรู้เรื่องหรือ parse ผ่าน ไม่ใช่ traceback / 500
2. **กด submit โดยไม่กรอกอะไร** — ฟอร์มว่างทั้ง 7 ช่อง → แสดง error ครบทุกช่อง ไม่ crash
3. **POST ที่ไม่มีคีย์ครบ** (curl / form บางส่วน) — ต้องไม่เกิด `KeyError` เป็น 500
4. **ค่าขนาดสุดขั้ว** — `RC=1e12`, `RE=1e-6`, `beta=1e9` → ยังคำนวณและ render ได้ ไม่ overflow
5. **Saturation ที่ `V_CE` ติดลบ** — ต้องแสดงค่าติดลบพร้อม warning ไม่ crash และไม่ฟ้องว่า active

---

### Task 1: Branch, venv, และ commit spec ที่อนุมัติแล้ว

**Files:**
- Create: `.venv/` (gitignored), `docs/superpowers/plans/2026-11-11-bjt-common-emitter-dc-bias.md`
- Modify: `docs/superpowers/specs/2026-11-11-bjt-common-emitter-dc-bias-design.md:2` (สถานะ → อนุมัติแล้ว)

**Interfaces:**
- Consumes: nothing
- Produces: branch `feature/bjt-bias-app`, venv ที่ทุก task ถัดไปใช้

- [ ] **Step 1: สร้าง branch และ venv**

```powershell
git checkout -b feature/bjt-bias-app
python -m venv .venv
.\.venv\Scripts\python.exe --version
```

Expected: branch ใหม่ และพิมพ์ `Python 3.14.10`
ถ้า Application Control บล็อก `.venv\Scripts\python.exe` ให้รายงานทันทีและใช้ `python` ของระบบแทนทุกคำสั่ง (ห้ามเงียบ ๆ เปลี่ยน)

- [ ] **Step 2: แก้สถานะใน spec**

เปลี่ยนบรรทัด `สถานะ: รออนุมัติ` เป็น `สถานะ: อนุมัติแล้ว (2026-11-11)`

- [ ] **Step 3: Commit spec + plan**

```powershell
git add docs/superpowers
git commit -m "docs: add approved design and implementation plan for BJT bias app"
```

---

### Task 2: Linear system solver

**Files:**
- Create: `bjt_bias/__init__.py`, `bjt_bias/bias.py`
- Test: `test_bjt_bias.py`

**Interfaces:**
- Consumes: nothing
- Produces: `solve_linear_system(a: list[list[float]], b: list[float]) -> list[float]` — แก้ `a·x = b` ด้วย Gaussian elimination + partial pivoting; raise `ValueError("Matrix must be square.")` / `ValueError("Matrix and vector sizes differ.")` / `ValueError("Matrix is singular.")`

- [ ] **Step 1: เขียนเทสที่ยังไม่ผ่าน**

```python
import unittest

from bjt_bias.bias import solve_linear_system


class TestLinearSolver(unittest.TestCase):
    def test_solves_two_by_two(self):
        self.assertEqual(solve_linear_system([[2, 1], [1, 3]], [5, 10]), [1.0, 3.0])

    def test_swaps_rows_when_pivot_is_zero(self):
        # แถวแรกมี pivot เป็น 0 ต้องสลับแถว
        solution = solve_linear_system([[0, 2], [1, 1]], [4, 3])
        self.assertAlmostEqual(solution[0], 1.0)
        self.assertAlmostEqual(solution[1], 2.0)

    def test_rejects_non_square_matrix(self):
        with self.assertRaises(ValueError):
            solve_linear_system([[1, 2, 3], [4, 5, 6]], [1, 2])

    def test_rejects_mismatched_vector(self):
        with self.assertRaises(ValueError):
            solve_linear_system([[1, 0], [0, 1]], [1, 2, 3])

    def test_rejects_singular_matrix(self):
        with self.assertRaises(ValueError):
            solve_linear_system([[1, 1], [1, 1]], [1, 2])
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_bias -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bjt_bias'`

- [ ] **Step 3: สร้างแพ็กเกจและ implement `solve_linear_system`**

`bjt_bias/__init__.py` เป็นไฟล์ว่าง (หรือ docstring บรรทัดเดียว)
ใน `bjt_bias/bias.py` เขียน `solve_linear_system(a, b)` — ก๊อปเมทริกซ์และเวกเตอร์ก่อนแก้ (ห้าม mutate input), วนคอลัมน์หาแถวที่มีค่าสัมบูรณ์มากสุดแล้วสลับ, ถ้า pivot เป็น 0 ให้ raise `"Matrix is singular."`, กำจัดตัวแปรแล้วแทนค่าย้อนกลับ

- [ ] **Step 4: รันให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_bias -v`
Expected: PASS 5 tests

- [ ] **Step 5: Commit**

```powershell
git add bjt_bias test_bjt_bias.py
git commit -m "feat: add linear system solver with partial pivoting"
```

---

### Task 3: Validation + Method 1

**Files:**
- Modify: `bjt_bias/bias.py`
- Test: `test_bjt_bias.py`

**Interfaces:**
- Consumes: nothing จาก Task 2
- Produces:
  - `solve_method1(vcc: float, r1: float, r2: float, rc: float, re: float, beta: float, vbe: float) -> dict[str, float]` — คืน dict ที่มีคีย์ `i_b_a, i_c_a, i_e_a, v_b_v, v_e_v, v_c_v, v_ce_v` (SI units) และ **ไม่ validate** (ผู้เรียกต้อง validate ก่อน)
  - `validate_inputs(vcc, r1, r2, rc, re, beta, vbe) -> None` — raise `ValueError` ตาม §5.5 ของ spec

- [ ] **Step 1: เขียนเทสที่ยังไม่ผ่าน**

```python
from bjt_bias.bias import solve_method1, validate_inputs

GOLDEN = dict(vcc=12.0, r1=47000.0, r2=10000.0, rc=2200.0, re=1000.0, beta=150.0, vbe=0.7)


class TestValidation(unittest.TestCase):
    def test_accepts_golden_inputs(self):
        validate_inputs(**GOLDEN)

    def test_rejects_non_positive_supply_and_resistors(self):
        for field in ("vcc", "r1", "r2", "rc", "re", "beta"):
            for bad in (0, -5):
                with self.subTest(field=field, bad=bad):
                    with self.assertRaises(ValueError):
                        validate_inputs(**{**GOLDEN, field: bad})

    def test_rejects_non_numbers(self):
        for bad in ("12", None, True, float("nan"), float("inf")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate_inputs(**{**GOLDEN, "vcc": bad})

    def test_rejects_vbe_outside_supply(self):
        for bad in (-0.1, 12.0, 13.0):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validate_inputs(**{**GOLDEN, "vbe": bad})


class TestMethod1(unittest.TestCase):
    def test_golden_operating_point(self):
        result = solve_method1(**GOLDEN)
        self.assertAlmostEqual(result["i_b_a"], 8.8245e-6, delta=1e-9)
        self.assertAlmostEqual(result["i_c_a"], 1.323675e-3, delta=1e-9)
        self.assertAlmostEqual(result["i_e_a"], 1.3325e-3, delta=1e-9)
        self.assertAlmostEqual(result["v_b_v"], 2.0325, delta=1e-6)
        self.assertAlmostEqual(result["v_e_v"], 1.3325, delta=1e-6)
        self.assertAlmostEqual(result["v_c_v"], 9.087915, delta=1e-6)
        self.assertAlmostEqual(result["v_ce_v"], 7.755415, delta=1e-6)
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_bias -v`
Expected: FAIL — `ImportError: cannot import name 'validate_inputs'`

- [ ] **Step 3: Implement `_finite_number`, `_positive_number`, `validate_inputs`, `solve_method1`**

- `_finite_number(value, name)`: `bool` หรือไม่ใช่ `int`/`float` → `ValueError(f"{name} must be a number.")`; `OverflowError`/`math.isfinite` เป็นเท็จ → `ValueError(f"{name} must be finite.")`
- `_positive_number(value, name)`: ผ่าน `_finite_number` แล้วต้อง `> 0` ไม่งั้น `ValueError(f"{name} must be a finite number greater than zero.")`
- `validate_inputs`: `vcc, r1, r2, rc, re, beta` ผ่าน `_positive_number`; `vbe` ผ่าน `_finite_number` แล้วต้อง `0 <= vbe < vcc` ไม่งั้น `ValueError("VBE must be between 0 and VCC.")`
- `solve_method1` ตามสูตรใน spec §5.2 (ใช้ `vbb`, `r_b` เป็นตัวแปรท้องถิ่น)

- [ ] **Step 4: รันให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_bias -v`
Expected: PASS 10 tests

- [ ] **Step 5: Commit**

```powershell
git add bjt_bias/bias.py test_bjt_bias.py
git commit -m "feat: validate bias inputs and add Thevenin bias calculation"
```

---

### Task 4: Method 2 (nodal) + agreement rule

**Files:**
- Modify: `bjt_bias/bias.py`
- Test: `test_bjt_bias.py`

**Interfaces:**
- Consumes: `solve_linear_system` (Task 2), `solve_method1` (Task 3)
- Produces:
  - `solve_method2(vcc, r1, r2, rc, re, beta, vbe) -> dict[str, float]` — คีย์ชุดเดียวกับ `solve_method1`
  - `OPERATING_POINT_FIELDS: tuple[tuple[str, str, str, float], ...]` — `(key, symbol, unit, display_scale)` เรียงตาม `i_b_a, i_c_a, i_e_a, v_b_v, v_e_v, v_c_v, v_ce_v`; unit คือ `µA, mA, mA, V, V, V, V`; scale คือ `1e6, 1e3, 1e3, 1.0, 1.0, 1.0, 1.0`
  - `max_normalized_difference(left: dict, right: dict) -> float` — `max(|a−b| / max(1, |a|, |b|))`; dict ว่างหรือทั้งคู่เป็น 0 → `0.0`

- [ ] **Step 1: เขียนเทสที่ยังไม่ผ่าน**

```python
from bjt_bias.bias import max_normalized_difference, solve_method2

SATURATING = dict(vcc=12.0, r1=47000.0, r2=10000.0, rc=10000.0, re=100.0, beta=150.0, vbe=0.7)
CUTOFF = dict(vcc=12.0, r1=47000.0, r2=2200.0, rc=2200.0, re=1000.0, beta=150.0, vbe=0.7)


class TestMethod2(unittest.TestCase):
    def test_agrees_with_method1_on_golden(self):
        diff = max_normalized_difference(solve_method1(**GOLDEN), solve_method2(**GOLDEN))
        self.assertLess(diff, 1e-6)

    def test_agrees_with_method1_on_saturation_case(self):
        diff = max_normalized_difference(solve_method1(**SATURATING), solve_method2(**SATURATING))
        self.assertLess(diff, 1e-6)

    def test_agrees_with_method1_on_cutoff_case(self):
        diff = max_normalized_difference(solve_method1(**CUTOFF), solve_method2(**CUTOFF))
        self.assertLess(diff, 1e-6)

    def test_does_not_use_divider_helpers(self):
        import inspect
        source = inspect.getsource(solve_method2)
        self.assertNotIn("vbb", source.lower())
        self.assertNotIn("r_b", source.lower())


class TestAgreementRule(unittest.TestCase):
    def test_zero_against_zero_is_agreement(self):
        zeros = {"i_b_a": 0.0, "i_c_a": 0.0}
        self.assertEqual(max_normalized_difference(zeros, dict(zeros)), 0.0)

    def test_zero_against_non_zero_does_not_divide_by_zero(self):
        self.assertEqual(max_normalized_difference({"i_b_a": 0.0}, {"i_b_a": 1e-12}), 1e-12)
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_bias -v`
Expected: FAIL — `ImportError: cannot import name 'max_normalized_difference'`

- [ ] **Step 3: Implement `solve_method2`, `OPERATING_POINT_FIELDS`, `max_normalized_difference`**

สร้างระบบ 6×6 ตามลำดับตัวแปร `[V_B, V_C, V_E, I_B, I_C, I_E]` — เมทริกซ์ A และเวกเตอร์ b ตาม spec §5.3:

```python
a = [
    [1 / r1 + 1 / r2, 0.0, 0.0, 1.0, 0.0, 0.0],
    [0.0, 1 / rc, 0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, -1 / re, 0.0, 0.0, 1.0],
    [0.0, 0.0, 0.0, -1.0, -1.0, 1.0],
    [0.0, 0.0, 0.0, -beta, 1.0, 0.0],
    [1.0, 0.0, -1.0, 0.0, 0.0, 0.0],
]
b = [vcc / r1, vcc / rc, 0.0, 0.0, 0.0, vbe]
```

แล้วแมปผลกลับเป็นคีย์เดียวกับ `solve_method1` (`v_ce_v = v_c_v - v_e_v`)

- [ ] **Step 4: รันให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_bias -v`
Expected: PASS 17 tests

- [ ] **Step 5: Commit**

```powershell
git add bjt_bias/bias.py test_bjt_bias.py
git commit -m "feat: add independent nodal analysis and agreement check"
```

---

### Task 5: Region classification + `analyze_bias`

**Files:**
- Modify: `bjt_bias/bias.py`
- Test: `test_bjt_bias.py`

**Interfaces:**
- Consumes: `validate_inputs`, `solve_method1`, `solve_method2`, `max_normalized_difference`, `OPERATING_POINT_FIELDS`
- Produces:
  - `classify_region(operating_point: dict, vcc: float, r1: float, r2: float) -> tuple[str, list[str]]` — คืน `(region, warnings)`
  - `cutoff_operating_point(vcc: float, r1: float, r2: float) -> dict[str, float]` — `i_b=i_c=i_e=0`, `v_e=0`, `v_b=vcc*r2/(r1+r2)`, `v_c=vcc`, `v_ce=vcc`
  - `analyze_bias(vcc, r1, r2, rc, re, beta, vbe) -> dict` โดยคืน

```python
{
    "operating_point": {7 keys ตาม OPERATING_POINT_FIELDS},
    "region": "active" | "cutoff" | "saturation",
    "warnings": [str, ...],
    "verification": {
        "method1": {7 keys},
        "method2": {7 keys},
        "max_difference": float,
        "agrees": bool,
    },
}
```

- [ ] **Step 1: เขียนเทสที่ยังไม่ผ่าน**

```python
from bjt_bias.bias import analyze_bias, cutoff_operating_point


class TestRegions(unittest.TestCase):
    def test_golden_case_is_active(self):
        result = analyze_bias(**GOLDEN)
        self.assertEqual(result["region"], "active")
        self.assertEqual(result["warnings"], [])
        self.assertTrue(result["verification"]["agrees"])
        self.assertAlmostEqual(result["operating_point"]["v_ce_v"], 7.755415, delta=1e-6)

    def test_cutoff_reports_physical_values(self):
        result = analyze_bias(**CUTOFF)
        self.assertEqual(result["region"], "cutoff")
        self.assertEqual(result["operating_point"]["i_c_a"], 0.0)
        self.assertEqual(result["operating_point"]["v_c_v"], 12.0)
        self.assertEqual(result["operating_point"]["v_ce_v"], 12.0)
        self.assertAlmostEqual(result["operating_point"]["v_b_v"], 12 * 2200 / 49200, delta=1e-9)
        self.assertTrue(any("cutoff" in w.lower() for w in result["warnings"]))

    def test_saturation_warns_and_keeps_linear_values(self):
        result = analyze_bias(**SATURATING)
        self.assertEqual(result["region"], "saturation")
        self.assertLess(result["operating_point"]["v_ce_v"], 0.2)
        self.assertTrue(any("saturation" in w.lower() for w in result["warnings"]))

    def test_vbe_outside_plausible_range_warns_but_computes(self):
        result = analyze_bias(**{**GOLDEN, "vbe": 0.95})
        self.assertEqual(result["region"], "active")
        self.assertTrue(any("0.5" in w and "0.9" in w for w in result["warnings"]))

    def test_extreme_but_valid_magnitudes_do_not_raise(self):
        result = analyze_bias(**{**GOLDEN, "rc": 1e12, "re": 1e-6, "beta": 1e9})
        self.assertIn(result["region"], {"active", "cutoff", "saturation"})
        self.assertTrue(result["verification"]["agrees"])

    def test_vbb_equal_to_vbe_does_not_divide_by_zero(self):
        result = analyze_bias(vcc=12.0, r1=113000.0, r2=7000.0, rc=2200.0, re=1000.0, beta=150.0, vbe=0.7)
        self.assertIn(result["region"], {"cutoff", "active"})


class TestCutoffOperatingPoint(unittest.TestCase):
    def test_cutoff_has_no_current(self):
        point = cutoff_operating_point(12.0, 47000.0, 2200.0)
        self.assertEqual(point["i_b_a"], 0.0)
        self.assertEqual(point["i_e_a"], 0.0)
        self.assertEqual(point["v_e_v"], 0.0)
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_bias -v`
Expected: FAIL — `ImportError: cannot import name 'analyze_bias'`

- [ ] **Step 3: Implement**

- `classify_region`: `i_b_a <= 0` → `("cutoff", ["Transistor is in cutoff (I_B <= 0): no collector current flows."])`; `v_ce_v < VCE_SAT_V` → `("saturation", ["Transistor is in saturation (V_CE < 0.2 V): active-mode equations are not valid."])`; ไม่เช่นนั้น `("active", [])`
- `cutoff_operating_point` ตามสูตรใน spec §5.4
- `analyze_bias`: `validate_inputs(...)` → คำนวณ `method1`, `method2` → `classify_region(method1, ...)` → ถ้า region เป็น cutoff ใช้ `cutoff_operating_point` ไม่งั้นใช้ `method1` → เติม warning เรื่อง VBE ถ้า `vbe < 0.5 or vbe > 0.9` (ข้อความต้องมีทั้ง `0.5` และ `0.9`) → คำนวณ `max_difference`/`agrees` และถ้าไม่ตรงกันให้เติม warning

- [ ] **Step 4: รันให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_bias -v`
Expected: PASS 25 tests

- [ ] **Step 5: Commit**

```powershell
git add bjt_bias/bias.py test_bjt_bias.py
git commit -m "feat: classify bias region and compose full analysis"
```

---

### Task 6: Flask app, template, CSS, route tests

**Files:**
- Create: `bjt_bias/app.py`, `bjt_bias/templates/index.html`, `bjt_bias/static/style.css`, `requirements.txt`, `test_bjt_app.py`
- Modify: nothing

**Interfaces:**
- Consumes: `analyze_bias`, `OPERATING_POINT_FIELDS` (Task 5)
- Produces:
  - `create_app() -> flask.Flask`
  - `parse_resistance(text: str, label: str) -> float` — รับ `47000`, `47k`, `47K`, `2.2k`, `1M`, ยอมรับช่องว่างหัวท้าย; ผิดรูป → `ValueError(f"{label} must be a number in ohms (e.g. 47000, 47k).")`
  - `format_value(value: float, scale: float) -> str` — `f"{value * scale:.3f}"`
  - module-level `app = create_app()` และ `if __name__ == "__main__": app.run(debug=True)`
  - เทมเพลตได้ context: `fields` (`list[dict]` ที่มี `name,label,unit,value`), `errors` (`list[str]`), `result` (`dict|None`), `op_fields`, `fmt`

- [ ] **Step 1: เขียนเทสที่ยังไม่ผ่าน**

```python
import unittest

from bjt_bias.app import create_app, format_value, parse_resistance

VALID_FORM = {
    "vcc": "12", "r1": "47k", "r2": "10k",
    "rc": "2.2k", "re": "1k", "beta": "150", "vbe": "0.7",
}


class TestParsing(unittest.TestCase):
    def test_accepts_engineering_suffixes(self):
        self.assertEqual(parse_resistance("47000", "R1"), 47000.0)
        self.assertEqual(parse_resistance("47k", "R1"), 47000.0)
        self.assertEqual(parse_resistance("47K", "R1"), 47000.0)
        self.assertEqual(parse_resistance("2.2k", "R1"), 2200.0)
        self.assertEqual(parse_resistance("1M", "R1"), 1e6)
        self.assertEqual(parse_resistance(" 47k ", "R1"), 47000.0)

    def test_rejects_bad_input(self):
        for bad in ("abc", "", "1,5k"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_resistance(bad, "R1")

    def test_formats_three_decimals(self):
        self.assertEqual(format_value(1.323675e-3, 1e3), "1.324")
        self.assertEqual(format_value(8.8245e-6, 1e6), "8.825")


class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_renders_seven_inputs(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for name in VALID_FORM:
            self.assertIn(f'name="{name}"', response.get_data(as_text=True))

    def test_post_valid_shows_operating_point_and_comparison(self):
        response = self.client.post("/", data=VALID_FORM)
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("1.324", body)
        self.assertIn("7.755", body)
        self.assertIn("active", body)
        self.assertIn("Method 1", body)
        self.assertIn("Method 2", body)

    def test_post_invalid_shows_error_and_keeps_input(self):
        response = self.client.post("/", data={**VALID_FORM, "r1": "0"})
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("greater than zero", body)
        self.assertNotIn("Traceback", body)

    def test_post_cutoff_shows_cutoff(self):
        response = self.client.post("/", data={**VALID_FORM, "r2": "2.2k"})
        self.assertIn("cutoff", response.get_data(as_text=True).lower())

    def test_post_with_comma_decimal_gives_friendly_error(self):
        response = self.client.post("/", data={**VALID_FORM, "vbe": "0,7"})
        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("must be a number", body)

    def test_post_empty_form_does_not_crash(self):
        response = self.client.post("/", data={})
        self.assertEqual(response.status_code, 200)
        self.assertIn("must be a number", response.get_data(as_text=True))

    def test_post_missing_fields_does_not_crash(self):
        response = self.client.post("/", data={"vcc": "12"})
        self.assertEqual(response.status_code, 200)
```

- [ ] **Step 2: รันให้เห็นว่า fail**

Run: `.\.venv\Scripts\python.exe -m pip install "flask>=3.0,<4"` แล้ว `.\.venv\Scripts\python.exe -m unittest test_bjt_app -v`
Expected: ติดตั้งสำเร็จ แล้ว FAIL — `ModuleNotFoundError: No module named 'bjt_bias.app'`
(ถ้า `pip` ถูกบล็อก ให้รายงานก่อนดำเนินการต่อ)

- [ ] **Step 3: Implement app.py**

- `FIELDS = (("vcc", "VCC", "V", "12"), ("r1", "R1", "Ω", "47k"), ("r2", "R2", "Ω", "10k"), ("rc", "RC", "Ω", "2.2k"), ("re", "RE", "Ω", "1k"), ("beta", "beta", "", "150"), ("vbe", "VBE", "V", "0.7"))`
- `parse_resistance`: strip, ถ้าลงท้ายด้วย `k`/`K` คูณ 1e3, `M` คูณ 1e6, แล้ว `float()`; จับ `ValueError`/`OverflowError` ทั้งหมดแล้ว raise ข้อความของเราเอง
- helper `_parse_voltage_or_beta(text, label)` ที่คืน `float(text)` หรือ raise `ValueError(f"{label} must be a number.")`
- route `"/"` รับ `GET`/`POST`: `GET` → render ด้วยค่า default จาก `FIELDS`; `POST` → อ่าน `request.form.get(name, "")`, parse ทีละช่องเก็บ error ไว้ใน list (parse ครบทุกช่องก่อนตัดสิน ไม่หยุดที่ช่องแรก), ถ้ามี error → render ฟอร์มพร้อมค่าที่ผู้ใช้พิมพ์และ `result=None`, ถ้าไม่มี → `analyze_bias(...)` แล้ว render ผล; จับ `ValueError` จาก `analyze_bias` เป็น error list เช่นกัน
- ทุกกรณีตอบ 200

- [ ] **Step 4: เขียน template และ CSS**

`index.html` ต้องมี: `<form method="post">` วน `fields` สร้าง `<input name="{{ f.name }}" value="{{ f.value }}">` พร้อม label/unit; block แสดง `errors`; เมื่อมี `result` แสดง (ก) ตาราง operating point จาก `op_fields` + `fmt`, (ข) badge region ที่มีคำว่า `active`/`cutoff`/`saturation`, (ค) ตาราง verification ที่มีหัวคอลัมน์ `Method 1`, `Method 2`, `Difference` และแถวต่อ `op_fields`, (ง) `warnings`
`style.css`: ฟอนต์ system, ฟอร์มเป็น grid 2 คอลัมน์, ตารางมี border-collapse, badge 3 สี (เขียว/เหลือง/แดง), ความกว้างสูงสุด ~900px กึ่งกลางหน้า

- [ ] **Step 5: รันให้ผ่าน**

Run: `.\.venv\Scripts\python.exe -m unittest test_bjt_app -v`
Expected: PASS 10 tests

- [ ] **Step 6: Pin requirements และ commit**

```powershell
.\.venv\Scripts\python.exe -m pip freeze | Select-String -Pattern "^[Ff]lask=="
```

เอาเวอร์ชันที่ได้เขียนเป็น `requirements.txt` (บรรทัดเดียว เช่น `Flask==3.1.2`)

```powershell
git add bjt_bias requirements.txt test_bjt_app.py
git commit -m "feat: add Flask UI with operating point and method comparison"
```

---

### Task 7: README, รันจริงบน localhost, และ verification

**Files:**
- Modify: `README.md`
- Create: `bjt_bias/README.md` (วิธีรัน + สูตรที่ใช้)

**Interfaces:**
- Consumes: ทุกอย่างจาก Task 1–6
- Produces: หลักฐานว่าแอปรันจริงและเทสผ่าน

- [ ] **Step 1: เขียนเอกสาร**

`bjt_bias/README.md`: วิธีติดตั้ง (`python -m venv .venv`, `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`), วิธีรัน (`.\.venv\Scripts\python.exe -m bjt_bias.app`), URL `http://127.0.0.1:5000`, ตาราง input/หน่วย, สูตร Method 1, ระบบสมการ Method 2, กฎ region, และข้อจำกัด (active-mode model, ไม่มี AC)
`README.md` เดิม: เพิ่มหัวข้อสั้น ๆ ด้านล่างชี้ไปที่ `bjt_bias/` โดยไม่ลบเนื้อหาเดิม

- [ ] **Step 2: รันเทสทั้งหมด**

Run: `.\.venv\Scripts\python.exe -m unittest discover -v`
Expected: PASS ทั้ง `test_bjt_bias` และ `test_bjt_app` (35 tests) และ `test_electrical` เดิมยังผ่าน

- [ ] **Step 3: รัน server จริงและยิง request จริง**

```powershell
Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m","bjt_bias.app" -WindowStyle Hidden
Start-Sleep -Seconds 3
(Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -UseBasicParsing).StatusCode
(Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -Method POST -Body @{vcc="12";r1="47k";r2="10k";rc="2.2k";re="1k";beta="150";vbe="0.7"} -UseBasicParsing).Content | Select-String "1.324"
```

Expected: `200`, และเจอ `1.324` ใน HTML

- [ ] **Step 4: หยุด server**

```powershell
Get-Process python | Where-Object { $_.Path -like "*\.venv\*" } | Stop-Process
```

Expected: ไม่มี process ของ venv เหลือ (ตรวจด้วย `Get-Process python` อีกครั้ง)

- [ ] **Step 5: Commit และ merge**

```powershell
git add README.md bjt_bias/README.md
git commit -m "docs: document BJT bias app usage and equations"
git checkout master
git merge --no-ff feature/bjt-bias-app -m "Merge branch 'feature/bjt-bias-app'"
```

- [ ] **Step 6: Push**

```powershell
git push origin master
```

Expected: push สำเร็จ; ถ้า authentication ล้มเหลว ให้รายงานพร้อม URL ของ remote และหยุด (ห้าม force push)

---

## Self-Review

**1. Spec coverage**

| Spec section | Task |
|---|---|
| §5.2 Method 1 | 3 |
| §5.3 Method 2 + agreement rule | 2, 4 |
| §5.4 region handling | 5 |
| §5.5 validation + parsing + หน่วย R | 3, 6 |
| §6 file layout | 1–7 |
| §7 routes | 6 |
| §8 UI (4 ส่วน) | 6 |
| §9 tests | 2–6 |
| §10 verification | 7 |
| §11 git plan | 1, 7 |

ไม่มีช่องว่าง

**2. Step scan** — ทุก step มี action เดียวและผลตรวจได้; ไม่มี step ที่เป็น "handle edge cases" ลอย ๆ; ไม่มี body ของฟังก์ชันที่ signature + เทสกำหนดอยู่แล้ว ยกเว้นเมทริกซ์ 6×6 ใน Task 4 ซึ่งเป็นอัลกอริทึมที่ผู้ทำอ่านเองไม่ได้

**3. Type consistency** — `solve_method1`/`solve_method2`/`cutoff_operating_point` คืนคีย์ชุดเดียวกัน 7 ตัว; `OPERATING_POINT_FIELDS` ใช้คีย์เดียวกัน; `analyze_bias` คืน `operating_point` + `verification.method1/method2` ที่ใช้คีย์ชุดนี้; route ส่ง `op_fields`/`fmt` ตรงกับที่ template ใช้

**4. Review Focus** — แต่ละข้อมีเทสใน task ที่เป็นเจ้าของ: (1) comma decimal → Task 6, (2) empty form → Task 6, (3) missing fields → Task 6, (4) extreme magnitudes → Task 5, (5) saturation ติดลบ → Task 5

**5. Proportion** — plan ยาวกว่า spec ประมาณ 1.5 เท่า แต่ส่วนใหญ่เป็น signature/เทส ไม่ใช่ body ของโปรแกรม
