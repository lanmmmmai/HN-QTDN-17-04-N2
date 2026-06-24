# Plan 006: Tự động hóa gửi Phiếu lương qua Email & Chatter

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise.
>
> **Drift check (run first)**: Check if `addons/cham_cong_tinh_luong/models/bang_luong.py` has any unsaved changes or new methods related to mail templates.

## Status

- **Priority**: P2
- **Effort**: S (2 hours)
- **Risk**: LOW
- **Depends on**: none
- **Category**: feature
- **Planned at**: 2026-06-22

## Why this matters

Hiện tại, nhân viên phải tự đăng nhập vào hệ thống Odoo để xem phiếu lương cá nhân của họ hoặc kế toán phải tải xuống PDF và gửi thủ công qua các kênh liên lạc khác. Việc tự động hóa gửi email phiếu lương kèm file PDF chi tiết trực tiếp khi bảng lương được thanh toán sẽ nâng cao hiệu quả làm việc của bộ phận kế toán, giảm thiểu thao tác thủ công và nâng cao trải nghiệm tự phục vụ của nhân viên.

Tính năng này sẽ:
1. Thêm nút "Gửi Email" trên giao diện Bảng lương dành cho Kế toán và Admin.
2. Tự động gửi email kèm file PDF Phiếu lương khi bảng lương được kế toán chuyển sang trạng thái "Đã thanh toán" (`da_thanh_toan`).
3. Ghi vết log gửi email vào Chatter của bản ghi bảng lương để tiện theo dõi.

## Current state

- File liên quan:
  - `addons/cham_cong_tinh_luong/__manifest__.py` — Đăng ký tệp dữ liệu XML mới.
  - `addons/cham_cong_tinh_luong/models/bang_luong.py` — Bổ sung logic gửi email.
  - `addons/cham_cong_tinh_luong/views/bang_luong_view.xml` — Thêm nút "Gửi Email" trên giao diện form.
  
- File cần tạo mới:
  - `addons/cham_cong_tinh_luong/data/mail_template_data.xml` — Chứa định nghĩa mẫu email gửi phiếu lương.

## Scope

**In scope**:
- Thiết lập Email Template cho bảng lương bằng tiếng Việt, được định dạng HTML chuyên nghiệp.
- Sinh tự động file PDF từ report `cham_cong_tinh_luong.action_report_bang_luong` và đính kèm vào email.
- Tích hợp nút bấm gửi email thủ công và cơ chế trigger tự động khi thanh toán.

**Out of scope**:
- Cấu hình SMTP server của hệ thống Odoo (giả định mail server đã được cấu hình sẵn trong Odoo).

## Steps

### Step 1: Tạo tệp Mẫu Email (Email Template)

Tạo tệp dữ liệu mới [mail_template_data.xml](file:///d:/My_Lan/HN-QTDN-17-04-N2/addons/cham_cong_tinh_luong/data/mail_template_data.xml) định nghĩa `mail.template` cho bảng lương:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <record id="mail_template_phieu_luong" model="mail.template">
            <field name="name">Phiếu lương nhân viên</field>
            <field name="model_id" ref="cham_cong_tinh_luong.model_bang_luong"/>
            <field name="subject">Phiếu lương Tháng ${object.thang}/${object.nam} - ${object.nhan_vien_id.ho_va_ten}</field>
            <field name="email_to">${object.nhan_vien_id.email}</field>
            <field name="body_html" type="html">
                <div style="font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 14px; color: #1a1a1a; padding: 20px;">
                    <p>Kính gửi anh/chị <strong>${object.nhan_vien_id.ho_va_ten}</strong>,</p>
                    <p>Phòng Kế toán xin gửi thông tin phiếu lương của anh/chị trong kỳ lương <strong>Tháng ${object.thang}/${object.nam}</strong> như sau:</p>
                    <ul>
                        <li>Số ngày đi làm thực tế: <strong>${object.so_ngay_di_lam} ngày</strong></li>
                        <li>Tổng giờ tăng ca: <strong>${object.tong_gio_tang_ca} giờ</strong></li>
                        <li>Tổng lương thực nhận (Net): <strong style="color: #0284c7;">${'{:,.0f}'.format(object.thuc_linh)} VNĐ</strong></li>
                    </ul>
                    <p>Chi tiết các khoản thu nhập, phụ cấp và khấu trừ được đính kèm trong file PDF gửi kèm thư này.</p>
                    <p>Mọi thắc mắc về số liệu vui lòng phản hồi lại với bộ phận Kế toán để được giải đáp sớm nhất.</p>
                    <br/>
                    <p>Trân trọng,</p>
                    <p><strong>Bộ phận Kế toán</strong></p>
                </div>
            </field>
            <field name="report_template" ref="cham_cong_tinh_luong.action_report_bang_luong"/>
            <field name="report_name">Phieu_luong_thang_${object.thang}_${object.nam}</field>
            <field name="auto_delete" eval="True"/>
        </record>
    </data>
</odoo>
```

### Step 2: Cập nhật Manifest đăng ký tệp data mới

Sửa [__manifest__.py](file:///d:/My_Lan/HN-QTDN-17-04-N2/addons/cham_cong_tinh_luong/__manifest__.py) để nạp tệp `data/mail_template_data.xml` vào cơ sở dữ liệu.
Nạp tệp ở phần dữ liệu cơ sở trước views:

```python
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/mail_template_data.xml',  # Nạp template trước views
        # ...
```

### Step 3: Thêm logic gửi email vào bang_luong.py

Thêm phương thức `action_gui_email_phieu_luong` và override trạng thái `action_da_thanh_toan` (hoặc chuyển trạng thái) để tự động gửi:

```python
    def action_gui_email_phieu_luong(self):
        self.ensure_one()
        if not self.nhan_vien_id.email:
            raise ValidationError('Nhân viên %s chưa cấu hình địa chỉ Email.' % self.nhan_vien_id.ho_va_ten)
        
        template = self.env.ref('cham_cong_tinh_luong.mail_template_phieu_luong', raise_if_not_found=False)
        if not template:
            raise ValidationError('Không tìm thấy mẫu email Phiếu lương.')
            
        template.send_mail(self.id, force_send=True)
        # Ghi log hoạt động vào Chatter
        self.message_post(body='Đã gửi phiếu lương tháng %s/%s qua email cho nhân viên.' % (self.thang, self.nam))
        return True

    def action_da_thanh_toan(self):
        # ... (các nghiệp vụ chuyển trạng thái thanh toán cũ)
        res = super().action_da_thanh_toan() # hoặc write({'state': 'da_thanh_toan'})
        for record in self:
            if record.nhan_vien_id.email:
                record.action_gui_email_phieu_luong()
        return res
```

### Step 4: Thêm nút bấm trên Giao diện form bảng lương

Sửa tệp [bang_luong_view.xml](file:///d:/My_Lan/HN-QTDN-17-04-N2/addons/cham_cong_tinh_luong/views/bang_luong_view.xml) để thêm nút "Gửi Email":

```xml
<button name="action_gui_email_phieu_luong" 
        string="Gửi Email" 
        type="object" 
        states="da_tinh,xac_nhan,da_thanh_toan" 
        class="oe_highlight" 
        groups="cham_cong_tinh_luong.group_cham_cong_ke_toan,cham_cong_tinh_luong.group_cham_cong_quan_tri"/>
```

---

## Done criteria

- [ ] Email Template `mail_template_phieu_luong` được khởi tạo thành công trong Odoo database.
- [ ] Nút "Gửi Email" hiển thị chính xác trên giao diện form bảng lương khi ở các trạng thái tương ứng.
- [ ] Bấm nút gửi email hoạt động không lỗi, tự động đính kèm file PDF phiếu lương chuẩn.
- [ ] Khi chuyển trạng thái bảng lương sang `da_thanh_toan`, hệ thống tự động gửi email thành công mà không cần bấm thủ công.
