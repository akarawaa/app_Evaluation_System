# Deploy a free pilot environment (Supabase Cloud + Render + Vercel)

> เป้าหมาย: ให้หัวหน้างานทดลองใช้งานจริงได้จากคอมของตัวเอง เริ่มจาก flow ทดลองงาน
> ต้นทุน: ฟรีทั้งหมด (มีข้อจำกัดของฟรี tier ตามที่ระบุไว้ในแต่ละขั้น)

ขั้นตอนแบ่งเป็น 2 กลุ่ม: 🙋 **ต้องทำเอง** (สร้างบัญชี/กรอก secret — ผู้ช่วยทำแทนไม่ได้ด้วยเหตุผลด้านความปลอดภัย)
กับ ✅ **เตรียมให้แล้ว** (ไฟล์ config ในโปรเจกต์)

---

## 1. 🙋 สร้าง Supabase Cloud project (ฟรี)

1. ไปที่ https://supabase.com → สมัคร/ล็อกอิน → **New project**
2. ตั้งชื่อ, เลือก region **Southeast Asia (Singapore)** (ใกล้ไทยที่สุด), ตั้งรหัสผ่าน DB (เก็บไว้ ใช้ตอนต่อ backend)
3. รอ project สร้างเสร็จ (~2 นาที) แล้วเปิด **Project Settings → API** จด 3 ค่านี้ไว้:
   - `Project URL` → จะใช้เป็น `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
   - `service_role` key (กด reveal) → `SUPABASE_SERVICE_ROLE_KEY` — **เก็บเป็นความลับ ห้ามใส่ในโค้ด/แชร์**
4. เปิด **Project Settings → Database** จด **Connection string** (URI, ใช้ตัว "Transaction" pooler หรือ direct ก็ได้) → จะแปลงเป็น `DATABASE_URL` (ดูรูปแบบด้านล่าง)

## 2. 🙋 รัน migration + seed data บน project ใหม่

เปิด terminal บนเครื่องนี้ (ที่มี Supabase CLI อยู่แล้วจากตอน dev local):

```bash
cd D:/app_Evaluation_System
npx supabase login              # เปิด browser ให้ล็อกอินบัญชี Supabase ของคุณ
npx supabase link --project-ref <PROJECT_REF>   # PROJECT_REF ดูจาก URL ของ project เช่น abcxyz123
npx supabase db push            # รัน migration ทั้ง 17 ไฟล์ + seed.sql (role catalog + master template + BARS)
```

ยืนยันสำเร็จ: เปิด **Table Editor** บน Supabase dashboard ควรเห็นตาราง `companies`, `employees`, `evaluations` ฯลฯ ครบ และ `criteria_items` มีข้อมูล 70 แถว (`company_id is null`)

## 3. 🙋 เปิดใช้งาน Custom Access Token Hook (สำคัญมาก — ขาดขั้นนี้ล็อกอินไม่ได้)

Auth ของระบบนี้ต้องมี `company_id`/`roles`/`is_super_admin` ฝังใน JWT ผ่าน hook — ต้องเปิดเองใน dashboard (migration สร้างแค่ตัวฟังก์ชัน ไม่ได้เปิดใช้อัตโนมัติ):

1. **Authentication → Hooks (หรือ Auth Hooks)** ใน Supabase dashboard
2. เลือก **Customize Access Token (JWT) Claims hook**
3. เลือกฟังก์ชัน **`app.custom_access_token_hook`** แล้ว Enable

## 4. 🙋 สร้าง tenant + hr_admin คนแรก

Cloud project ใหม่ยังไม่มี tenant ไหนเลย ต้องสร้างผ่าน super_admin ก่อน (endpoint `POST /api/admin/tenants`) — รอจนกว่า backend deploy เสร็จ (ขั้น 6) ค่อยเรียกจาก Postman/curl หรือฝากผู้ช่วยทำให้ทีหลังได้

## 5. 🙋 Push โค้ดขึ้น GitHub (private repo)

1. สร้าง repo ใหม่ (private) ที่ https://github.com/new — **อย่าติ๊ก** "Add a README" (repo ต้องว่างเปล่า)
2. บอก URL ของ repo (เช่น `https://github.com/yourname/e-appraisal.git`) แล้วผู้ช่วยจะ push โค้ดให้

## 6. 🙋 Deploy backend บน Render (ฟรี)

1. ไปที่ https://render.com → สมัคร/ล็อกอินด้วย GitHub
2. **New → Blueprint** → เลือก repo ที่ push ไป → Render จะอ่าน `render.yaml` ที่เตรียมไว้แล้วอัตโนมัติ
3. ระหว่างตั้งค่า จะมีช่องให้กรอก env vars ที่ทำเครื่องหมาย "sync: false" ไว้ — กรอกค่าจริงตรงนี้ **บนหน้า Render โดยตรง** (ไม่ต้องส่งให้ผู้ช่วย):
   - `DATABASE_URL` = `postgresql+asyncpg://postgres:<DB_PASSWORD>@<HOST_จาก_ขั้น_1>:5432/postgres`
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` = ค่าจากขั้น 1
   - `CORS_ORIGINS` = ใส่ `https://placeholder.vercel.app` ไปก่อน (จะกลับมาแก้เป็นโดเมนจริงหลังขั้น 7)
4. Deploy — เสร็จแล้วจะได้ URL แบบ `https://e-appraisal-api.onrender.com`
5. **ข้อจำกัดฟรี tier**: service จะ sleep หลังไม่มีคนใช้ 15 นาที คำขอแรกหลัง sleep จะช้า ~30-50 วินาที (ปกติของแผนฟรี)

## 7. 🙋 Deploy frontend บน Vercel (ฟรี)

1. ไปที่ https://vercel.com → สมัคร/ล็อกอินด้วย GitHub
2. **Add New → Project** → เลือก repo เดียวกัน → **Root Directory** ตั้งเป็น `frontend`
3. Vercel จะ detect Vite อัตโนมัติ (build command/output ไม่ต้องแก้)
4. เพิ่ม Environment Variables:
   - `VITE_SUPABASE_URL` = ค่าจากขั้น 1
   - `VITE_SUPABASE_ANON_KEY` = ค่าจากขั้น 1 (anon key เท่านั้น — **ห้ามใส่ service_role**)
   - `VITE_API_BASE_URL` = URL จาก Render (ขั้น 6.4)
5. Deploy — เสร็จแล้วจะได้ URL แบบ `https://e-appraisal.vercel.app`

## 8. 🙋 ปิดวงจร: อัปเดต CORS_ORIGINS

กลับไปที่ Render → env var `CORS_ORIGINS` → แก้จาก placeholder เป็น URL จริงจาก Vercel (ขั้น 7.5) → save (Render จะ redeploy อัตโนมัติ)

---

## ✅ เตรียมให้แล้วในโปรเจกต์
- [render.yaml](../render.yaml) — Render Blueprint (build/start command, Python 3.11.9, region Singapore, env var ที่ต้องกรอกมือทำเครื่องหมาย `sync: false` ไว้ให้)
- [frontend/vercel.json](../frontend/vercel.json) — SPA rewrite (จำเป็นสำหรับ React Router ให้ URL ตรง ๆ เช่น `/evaluations/compare` ใช้งานได้ ไม่ใช่แค่ผ่านลิงก์ในแอป)

## หลัง deploy สำเร็จ
- ทดสอบ end-to-end: HR (ผ่าน super_admin หรือ hr_admin ที่สร้างไว้) สร้างพนักงานทดลอง → สร้างใบประเมิน `kind=probation` → หัวหน้างานล็อกอินจาก URL ของ Vercel ให้คะแนน
- ถ้าจะยกเลิก pilot: ลบ Render service + Vercel project + Supabase project ได้เลย ไม่มีผลต่อโค้ด local
