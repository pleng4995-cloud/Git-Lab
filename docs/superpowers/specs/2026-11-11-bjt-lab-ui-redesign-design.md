# Design — BJT Lab UI Redesign (Lab 02 layout)

วันที่: 2026-11-11
สถานะ: อนุมัติแล้ว (2026-11-11)
ขนาดงาน: small change (template + CSS + app layer; engine ไม่แตะ)

## 1. Intent / Why

หน้าปัจจุบันของ `bjt_bias/` ใช้งานได้แต่เป็นฟอร์มเรียบ ๆ ไม่ได้สื่อว่าเป็นแล็บของรายวิชา
ผู้ใช้ต้องการหน้าแบบ **Lab 02** — สามคอลัมน์ (Input / Circuit / Results) พร้อม banner
บอก region และแถบ Week 2 Goal — เพื่อใช้เป็นหน้านำเสนอผลงานแล็บ

**ตัวเลขทุกตัวบนหน้าต้องมาจาก engine ที่คำนวณจริง** ไม่ใช่ค่าจาก mockup
(ค่าใน mockup ขัดกับสมการเอง เช่น `V_B = 2.20 V` สูงกว่า `V_BB = 2.164 V`)

## 2. Goals

- โครงหน้า: header + 3 คอลัมน์ + verification panel + Week 2 Goal strip
- Input panel มี unit selector ต่อช่อง (Ω/kΩ/MΩ สำหรับตัวต้านทาน, V สำหรับแรงดัน, – สำหรับ β)
- Circuit panel เป็น SVG วงจร common-emitter ที่ label วิ่งตามค่าที่ผู้ใช้กรอก
- Results panel แสดง 7 ค่าเรียงตาม mockup: `V_B, V_E, V_C, V_CE, I_B, I_C, I_E`
- Banner ตาม region จาก engine: active (เขียว) / cutoff (เหลือง) / saturation (แดง)
- คงส่วน verification Method 1 vs Method 2 + PASS/FAIL ไว้เป็น panel รอง
- เทสเดิม 43 ตัวยังผ่าน; เพิ่มเทสสำหรับ unit conversion, banner, circuit label

## 3. Non-goals / Anti-goals

- ไม่เปลี่ยนสมการหรือ `bias.py` (ยกเว้นถ้าจำเป็นจริง ๆ ต้องแจ้งก่อน)
- ไม่ทำ circuit editor / ลากวางอุปกรณ์ / แก้ topology
- ไม่คำนวณฝั่ง JavaScript — logic อยู่ฝั่ง Python ตามข้อกำหนดเดิม
- ไม่ใช้ CDN, web font, หรือ icon library ภายนอก (เปิด offline ได้)
- ไม่เพิ่มหน้าใหม่ที่ route อื่น — restyle หน้า `/` เดิม
- Anti-goal: หน้าใหม่ที่ตัวเลขไม่ตรงกับ engine หรือหน่วยหาย

## 4. Constraints

- Flask 3.1.3, Python 3.14, `unittest` เท่านั้น
- `analyze_bias` และ `OPERATING_POINT_FIELDS` เป็น contract เดิม ใช้ต่อไม่แก้
- ต้องรองรับ POST ที่ไม่มี unit key (เช่น curl เดิม) — default เป็นหน่วยฐาน
- ค่า default ของฟอร์มเปลี่ยนเป็นชุดใน mockup: `12, 100 kΩ, 22 kΩ, 2.2 kΩ, 1 kΩ, 100, 0.7`

## 5. Approaches

| ทาง | ข้อดี | ข้อเสีย | ผล |
|---|---|---|---|
| **A. Restyle in place** — เขียน `index.html`/`style.css` ใหม่ + ขยาย `app.py` | engine ที่ review แล้วไม่แตะ, เทสเดิมใช้ได้, ไฟล์น้อย | ต้องแก้ parsing ให้รับ unit | **เลือก** |
| B. เพิ่มหน้าใหม่ `/lab` | เก็บหน้าเดิมไว้ | ต้องดูแลสองหน้า, deliverable กำกวม, เทสซ้ำ | ตัด |
| C. คำนวณฝั่ง client ด้วย JS | หน้าโต้ตอบเร็ว | ผิดข้อกำหนด "engineering logic แยกฝั่ง Python" | ตัด |

## 6. Decisions (ผู้ใช้เลือก / builder call)

- **ผู้ใช้เลือก:** โครงคล้าย mockup แต่ใช้ตัวเลขที่คำนวณถูกต้อง; เก็บ verification panel ไว้
- **Builder call:** unit selector เป็น `<select>` ข้าง input; ตัวต้านทานมี Ω/kΩ/MΩ (default kΩ), VCC/VBE มี V, β มี –
- **Builder call:** backend แปลง `value × unit` เป็น SI ก่อนเรียก `analyze_bias`; ถ้าไม่มี unit key ใช้ตัวคูณ 1
- **Builder call:** `parse_resistance` เดิมยังอยู่ (รับ `47k`/`1M`) เพื่อความเข้ากันได้ของเทสและ curl
- **Builder call:** circuit เป็น SVG static topology, label มาจากค่าที่ POST มา (ไม่ใช่ค่าที่คำนวณ)
- **Builder call:** results เรียงตาม mockup โดยใช้รายการ display order ใน `app.py` ไม่แก้ `OPERATING_POINT_FIELDS`
- **Builder call:** verification อยู่ใน `<details open>` ใต้ 3 คอลัมน์
- **Builder call:** error แสดงใน input panel; results/banner ไม่แสดงเมื่อมี error
- **Builder call:** responsive — 3 คอลัมน์เมื่อ ≥ 900px, 1 คอลัมน์เมื่อแคบกว่า

## 7. Left to the builder

- สี/ระยะห่าง/เงาให้ใกล้ mockup ภายใน palette ที่อ่านง่ายและ contrast ผ่าน
- ข้อความ banner ของ cutoff/saturation (mockup มีแต่ active)
- วิธี format ค่าบน circuit label (เช่น `2.2 kΩ` vs `2200 Ω`)
- เทสที่จำเป็นเพิ่มเติมนอกเหนือจากที่ระบุใน §2
