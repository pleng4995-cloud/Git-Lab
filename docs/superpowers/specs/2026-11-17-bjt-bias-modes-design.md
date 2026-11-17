# Design — เพิ่ม Fixed Bias และ Emitter Bias ใน Lab 03

วันที่: 2026-11-17
สถานะ: รออนุมัติ
งานที่ต่อยอด: Lab 02 (`bjt_bias/`) — Flask + Divider bias ที่ใช้งานได้แล้ว

## Intent

นักศึกษาต้องส่ง Lab 03 ที่เว็บเดียวรองรับ BJT Common-Emitter 3 โหมด คือ
Voltage Divider (ของเดิม), Fixed Bias และ Emitter Bias โดยใช้แบบจำลอง DC
ที่ β และ VBE คงที่ในย่าน Forward Active และ **ผลของ Divider ต้องไม่เปลี่ยน**
(A1 ต้องได้ค่าเดียวกับ Lab 2 ก่อนแก้)

## Goals

1. `bjt_bias/bias.py` มีฟังก์ชัน Fixed และ Emitter แยกกัน ตามสมการในใบงาน
   และยังเก็บวิธีคำนวณ Divider เดิมไว้ครบ
2. ทั้งสามโหมดคืน dict คีย์ชุดเดียวกัน: `v_b_v, v_e_v, v_c_v, v_ce_v,
   i_b_a, i_c_a, i_e_a` (ชื่อเดิมของ Lab 2 ซึ่งใบงานอนุญาตให้ใช้ต่อ)
3. `app.py` เลือกโมเดลด้วย `if/elif` ตามค่าจากฟอร์ม, แปลงหน่วยที่จุดเดียว,
   ตรวจเฉพาะช่องที่โหมดนั้นต้องใช้
4. หน้าเว็บเลือกโหมดได้โดยไม่ต้องใช้ JavaScript, เห็นเฉพาะช่องของโหมดนั้น,
   และผล/ข้อผิดพลาดระบุโหมดที่เลือก
5. `docs/validation.md` มีตาราง A1–A5 พร้อมค่าอ้างอิงที่คำนวณด้วยมือ

## Non-goals

- ไม่ทำ AC analysis, transient, load line, circuit editor
- ไม่แก้สมการหรือพฤติกรรมของ Divider (`analyze_bias` คงเดิม)
- ไม่เขียน unittest ใหม่ (ใบงานสั่งให้คงเทสเดิมและตรวจผ่าน browser)
- ไม่เพิ่ม dependency ใน `requirements.txt` (ยังมีแค่ Flask)
- ไม่ย้ายสมการไปไว้ใน HTML และไม่สร้างโปรเจกต์ใหม่

## Anti-goals

- ผล Divider เปลี่ยนแม้แต่นิดเดียว
- โหมดที่ไม่รู้จักถูกเดาเป็น Divider
- เห็นผลของรอบก่อนค้างอยู่ทั้งที่รอบนี้กรอกผิด
- หน้าเว็บโชว์ไดอะแกรม Divider ขณะเลือกโหมด Fixed

## Constraints

- Flask 3.1.3, Python 3.14, `unittest` เดิม 62 เทสต้องผ่านทั้งหมด
- เทสเดิม POST `/` โดยไม่ส่ง `mode` → ต้องตีความเป็น Divider
- ตัวเลขบนเว็บต้องมาจาก engine เท่านั้น
- Playwright MCP ยังใช้ไม่ได้บนเครื่องนี้ (ไม่มี Node.js/npx, ไม่มี
  `opencode.json`) — ต้องตั้งก่อนรัน A1–A5

## Approaches ที่พิจารณา

**1. สลับโหมด (เลือกแล้ว: GET + hidden field)**
- A. `GET /?mode=fixed` เรนเดอร์ฟอร์มของโหมดนั้น แล้วฟอร์มค่าส่ง `mode`
  เป็น hidden field ไปกับ POST — เปลี่ยนโหมดกับการคำนวณเป็นคนละ action
- B. ฟอร์มเดียว POST ตลอด: เปลี่ยนโหมด = กดคำนวณ → ปนสองเจตนา และทำให้
  ค่าที่ค้างจากโหมดก่อนหลุดเข้าโหมดใหม่
- C. ลิงก์ `/?mode=...` ไม่มี dropdown — ทำงานเหมือน A แต่Discoverability แย่กว่า

**2. ไดอะแกรม (เลือกแล้ว: แยก 3 แบบ)**
- A. SVG 3 ชุด เลือกตามโหมด — ตรงกับวงจรจริง
- B. SVG กลาง ๆ ชุดเดียว — ประหยัดงานแต่หน้าจะแสดง R2 ในโหมด Fixed ซึ่งผิด

**3. แผง Verification (เลือกแล้ว: ซ่อนในโหมดใหม่)**
- A. แสดงเฉพาะ Divider — Method 1/2 มีความหมายกับ divider เท่านั้น
- B. เขียน nodal method ที่สองให้ Fixed/Emitter — เกินขอบเขตใบงาน

**4. banner ของโหมดใหม่ (เลือกแล้ว: คงค่าไว้ + เตือน)**
- A. โชว์ค่าที่สมการให้มา แล้วเตือนว่าแบบจำลองอาจใช้ไม่ได้ (ตามใบงาน)
- B. แทนค่าด้วย operating point ของ Cutoff/Saturation — ใบงานห้าม

## Design

### 1. Engine — `bjt_bias/bias.py`

เพิ่มฟังก์ชันบริสุทธิ์ (ไม่แตะของเดิม):

```python
def solve_fixed_bias(vcc, rb, rc, beta, vbe):
    i_b = (vcc - vbe) / rb
    i_c = beta * i_b
    i_e = (beta + 1) * i_b
    v_e = 0.0
    v_b = v_e + vbe
    v_c = vcc - i_c * rc
    return {"i_b_a": i_b, "i_c_a": i_c, "i_e_a": i_e,
            "v_b_v": v_b, "v_e_v": v_e, "v_c_v": v_c, "v_ce_v": v_c - v_e}

def solve_emitter_bias(vcc, rb, re, rc, beta, vbe):
    i_b = (vcc - vbe) / (rb + (beta + 1) * re)
    # ที่เหลือเหมือน Fixed แต่ v_e = i_e * re
```

ตัวห่อผลลัพธ์ (`analyze_fixed_bias`, `analyze_emitter_bias`) ทำตามลำดับ:
1. validate เฉพาะช่องของโหมด (`_positive_number` / `_finite_number`,
   VBE ต้องอยู่ระหว่าง 0 ถึง VCC)
2. คำนวณด้วย `solve_*`
3. `region` = `cutoff` ถ้า `i_b <= 0`, `saturation` ถ้า `v_ce <= VCE_SAT_V`,
   ไม่งั้น `active` — **ไม่แทนที่ operating point** (ต่างจาก Divider)
4. `warnings` มีข้อความ "Forward Active model may not be valid ..." เมื่อ
   region ไม่ใช่ active
5. คืน `{"operating_point", "region", "warnings", "verification": None}`

Divider ใช้ `analyze_bias` เดิมทุกบรรทัด รวมถึง `verification` และการแทน
cutoff operating point

### 2. ช่องอินพุต — `bjt_bias/app.py`

เพิ่ม field `rb` (Base Resistor, Ω/kΩ/MΩ, default `1000` kΩ = 1 MΩ) และ
ขยาย `FIELDS` แต่ละรายการด้วย `modes` (โหมดที่ใช้ช่องนั้น)

| โหมด | ช่องที่ต้องใช้ |
|---|---|
| `divider` | `vcc, r1, r2, rc, re, beta, vbe` |
| `fixed` | `vcc, rb, rc, beta, vbe` |
| `emitter` | `vcc, rb, re, rc, beta, vbe` |

- `mode` หายไปจาก POST → `divider` (รองรับเทสเดิมและ curl)
- `mode` ไม่รู้จัก → error `Unknown bias mode: '<ค่า>'` ไม่คำนวณ
- `_read_form(form, mode)` parse เฉพาะช่องของโหมดนั้น ช่องอื่นไม่ถูกตรวจ
  และไม่ถูกส่งเข้า engine
- เลือกฟังก์ชันด้วย `if/elif` ตาม `mode` แล้วเรียก `analyze_bias` /
  `analyze_fixed_bias` / `analyze_emitter_bias`
- ถ้ามี error ใด ๆ → `result = None` (ไม่ค้างผลรอบก่อน)
- `page_context` เพิ่ม `mode`, `mode_label`, `mode_options`
- `circuit_labels` รับ `mode` เพื่อ label เฉพาะตัวต้านทานที่มีในโหมดนั้น

### 3. เทมเพลต — `bjt_bias/templates/index.html`

- เหนือฟอร์มค่า: ฟอร์ม GET เล็ก ๆ `<select name="mode">` + ปุ่ม
  "Load form" (ไม่ใช้ JS) — เมื่อเปลี่ยนโหมดแล้ว submit จะได้หน้าใหม่ที่
  แสดงเฉพาะช่องของโหมดนั้น
- ฟอร์มค่า: `<input type="hidden" name="mode" value="{{ mode }}">`
- หัวข้อผลลัพธ์: `DC Bias Results — Fixed Bias` (ระบุโหมด)
- กล่อง error: `Invalid input (Fixed Bias)` เพื่อไม่ให้สับสนว่าเป็นของโหมดไหน
- ไดอะแกรม: 3 บล็อก เลือกด้วย `{% if mode == ... %}` — Fixed ไม่มี R2/RE,
  Emitter ไม่มี R1/R2, Divider เหมือนเดิม
- แผง Verification: แสดงเฉพาะเมื่อ `result.verification` ไม่เป็น None
- banner: ใช้คลาสเดิม (`banner-active/cutoff/saturation`) แต่ข้อความของ
  โหมดใหม่พูดว่า "Forward Active model may not be valid" ไม่ใช่ยืนยันว่าอยู่
  ในโหมดนั้นจริง

### 4. CSS — `bjt_bias/static/style.css`

เพิ่มสไตล์สำหรับแถบเลือกโหมด (`.mode-bar`, `.mode-bar select`) ให้เข้ากับ
palette เดิม ไม่แตะสไตล์ที่มีอยู่

### 5. เอกสารและหลักฐาน

- `docs/validation.md` — ตาราง A1–A5 ตามแม่แบบใบงาน มีค่าอ้างอิงที่คำนวณ
  ด้วยมือ (แสดง arithmetic ไว้ข้าง ๆ) และคอลัมน์ "เห็นจริง / วิธีตรวจ / สถานะ"
- `opencode.json` ที่รากโปรเจกต์ — เพิ่ม Playwright MCP ใต้ `mcp.servers`
  (V2 schema ตรวจแล้วจาก https://opencode.ai/config.json)
- ต้องติดตั้ง Node.js LTS แล้วปิด–เปิด OpenCode ก่อนรัน A1–A5

### ค่าอ้างอิงที่คำนวณด้วยมือ (VCC 12 V, RC 2.2 kΩ, β 100, VBE 0.70 V)

| กรณี | สมการที่ใช้ | IC | VCE |
|---|---|---|---|
| A1 Divider R1 100k R2 22k RE 1k | VTH=2.163934 V, RTH=18.033k, IB=(VTH−VBE)/(RTH+101·RE) | 1.2298 mA | 8.0522 V |
| A2 Fixed RB 1M | IB=(12−0.7)/1M | 1.1300 mA | 9.5140 V |
| A3 Emitter RB 1M RE 1k | IB=(12−0.7)/(1M+101·1k) | 1.0263 mA | 8.7054 V |
| A4 Emitter RE 2k | IB=(12−0.7)/(1M+101·2k) | 0.9401 mA | 8.0328 V |
| A5 Fixed RB 0 | ต้องถูกปฏิเสธก่อนถึงสมการ | — | — |

A4 ทำนาย: IC **ลดลง** จาก A3 เพราะ RE ใหญ่ขึ้น → emitter degeneration มากขึ้น
→ IB เล็กลง

## สิ่งที่เหลือให้ผู้สร้างตัดสิน

- ถ้อยคำของ warning/banner (ความหมายต้องตรงใบงาน)
- ตำแหน่งของแถบเลือกโหมด (เหนือฟอร์มค่าคือค่าที่เสนอ)
- รูปแบบตาราง `docs/validation.md` ให้ใกล้แม่แบบใบงานที่สุด
