# DC Circuit Calculator

วัตถุประสงค์: โปรแกรมคำนวณและวิเคราะห์วงจรไฟฟ้ากระแสตรง (DC) แบบอนุกรม ขนาน และผสม โดยผู้ใช้เพียงระบุค่าความต่างศักย์และแรงต้านทาน ระบบจะคำนวณหาค่ากระแสไฟฟ้ารวม (Current) และกำลังไฟฟ้า (Power) ของแต่ละอุปกรณ์ให้อัตโนมัติ เพื่อช่วยให้ผู้เรียนเข้าใจกฎของโอมห์และวิเคราะห์วงจรได้อย่างแม่นยำ

## BJT Common-Emitter DC Bias — Flask web app (Lab 2–3)

เว็บแอป Flask สำหรับคำนวณ DC operating point ของ BJT common-emitter
รองรับ **3 โหมดไบแอส**: Voltage Divider Bias (ของเดิมจาก Lab 2), Fixed Bias
และ Emitter Bias (เพิ่มใน Lab 3)

- **GitHub:** <https://github.com/pleng4995-cloud/Git-Lab>
- **Commit SHA ของงาน Lab 3:** [`de871dc`](https://github.com/pleng4995-cloud/Git-Lab/commit/de871dccca5f3b9368640ed85cb8057c0e74310a)
  (`de871dccca5f3b9368640ed85cb8057c0e74310a`)
- **ตารางตรวจรับ A1–A5 + หลักฐานจากหน้าเว็บ:** [`docs/validation.md`](docs/validation.md)

### วิธีรัน

ต้องมี Python 3 และติดตั้ง dependency (มีแค่ Flask)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

วิธีที่แนะนำ — ดับเบิลคลิก `start.bat` (ใช้ `.venv` ให้เอง เปิดเซิร์ฟเวอร์ใน
หน้าต่างแยก แล้วเปิดเบราว์เซอร์ที่ <http://127.0.0.1:5000>)
หยุดเซิร์ฟเวอร์ด้วย `stop.bat`

หรือรันเองใน PowerShell:

```powershell
.\.venv\Scripts\python.exe -m bjt_bias.app
```

แล้วเปิด <http://127.0.0.1:5000> — terminal ต้องเปิดค้างไว้ตลอดที่ใช้งาน

> ถ้าเรียก `python -m bjt_bias.app` เฉย ๆ จะได้
> `ModuleNotFoundError: No module named 'flask'` เพราะ Flask อยู่ใน `.venv`
> ต้องเรียกผ่าน `.\.venv\Scripts\python.exe`

### โหมดที่รองรับ

| โหมด | ช่องที่ใช้ | สมการ IB |
|---|---|---|
| Voltage Divider Bias | VCC, R1, R2, RC, RE, β, VBE | `(VTH − VBE) / [RTH + (β+1)·RE]` |
| Fixed Bias | VCC, RB, RC, β, VBE | `(VCC − VBE) / RB` |
| Emitter Bias | VCC, RB, RE, RC, β, VBE | `(VCC − VBE) / [RB + (β+1)·RE]` |

จาก IB: `IC = β·IB`, `IE = (β+1)·IB`, `VE = IE·RE` (Fixed ใช้ `VE = 0`),
`VB = VE + VBE`, `VC = VCC − IC·RC`, `VCE = VC − VE`
รายละเอียดเพิ่มเติม: [`bjt_bias/README.md`](bjt_bias/README.md)

### ค่าอ้างอิงอิสระ (คำนวณมือ ไม่ได้มาจากโปรแกรม)

VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V

| กรณี | สมการ | ค่าอ้างอิง |
|---|---|---|
| Fixed, RB = 1 MΩ | `IB = (12 − 0.70) / 1 MΩ = 11.3 µA` → `IC = 1.1300 mA`, `VC = 12 − 1.13 mA × 2.2 kΩ = 9.5140 V` | IC = 1.1300 mA, VCE = 9.5140 V |
| Emitter, RB = 1 MΩ, RE = 1 kΩ | `IB = 11.3 / (1 MΩ + 101 × 1 kΩ) = 10.2634 µA` → `IC = 1.02634 mA`, `VE = 1.0366 V`, `VCE = 8.70545 V` | IC = 1.0263 mA, VCE = 8.7054 V |

arithmetic เต็มของ A1–A5 อยู่ใน [`docs/validation.md`](docs/validation.md)

### AI ช่วยสร้างส่วนไหน และนักศึกษาตรวจอะไร

**AI (OpenCode) เขียน:**

- `bjt_bias/bias.py` — `solve_fixed_bias`, `solve_emitter_bias`,
  `analyze_fixed_bias`, `analyze_emitter_bias`, `_validate_common_inputs`,
  `_forward_active_result` (สมการตามใบงาน, คืน dict 7 คีย์เดิม)
- `bjt_bias/app.py` — `MODES`/`MODE_LABELS`, `_resolve_mode`, `_mode_fields`,
  `_read_form(form, mode)`, `_analyze` (if/elif เลือกโมเดล), `page_context`
- `bjt_bias/templates/index.html`, `bjt_bias/static/style.css` — แถบเลือกโหมด,
  ไดอะแกรม SVG ตามโหมด, หัวข้อ/error ที่ระบุโหมด
- `start.bat`, `stop.bat`, `scripts/browser_acceptance.py`, เอกสาร `docs/`

**นักศึกษาตรวจ:**

- รันแอปและเปลี่ยนโหมดทั้งสามด้วยตัวเอง แล้วแจ้งข้อผิดพลาดที่พบ
  (ไดอะแกรมไม่เปลี่ยนตามโหมด, เปิด Flask ไม่ได้) ซึ่งนำไปสู่การแก้ไข
- ตรวจว่าผลของโหมด Divider ยังเท่าเดิมกับ Lab 2 (A1: 1.230 mA / 8.052 V)
  และชุดเทสเดิม 62 ตัวยังผ่าน
- ทวนผลเองอย่างน้อย 1 กรณี — บันทึกในหัวข้อ "ทวนเองโดยนักศึกษา"
  ของ [`docs/validation.md`](docs/validation.md)

**โค้ดเลือกฟังก์ชันตามโหมด:** `bjt_bias/app.py`

- `_resolve_mode()` อ่านค่า `mode` จาก request (หาย → `divider`, ไม่รู้จัก → error)
- `_analyze()` ใช้ `if/elif` เรียก `analyze_bias` / `analyze_fixed_bias` /
  `analyze_emitter_bias`

**โค้ดแปลงหน่วย:** `bjt_bias/app.py` ฟังก์ชัน `_read_form()` — แปลงค่าที่กรอก
(Ω / kΩ / MΩ) เป็น SI (โอห์ม, โวลต์) ด้วย `multiplier` **ที่จุดเดียว**
แล้วส่งเข้า engine; engine ทำงานเป็น SI ทั้งหมด
