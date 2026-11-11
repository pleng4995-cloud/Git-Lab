# Design — BJT Common-Emitter DC Bias Web App (ENG29 2121)

วันที่: 2026-11-11
สถานะ: อนุมัติแล้ว (2026-11-11)
ขนาดงาน: small project (7 ไฟล์ source + 2 ไฟล์ test)

## 1. Intent / Why

แล็บสั้นของ ENG29 2121 ต้องการ **Flask web application จริง** ที่คำนวณ **DC operating point** ของวงจร
BJT Common-Emitter แบบ voltage-divider bias และ **พิสูจน์ผลด้วยการคำนวณวิศวกรรมอีกวิธีที่เป็นอิสระ**
ผู้เรียนเห็นทั้งผลลัพธ์ หน่วย และคำเตือนว่าไบอัสอยู่ใน region ใด พร้อมหลักฐานว่าเลขที่ได้ไม่ได้มาจากสูตรชุดเดียว

## 2. Goals

- รับ input 7 ค่า: `VCC`, `R1`, `R2`, `RC`, `RE`, `beta`, `VBE`
- คำนวณ DC operating point: `I_B`, `I_C`, `I_E`, `V_B`, `V_E`, `V_C`, `V_CE` พร้อมหน่วย
- Validate input อย่างชัดเจน เป็นมิตรกับผู้ใช้ (ไม่ crash, บอกว่าผิดตรงไหน)
- เตือน region: **cutoff / active / saturation**
- แสดง **Method 1** (สูตรมาตรฐาน) กับ **Method 2** (nodal analysis) เทียบกัน พร้อมส่วนต่างและสรุป PASS/FAIL
- รันบน `localhost` ได้จริง และมีเทสอัตโนมัติที่ผ่าน

## 3. Non-goals / Anti-goals

- ไม่มี AC analysis, transient, frequency response, load line graph
- ไม่มี circuit editor / schematic drawing / netlist
- ไม่มี FET, Darlington, emitter degeneration analysis, temperature sweep
- ไม่มี beta sensitivity sweep หรือ Monte Carlo
- ไม่มี database / user account / deployment (local only)
- **ไม่ re-solve วงจรใน saturation** — แค่เตือนว่าสมการ active mode ใช้ไม่ได้ (ดู §5.3)
- Anti-goal: แอปที่โชว์เลขโดยไม่มีหน่วย หรือ validate แบบเงียบ ๆ

## 4. Constraints

- Python 3.14.10, Flask 3.x (ติดตั้งผ่าน `python -m pip` เพราะ `pip.exe` ถูก Application Control บล็อก)
- ใช้ `unittest` (stdlib) ต่อจาก `test_electrical.py` เดิม — ไม่เพิ่ม dependency สำหรับเทส
- dependency ทั้งหมดมีแค่ `flask` (pin ใน `requirements.txt`)
- โค้ดใหม่แยกใน `bjt_bias/` ไม่แตะ `electrical.py` / `test_electrical.py` เดิม
- เทส logic ต้องรันได้โดยไม่ต้องมี Flask

## 5. Engineering model

### 5.1 สมมติฐาน

BJT เป็น **active-mode DC model**: `V_BE` คงที่ตาม input, `I_C = beta · I_B`, กระแส leakage ถูกมองข้าม,
`V_CE_sat = 0.2 V` เป็นค่าคงที่ในโค้ด ไม่ใช่ input

### 5.2 Method 1 — standard divider/Thevenin (sequential)

```
V_BB = VCC · R2 / (R1 + R2)
R_B  = R1 · R2 / (R1 + R2)
I_B  = (V_BB − VBE) / (R_B + (beta + 1) · RE)
I_C  = beta · I_B
I_E  = (beta + 1) · I_B
V_E  = I_E · RE
V_C  = VCC − I_C · RC
V_CE = V_C − V_E
V_B  = V_E + VBE
```

### 5.3 Method 2 — nodal analysis (independent)

สร้างระบบสมการเชิงเส้น 6 ตัวแปร (`V_B, V_C, V_E, I_B, I_C, I_E`) จาก KCL ที่แต่ละ node
โดยถือ `VBE` เป็นแหล่งจ่ายแรงดันคงที่ แล้วแก้ด้วย Gaussian elimination + partial pivoting
ที่เขียนเองใน pure Python (`_solve_linear_system`) — **คนละพีชคณิตกับ Method 1 จริง**
(ไม่ได้ผ่าน `V_BB`, `R_B` หรือการแทนค่าต่อกัน)

```
node B: (V_B − VCC)/R1 + V_B/R2 + I_B = 0
node C: (V_C − VCC)/RC + I_C = 0
node E: I_E − V_E/RE = 0
I_E = I_B + I_C
I_C = beta · I_B
V_B − V_E = VBE
```

**เกณฑ์การตรงกัน (agreement rule):** ใช้ mixed absolute/relative tolerance

```
agree(a, b)  ⇔  |a − b| ≤ 1e-6 · max(1, |a|, |b|)
```

`max(1, ...)` กันกรณีค่าศูนย์หรือค่าน้อยมาก (เช่น `V_BB == VBE` ทำให้ `I_B = 0` ทั้งสองวิธี)
จึงไม่มีการหารด้วยศูนย์ และ `0 vs 0` ถือว่าตรงกัน

### 5.4 Region handling (ลำดับการตัดสิน)

| เงื่อนไข | Region | สิ่งที่รายงาน |
|---|---|---|
| `I_B ≤ 0` | **cutoff** | operating point แบบ physical: `I_B = I_C = I_E = 0`, `V_E = 0`, `V_B = V_BB`, `V_C = VCC`, `V_CE = VCC` + เตือนว่า BJT ถูกตัด |
| `V_CE < 0.2 V` | **saturation** | ค่าจาก linear solution ตามเดิม + เตือนว่า `V_CE < VCE_sat` สมการ active mode ใช้ไม่ได้ |
| อื่น ๆ | **active** | ค่าจาก linear solution + ยืนยันว่าอยู่ใน active region |

ตารางเปรียบเทียบ Method 1 vs Method 2 ใช้ค่า **linear solution ดิบ** ทั้งสองฝั่ง (ก่อนปรับตาม region)
เพื่อให้การตรวจสอบเป็นอิสระจริง ส่วน operating point ที่รายงานใช้ค่าตาม §5.4

### 5.5 Validation rules

| เงื่อนไข | ผล |
|---|---|
| ไม่ใช่ตัวเลข / `bool` / `NaN` / `inf` | error: "must be a finite number" |
| `VCC ≤ 0` | error |
| `R1, R2, RC, RE ≤ 0` | error |
| `beta ≤ 0` | error |
| `VBE < 0` หรือ `VBE ≥ VCC` | error |
| `VBE` นอกช่วง 0.5–0.9 V | **warning** (ไม่บล็อก) — ค่าไม่สมจริงสำหรับ silicon BJT |

Validation อยู่ที่ `bjt_bias/bias.py` raise `ValueError` พร้อมข้อความ — ตามแพตเทิร์น `_finite_number` /
`_positive_number` ที่มีอยู่แล้วใน `electrical.py` ส่วน Flask route เป็นคนแปลงเป็นข้อความบนหน้าเว็บ

**ชั้นแปลงค่า (parsing layer):** `bias.py` รับเฉพาะตัวเลขจริง (`int`/`float`) ตามแบบ `electrical.py`
ไม่รับ string — Flask route เป็นเจ้าของการแปลง string → number และแปลง `ValueError` จาก `float()`
ให้เป็นข้อความชุดเดียวกับ validation (`"<field> must be a number."`) ผู้ใช้จะไม่เห็น
`could not convert string to float`

**หน่วยของ R:** ฟิลด์ตัวต้านทานเป็นโอห์ม และยอมรับ suffix `k`/`K` (×1e3) กับ `M` (×1e6)
เช่น `47000`, `47k`, `2.2k`, `1M` — parse ที่ชั้น route ด้วย `parse_resistance()` (~10 บรรทัด)
เพราะในแล็บเขียนค่าแบบ `2.2k` ตามปกติ ค่า default ในฟอร์มแสดงเป็น `47k`, `10k`, `2.2k`, `1k`

## 6. File layout

```
bjt_bias/
  __init__.py          # แพ็กเกจว่าง
  bias.py              # engineering logic ล้วน (ไม่ import Flask)
  app.py               # Flask app factory + routes + __main__
  templates/index.html # ฟอร์ม input + ผลลัพธ์ + ตารางเปรียบเทียบ
  static/style.css     # สไตล์
requirements.txt       # flask (pin version)
test_bjt_bias.py       # unittest ของ logic (ไม่ต้องมี Flask)
test_bjt_app.py        # unittest ของ route ด้วย Flask test client
docs/superpowers/specs/2026-11-10-bjt-common-emitter-dc-bias-design.md
```

## 7. Routes

| Route | Method | พฤติกรรม |
|---|---|---|
| `/` | GET | ฟอร์มพร้อมค่า default (VCC=12, R1=47k, R2=10k, RC=2.2k, RE=1k, beta=150, VBE=0.7) |
| `/` | POST | validate → คำนวณ → render ผลลัพธ์; ถ้า invalid render ฟอร์มเดิมพร้อม error และคงค่าที่กรอกไว้ |

ทั้งสองกรณีตอบ HTTP 200 (ฟอร์ม + ข้อความ error) เพื่อให้ผู้ใช้แก้ไขต่อได้ทันที ไม่ใช้ redirect

## 8. UI

หน้าเดียว: ฟอร์ม 7 ช่อง (หน่วยกำกับใน label) → หลัง submit แสดง

1. **Operating point** — การ์ดค่าที่รายงาน พร้อมหน่วย (V ทศนิยม 3 ตำแหน่ง, กระแสเป็น mA 3 ตำแหน่ง)
2. **Region badge** — active (เขียว) / cutoff (เหลือง) / saturation (แดง) + ข้อความอธิบาย
3. **Verification table** — แถวคือ `I_B, I_C, I_E, V_B, V_E, V_C, V_CE`; คอลัมน์คือ Method 1, Method 2, Δ;
   ปิดท้ายด้วย max relative difference และ badge PASS/FAIL (tolerance 1e-6)
4. **Warnings** — รวม warning จาก validation และ region ไว้ที่เดียว

## 9. Tests

`test_bjt_bias.py`
- golden case: VCC=12, R1=47k, R2=10k, RC=2.2k, RE=1k, beta=150, VBE=0.7 → active
  (`I_B ≈ 8.8245 µA`, `I_C ≈ 1.32368 mA`, `V_CE ≈ 7.7554 V`)
- cutoff case: R2=2.2k (V_BB ≈ 0.5366 V) → region = cutoff และค่าที่รายงานเป็นค่าตัด
- saturation case: RC=10k, RE=100 → region = saturation
- Method 1 vs Method 2 ตรงกันในทุกเคสข้างบน (relative diff < 1e-6)
- `_solve_linear_system` ถูกต้องกับระบบที่รู้คำตอบ + ระบบที่ต้องสลับแถว (partial pivoting)
- validation: ค่าติดลบ/ศูนย์, `VBE ≥ VCC`, `beta ≤ 0`, string, `bool`, `NaN`, `inf` → `ValueError`
- warning: `VBE = 0.95` → มี warning แต่ยังคำนวณได้
- `parse_resistance`: `47000`, `47k`, `2.2k`, `1M`, `47K` → ค่าถูก; `abc`, `0`, `-1k` → `ValueError`
- agreement rule ที่ค่าศูนย์: VCC=12, VBE=0.7, R1=113k, R2=7k (`V_BB == VBE`) → `I_B = 0` ทั้งสองวิธี
  ไม่ crash (0 vs 0 ผ่าน), region = cutoff

`test_bjt_app.py`
- `GET /` → 200 และมี input ทั้ง 7 ช่อง
- `POST /` ค่าถูกต้อง → 200, มีค่า `1.324` (mA), มี "active", มีตารางเปรียบเทียบ + PASS
- `POST /` ค่า invalid (`R1=0`) → 200, มีข้อความ error, ไม่มี traceback
- `POST /` เคส cutoff → 200 และมีคำว่า cutoff

## 10. Verification before claiming done

1. `python -m unittest discover -v` → ทุกเทสผ่าน (แสดงผลจริง)
2. `python -m bjt_bias.app` แล้วยิง `GET /` และ `POST /` ด้วยค่าจริง → HTTP 200 + เลขตรงกับ golden case
3. หยุด server แล้วรายงาน port ที่ใช้และคำสั่งรัน

## 11. Git plan

- branch `feature/bjt-bias-app` จาก `master`
- commit แยก: (1) design doc, (2) logic + tests, (3) Flask + templates + CSS + route tests, (4) README/requirements
- merge เข้า `master` แล้ว push ขึ้น `origin` (`pleng4995-cloud/Git-Lab`)
- ไฟล์ untracked เดิม (`B6811938-Phatcharakan_G01.zip`, `git-evidence.pdf`, `*.txt`) **ไม่ commit และไม่ลบ** — เป็นไฟล์ส่วนตัวของผู้ใช้

## 12. สิ่งที่เหลือให้ builder ตัดสิน

- จำนวนทศนิยม/รูปแบบตัวเลขบน UI ถ้าอาจารย์ต้องการทศนิยมต่างจากที่ระบุ
- จะเพิ่ม `/api/bias` (JSON) หรือไม่ — ตอนนี้ตัดออกเพื่อความเล็กที่สุด
- ภาษาในหน้าเว็บ (ตอนนี้: อังกฤษสำหรับ label/หน่วย, ไทยสำหรับคำอธิบาย warning)

## 13. Calls made after builder check (ตรวจย้อนได้)

| # | คำถามที่ reviewer ถาม | ข้อสรุป |
|---|---|---|
| 1 | หน่วยของ R และรับ suffix ไหม | โอห์ม + รับ `k`/`M`, default แสดง `47k` (§5.5) |
| 2 | แปลง string เป็น number ที่ชั้นไหน | route แปลง; `bias.py` รับเฉพาะ number (§5.5) |
| 3 | tolerance พังเมื่อค่าเป็นศูนย์ | `agree()` แบบ mixed abs/rel, `0 vs 0` = ตรงกัน (§5.3) |
