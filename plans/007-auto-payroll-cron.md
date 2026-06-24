# Plan 007: Thiết lập Cron Job tự động tính công và sinh bảng lương định kỳ cuối tháng

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise.
>
> **Drift check (run first)**: Check if `addons/cham_cong_tinh_luong/models/bang_luong.py` has any unsaved changes or new methods related to scheduled actions.

## Status

- **Priority**: P2
- **Effort**: S (2 hours)
- **Risk**: LOW
- **Depends on**: none
- **Category**: feature
- **Planned at**: 2026-06-24

## Why this matters

Hiện tại, việc sinh bảng lương nháp và phân tích cảnh báo chấm công hàng tháng vẫn đang được Kế toán hoặc Admin thực hiện hoàn toàn thủ công thông qua giao diện Wizard. 
Việc tự động hóa hai tác vụ này thông qua Hành động định kỳ của Odoo (`ir.cron`) sẽ giúp hệ thống tự chạy vào ngày cuối cùng của tháng để:
1. Tự động chạy phân tích chấm công của tháng hiện tại và tạo các cảnh báo vi phạm.
2. Tự động sinh bảng lương nháp cho toàn bộ nhân viên hoạt động trong tháng, đảm bảo dữ liệu luôn sẵn sàng cho kế toán đối soát vào ngày mùng 1 đầu tháng tiếp theo.

## Current state

- File liên quan:
  - `addons/cham_cong_tinh_luong/__manifest__.py` — Đăng ký tệp dữ liệu XML mới.
  - `addons/cham_cong_tinh_luong/models/bang_luong.py` — Bổ sung hàm chạy tự động từ cron.
  - `addons/cham_cong_tinh_luong/models/canh_bao_cham_cong.py` — Bổ sung hàm phân tích tự động từ cron.

- File cần tạo mới:
  - `addons/cham_cong_tinh_luong/data/ir_cron_data.xml` — Chứa định nghĩa các hành động định kỳ (`ir.cron`).

## Scope

**In scope**:
- Cấu hình 2 Cron Job định kỳ hàng tháng.
- Viết các phương thức Python làm điểm kích hoạt cho Cron Job.
- Đảm bảo cơ chế tự xác định tháng/năm hiện tại để chạy tự động.

**Out of scope**:
- Cấu hình hạ tầng cron ở cấp độ hệ điều hành (giả lập cron của Odoo đã chạy sẵn).

## Steps

### Step 1: Tạo tệp cấu hình Cron XML

Tạo tệp dữ liệu mới [ir_cron_data.xml](file:///d:/My_Lan/HN-QTDN-17-04-N2/addons/cham_cong_tinh_luong/data/ir_cron_data.xml) để khai báo các hành động định kỳ:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">
        <!-- Cron Job 1: Tự động phân tích cảnh báo chấm công hàng tháng -->
        <record id="ir_cron_auto_analyze_attendance" model="ir.cron">
            <field name="name">Chấm công: Tự động phân tích cảnh báo chấm công hàng tháng</field>
            <field name="model_id" ref="cham_cong_tinh_luong.model_canh_bao_cham_cong"/>
            <field name="state">code</field>
            <field name="code">model.cron_auto_analyze_attendance()</field>
            <field name="interval_number">1</field>
            <field name="interval_type">months</field>
            <field name="numbercall">-1</field>
            <field name="doall" eval="False"/>
            <field name="active" eval="True"/>
        </record>

        <!-- Cron Job 2: Tự động sinh bảng lương nháp hàng tháng -->
        <record id="ir_cron_auto_calculate_payroll" model="ir.cron">
            <field name="name">Tính lương: Tự động sinh bảng lương nháp hàng tháng</field>
            <field name="model_id" ref="cham_cong_tinh_luong.model_bang_luong"/>
            <field name="state">code</field>
            <field name="code">model.cron_auto_calculate_payroll()</field>
            <field name="interval_number">1</field>
            <field name="interval_type">months</field>
            <field name="numbercall">-1</field>
            <field name="doall" eval="False"/>
            <field name="active" eval="True"/>
        </record>
    </data>
</odoo>
```

### Step 2: Cập nhật Manifest đăng ký tệp XML mới

Sửa [__manifest__.py](file:///d:/My_Lan/HN-QTDN-17-04-N2/addons/cham_cong_tinh_luong/__manifest__.py) để nạp tệp `data/ir_cron_data.xml` vào cơ sở dữ liệu:

```python
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',  # Nạp cron data tại đây
        # ...
```

### Step 3: Thêm logic Cron trong `bang_luong.py`

Thêm phương thức `cron_auto_calculate_payroll(self)` vào [bang_luong.py](file:///d:/My_Lan/HN-QTDN-17-04-N2/addons/cham_cong_tinh_luong/models/bang_luong.py):

```python
    @api.model
    def cron_auto_calculate_payroll(self):
        _logger.info('Bắt đầu chạy Cron tự động sinh bảng lương tháng...')
        today = fields.Date.context_today(self)
        thang = str(today.month)
        nam = today.year
        # Gọi hàm sinh bảng lương hàng loạt bằng quyền hệ thống (sudo)
        self.env['bang_luong'].sudo().action_sinh_bang_luong_thang(thang, nam)
        _logger.info('Cron tự động sinh bảng lương tháng kết thúc thành công.')
        return True
```

### Step 4: Thêm logic Cron trong `canh_bao_cham_cong.py`

Thêm phương thức `cron_auto_analyze_attendance(self)` vào [canh_bao_cham_cong.py](file:///d:/My_Lan/HN-QTDN-17-04-N2/addons/cham_cong_tinh_luong/models/canh_bao_cham_cong.py):

```python
    @api.model
    def cron_auto_analyze_attendance(self):
        _logger.info('Bắt đầu chạy Cron tự động phân tích chấm công tháng...')
        today = fields.Date.context_today(self)
        thang = str(today.month)
        nam = today.year
        
        # Giả lập hoạt động của wizard phân tích chấm công
        employees = self.env['nhan_vien'].sudo().search([])
        wizard = self.env['phan_tich_cham_cong_wizard'].sudo().create({
            'thang': thang,
            'nam': nam,
            'nhan_vien_ids': [(6, 0, employees.ids)],
        })
        wizard.action_phan_tich_canh_bao()
        _logger.info('Cron tự động phân tích chấm công tháng kết thúc thành công.')
        return True
```

---

## Done criteria

- [ ] Các bản ghi `ir.cron` được khởi tạo thành công trong Odoo database.
- [ ] Các hàm `cron_auto_calculate_payroll` và `cron_auto_analyze_attendance` chạy thành công không có lỗi runtime.
- [ ] Bộ test tự động kiểm thử hoạt động của cron hoàn thành.
