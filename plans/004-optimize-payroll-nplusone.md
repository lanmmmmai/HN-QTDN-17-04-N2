# Plan 004: Tối ưu hóa hiệu năng tính lương (Giảm thiểu truy vấn N+1) trong Bảng lương

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise.
>
> **Drift check (run first)**: `git diff --stat 1f284728..HEAD -- addons/cham_cong_tinh_luong/models/bang_luong.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M (2-3 hours)
- **Risk**: MED (Yêu cầu khớp chính xác dữ liệu cấu hình lương, chấm công và khen thưởng kỷ luật theo thời gian trong bộ nhớ)
- **Depends on**: none
- **Category**: perf
- **Planned at**: commit `1f284728`, 2026-06-19

## Why this matters

Trong mô hình Bảng lương (`bang_luong`), các hàm tính toán hiện đang thực hiện các câu lệnh `search` cơ sở dữ liệu riêng lẻ cho từng dòng ghi:
1. Hàm `_compute_bang_luong` lặp qua từng bản ghi bảng lương để tính toán, mỗi lần gọi `_get_payroll_values()` lại thực hiện các câu lệnh truy vấn cấu hình lương (`cau_hinh_luong`), chấm công (`cham_cong`) và khen thưởng kỷ luật (`khen_thuong_ky_luat`). Nếu tính lương cho 100 nhân viên trong một tháng, Odoo sẽ phát sinh khoảng 400 câu truy vấn cơ sở dữ liệu (N+1 query).
2. Hàm sinh bảng lương hàng loạt `action_sinh_bang_luong_thang` thực hiện `self.search(...)` trong vòng lặp nhân viên để kiểm tra xem bản ghi bảng lương nháp đã tồn tại chưa.

Việc này làm chậm đáng kể giao diện người dùng và gây áp lực lớn lên PostgreSQL khi số lượng nhân viên tăng lên. Việc áp dụng các nguyên tắc tối ưu hóa ECC (`postgres-patterns`, `performance-optimization`) giúp gộp các truy vấn này thành các câu lệnh SQL đơn lẻ, cải thiện hiệu năng gấp nhiều lần.

## Current state

- File liên quan:
  - `addons/cham_cong_tinh_luong/models/bang_luong.py` — Lớp `BangLuong`.

Đoạn mã hiện tại của `action_sinh_bang_luong_thang` (dòng 343–365):
```python
    @api.model
    def action_sinh_bang_luong_thang(self, thang, nam, nhan_vien_ids=None):
        employees = self.env['nhan_vien'].search([])
        if nhan_vien_ids:
            employees = employees.filtered(lambda emp: emp.id in nhan_vien_ids)

        created = 0
        updated = 0
        skipped = 0
        messages = []
        for employee in employees:
            draft = self.search([
                ('nhan_vien_id', '=', employee.id),
                ('thang', '=', str(thang)),
                ('nam', '=', int(nam)),
            ], limit=1)
```

Đoạn mã hiện tại của `_compute_bang_luong` (dòng 301–328):
```python
    @api.depends('nhan_vien_id', 'thang', 'nam', 'ngay_tao', 'he_so_tang_ca')
    def _compute_bang_luong(self):
        for record in self:
            values = record._get_payroll_values()
            record.so_ngay_di_lam = values['so_ngay_di_lam']
            # ...
```

## Commands you will need

| Purpose   | Command                                                                            | Expected on success |
|-----------|------------------------------------------------------------------------------------|---------------------|
| Upgrade   | `docker exec -u 0 odoo15 odoo -d MaiLan -u cham_cong_tinh_luong --stop-after-init` | exit 0              |
| Restart   | `docker restart odoo15`                                                            | Container restarts  |

## Scope

**In scope**:
- `addons/cham_cong_tinh_luong/models/bang_luong.py`

**Out of scope**:
- Bất kỳ thay đổi cấu trúc bảng hoặc cơ sở dữ liệu nào.

## Steps

### Step 1: Tối ưu hóa hàm `action_sinh_bang_luong_thang` bằng cách pre-fetch bảng lương

Chỉnh sửa tệp `addons/cham_cong_tinh_luong/models/bang_luong.py` để tìm kiếm toàn bộ các bảng lương hiện có trước khi đi vào vòng lặp nhân viên:

```python
    @api.model
    def action_sinh_bang_luong_thang(self, thang, nam, nhan_vien_ids=None):
        self._check_payroll_manager_rights()
        employees = self.env['nhan_vien'].search([])
        if nhan_vien_ids:
            employees = employees.filtered(lambda emp: emp.id in nhan_vien_ids)

        # Pre-fetch existing payroll sheets for this month & year
        existing_payrolls = self.search([
            ('nhan_vien_id', 'in', employees.ids),
            ('thang', '=', str(thang)),
            ('nam', '=', int(nam)),
        ])
        payroll_map = {p.nhan_vien_id.id: p for p in existing_payrolls}

        created = 0
        updated = 0
        skipped = 0
        messages = []
        for employee in employees:
            draft = payroll_map.get(employee.id)
            payroll = draft or self.new({
                'nhan_vien_id': employee.id,
                'thang': str(thang),
                'nam': int(nam),
                'ngay_tao': fields.Date.context_today(self),
            })
            # ...
```

### Step 2: Tối ưu hóa `_compute_bang_luong` và các hàm phụ trợ để xử lý batch

Cấu trúc lại cơ chế lấy cấu hình lương, chấm công và khen thưởng/kỷ luật để nạp hàng loạt (pre-fetch) khi chạy `_compute_bang_luong` trên nhiều dòng ghi:

1. Thêm tham số tùy chọn `prefetched_data` cho hàm `_get_payroll_values(self, require_config=False, prefetched_data=None)`.
2. Trong hàm `_compute_bang_luong`, trước khi lặp qua `self`, hãy chuẩn bị dữ liệu:
   - Gom tất cả `employee_ids`.
   - Tìm kiếm hàng loạt cấu hình lương (`cau_hinh_luong`), chấm công (`cham_cong`), và khen thưởng kỷ luật (`khen_thuong_ky_luat`).
   - Phân nhóm dữ liệu này theo `nhan_vien_id.id` vào các từ điển Python.
   - Truyền từ điển này vào hàm `_get_payroll_values`.

Cập nhật mã nguồn `_compute_bang_luong` và `_get_payroll_values`:

```python
    @api.depends('nhan_vien_id', 'thang', 'nam', 'ngay_tao', 'he_so_tang_ca')
    def _compute_bang_luong(self):
        # Thu thập thông tin để batch fetch
        employee_ids = self.mapped('nhan_vien_id').ids
        prefetched = {}
        
        if len(self) > 1 and employee_ids:
            # Tìm kiếm cấu hình lương hàng loạt
            configs = self.env['cau_hinh_luong'].search([
                ('nhan_vien_id', 'in', employee_ids),
                ('trang_thai', 'in', ['dang_ap_dung', 'ap_dung']),
            ], order='ngay_bat_dau desc, id desc')
            
            # Tìm kiếm tất cả chấm công trong các khoảng thời gian liên quan
            # Để đơn giản, ta tìm min_start và max_end của toàn bộ recordset
            start_dates = []
            end_dates = []
            for record in self:
                if record.thang and record.nam:
                    s, e = record._get_month_range()
                    start_dates.append(s)
                    end_dates.append(e)
            
            if start_dates and end_dates:
                min_start = min(start_dates)
                max_end = max(end_dates)
                
                cham_cong = self.env['cham_cong'].search([
                    ('nhan_vien_id', 'in', employee_ids),
                    ('ngay_cham_cong', '>=', min_start),
                    ('ngay_cham_cong', '<', max_end),
                    ('state', 'in', ['xac_nhan', 'confirmed']),
                ], order='ngay_cham_cong, gio_vao, id')
                
                rewards_disciplines = self.env['khen_thuong_ky_luat'].search([
                    ('nhan_vien_id', 'in', employee_ids),
                    ('ngay_ap_dung', '>=', min_start),
                    ('ngay_ap_dung', '<', max_end),
                ])
                
                # Tổ chức cấu trúc prefetched_data
                prefetched = {
                    'configs': configs,
                    'cham_cong': cham_cong,
                    'rewards_disciplines': rewards_disciplines,
                }

        for record in self:
            values = record._get_payroll_values(prefetched_data=prefetched)
            record.so_ngay_di_lam = values['so_ngay_di_lam']
            record.tong_ngay_cong = values['tong_ngay_cong']
            record.tong_gio_lam = values['tong_gio_lam']
            record.tong_gio_tang_ca = values['tong_gio_tang_ca']
            record.so_ngay_nghi = values['so_ngay_nghi']
            record.luong_co_ban = values['luong_co_ban']
            record.luong_theo_cong = values['luong_theo_cong']
            record.don_gia_gio = values['don_gia_gio']
            record.tien_tang_ca = values['tien_tang_ca']
            record.tong_phu_cap = values['tong_phu_cap']
            record.phu_cap_an_trua = values['phu_cap_an_trua']
            record.phu_cap_xang_xe = values['phu_cap_xang_xe']
            record.phu_cap_trach_nhiem = values['phu_cap_trach_nhiem']
            record.phu_cap_khac = values['phu_cap_khac']
            record.tong_khen_thuong = values['tong_khen_thuong']
            record.tong_ky_luat = values['tong_ky_luat']
            record.tien_bao_hiem = values['tien_bao_hiem']
            record.thue_tncn = values['thue_tncn']
            record.khau_tru_khac = values['khau_tru_khac']
            record.tong_khau_tru = values['tong_khau_tru']
            record.tong_luong = values['tong_luong']
            record.cong_thuc_tinh_luong = values['cong_thuc_tinh_luong']
            record.canh_bao = values['canh_bao']
```

Cập nhật hàm `_get_payroll_values` (dòng 192):

```python
    def _get_payroll_values(self, require_config=False, prefetched_data=None):
        self.ensure_one()
        values = {
            'so_ngay_di_lam': 0.0,
            'tong_ngay_cong': 0.0,
            'tong_gio_lam': 0.0,
            'tong_gio_tang_ca': 0.0,
            'so_ngay_nghi': 0.0,
            'luong_co_ban': 0.0,
            'luong_theo_cong': 0.0,
            'don_gia_gio': 0.0,
            'tien_tang_ca': 0.0,
            'tong_phu_cap': 0.0,
            'phu_cap_an_trua': 0.0,
            'phu_cap_xang_xe': 0.0,
            'phu_cap_trach_nhiem': 0.0,
            'phu_cap_khac': 0.0,
            'tong_khen_thuong': 0.0,
            'tong_ky_luat': 0.0,
            'tien_bao_hiem': 0.0,
            'thue_tncn': 0.0,
            'khau_tru_khac': 0.0,
            'tong_khau_tru': 0.0,
            'tong_luong': 0.0,
            'cong_thuc_tinh_luong': '',
            'canh_bao': '',
            'cham_cong_ids': [(5, 0, 0)],
        }

        if not self.nhan_vien_id or not self.thang or not self.nam:
            return values

        start_date, end_date = self._get_month_range()
        payroll_date = self.ngay_tao or start_date

        # Lấy Config (Cấu hình lương)
        config = self.env['cau_hinh_luong']
        if prefetched_data and 'configs' in prefetched_data:
            # Lọc trong bộ nhớ
            emp_configs = prefetched_data['configs'].filtered(lambda c: c.nhan_vien_id.id == self.nhan_vien_id.id)
            for c in emp_configs:
                s_date = c.ngay_bat_dau or date(1900, 1, 1)
                e_date = c.ngay_ket_thuc or date(2999, 12, 31)
                if s_date <= payroll_date <= e_date:
                    config = c
                    break
        else:
            config = self._get_active_salary_config()

        if not config:
            if require_config:
                raise ValidationError('Chưa có cấu hình lương đang áp dụng cho nhân viên này.')
            values['canh_bao'] = 'Chưa có cấu hình lương đang áp dụng cho nhân viên này.'
            return values

        # Lấy Chấm công
        if prefetched_data and 'cham_cong' in prefetched_data:
            cham_cong_records = prefetched_data['cham_cong'].filtered(
                lambda att: att.nhan_vien_id.id == self.nhan_vien_id.id 
                and start_date <= att.ngay_cham_cong < end_date
            )
        else:
            cham_cong_records = self.env['cham_cong'].search([
                ('nhan_vien_id', '=', self.nhan_vien_id.id),
                ('ngay_cham_cong', '>=', start_date),
                ('ngay_cham_cong', '<', end_date),
                ('state', 'in', ['xac_nhan', 'confirmed']),
            ], order='ngay_cham_cong, gio_vao, id')

        values['cham_cong_ids'] = [(6, 0, cham_cong_records.ids)]
        if not cham_cong_records:
            values['canh_bao'] = 'Không có chấm công trong kỳ lương, tổng ngày công = 0.'

        values['so_ngay_di_lam'] = round(sum(cham_cong_records.mapped('so_ngay_cong')), 2)
        values['tong_ngay_cong'] = values['so_ngay_di_lam']
        values['tong_gio_lam'] = round(sum(cham_cong_records.mapped('so_gio_lam')), 2)
        values['tong_gio_tang_ca'] = round(sum(cham_cong_records.mapped('so_gio_tang_ca')), 2)
        values['so_ngay_nghi'] = round(
            len(cham_cong_records.filtered(lambda item: item.trang_thai in ('nghi', 'nghi_co_phep', 'nghi_khong_phep'))),
            2,
        )

        values['luong_co_ban'] = config.luong_co_ban
        values['tong_phu_cap'] = config.tong_phu_cap
        values['phu_cap_an_trua'] = config.phu_cap_an_trua
        values['phu_cap_xang_xe'] = config.phu_cap_xang_xe
        values['phu_cap_trach_nhiem'] = config.phu_cap_trach_nhiem
        values['phu_cap_khac'] = config.phu_cap_khac
        if config.so_ngay_cong_chuan and config.so_gio_cong_chuan:
            values['don_gia_gio'] = round(config.luong_co_ban / config.so_ngay_cong_chuan / config.so_gio_cong_chuan, 2)
        else:
            values['don_gia_gio'] = 0.0
        values['luong_theo_cong'] = round(config.luong_co_ban / 26.0 * values['so_ngay_di_lam'], 2)
        values['tien_tang_ca'] = round(values['don_gia_gio'] * self.he_so_tang_ca * values['tong_gio_tang_ca'], 2)
        values['tien_bao_hiem'] = round(config.luong_co_ban * config.ty_le_bao_hiem / 100.0, 2)
        values['thue_tncn'] = round(config.thue_tncn, 2)
        values['khau_tru_khac'] = round(config.khau_tru_khac, 2)
        values['tong_khau_tru'] = round(
            values['tien_bao_hiem'] + values['thue_tncn'] + values['khau_tru_khac'],
            2,
        )

        # Lấy Khen thưởng / Kỷ luật
        if prefetched_data and 'rewards_disciplines' in prefetched_data:
            emp_rewards_disciplines = prefetched_data['rewards_disciplines'].filtered(
                lambda r: r.nhan_vien_id.id == self.nhan_vien_id.id
                and start_date <= r.ngay_ap_dung < end_date
            )
            tong_khen_thuong = sum(emp_rewards_disciplines.filtered(lambda r: r.loai_quyet_dinh == 'khen_thuong').mapped('so_tien'))
            tong_ky_luat = sum(emp_rewards_disciplines.filtered(lambda r: r.loai_quyet_dinh == 'ky_luat').mapped('so_tien'))
            tong_khen_thuong, tong_ky_luat = round(tong_khen_thuong, 2), round(tong_ky_luat, 2)
        else:
            tong_khen_thuong, tong_ky_luat = self._get_reward_discipline_totals(start_date, end_date)

        values['tong_khen_thuong'] = tong_khen_thuong
        values['tong_ky_luat'] = tong_ky_luat
        values['tong_luong'] = round(
            values['luong_theo_cong']
            + values['tong_phu_cap']
            + values['tong_khen_thuong']
            - values['tong_ky_luat'],
            2,
        )
        values['cong_thuc_tinh_luong'] = (
            'Lương theo ngày công = Lương cơ bản / 26 * Số ngày đi làm thực tế\n'
            'Thực lĩnh = Lương theo ngày công + Tổng phụ cấp + Khen thưởng - Kỷ luật'
        )
        return values
```

**Verify**: Chạy nâng cấp module và khởi động lại Odoo. Thử tải lại danh sách bảng lương hoặc sinh hàng loạt để kiểm chứng số lượng truy vấn SQL giảm đáng kể.

---

## Done criteria

- [ ] Hàm `action_sinh_bang_luong_thang` đã chuyển sang sử dụng pre-fetched dictionary thay vì gọi `search` trong vòng lặp nhân viên.
- [ ] Hàm `_compute_bang_luong` và `_get_payroll_values` nhận tham số `prefetched_data` và lọc trong bộ nhớ thay vì gọi `search` khi có tập dữ liệu lớn.
- [ ] Ứng dụng Odoo nâng cấp thành công mà không báo lỗi runtime hay cú pháp Python.
- [ ] Bảng lương của nhân viên vẫn được tính toán hoàn toàn chính xác như trước.

## STOP conditions

- Trình nâng cấp Odoo báo lỗi biên dịch cú pháp hoặc lỗi cơ sở dữ liệu.
- Số tiền lương tính ra bị sai khác so với phiên bản trước đó.
