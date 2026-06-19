# Plan 002: Tối ưu hiệu năng bằng cách gộp tạo cảnh báo (Bulk Create) trong Wizard phân tích chấm công

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise.
>
> **Drift check (run first)**: `git diff --stat 1f284728..HEAD -- addons/cham_cong_tinh_luong/wizards/phan_tich_cham_cong_wizard.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M (3-4 hours)
- **Risk**: MED (Requires careful aggregation of list values and ensuring constraints)
- **Depends on**: plans/001-*.md
- **Category**: perf
- **Planned at**: commit `1f284728`, 2026-06-19

## Why this matters

Trong Wizard phân tích chấm công (`phan_tich_cham_cong_wizard`), hệ thống duyệt qua từng bản ghi chấm công của từng nhân viên để tìm lỗi và tạo cảnh báo (`canh_bao_cham_cong`).

Hiện tại, việc gọi `Alert.create({...})` đang được thực hiện ngay lập tức trong các vòng lặp `for att in attendances:` và `for condition, ... in rule_values:`.
*   **Hậu quả**: Nếu một tháng có 100 nhân viên và phát sinh trung bình 3-5 lỗi/nhân viên, Odoo sẽ phải thực hiện hơn 500 câu lệnh `INSERT INTO` riêng lẻ tới PostgreSQL. Việc này gây nghẽn nghiêm trọng (database bottleneck) và làm chậm đáng kể thời gian phản hồi của wizard.
*   **Giải pháp**: Tận dụng tính năng tạo hàng loạt của Odoo (`@api.model_create_multi` trên hàm `create`) bằng cách gom tất cả các từ điển dữ liệu (`vals`) vào một danh sách lớn và chỉ gọi `Alert.create(alerts_to_create)` đúng 1 lần duy nhất ở cuối hàm xử lý.

## Current state

- File liên quan:
  - `addons/cham_cong_tinh_luong/wizards/phan_tich_cham_cong_wizard.py` — Chứa hàm `action_phan_tich_canh_bao`.

Ví dụ về cách viết cũ tạo bản ghi đơn lẻ trong vòng lặp (dòng 52-60):
```python
                # 1. Đi muộn
                if att.trang_thai == 'di_muon':
                    Alert.create({
                        'nhan_vien_id': employee.id,
                        'thang': self.thang,
                        'nam': self.nam,
                        'loai_canh_bao': 'di_muon',
                        'muc_do': 'trung_binh',
                        'noi_dung': 'Đi muộn ngày %s (vào lúc %s).' % (att.ngay_cham_cong.strftime('%d/%m/%Y'), (att.gio_vao + timedelta(hours=7)).strftime('%H:%M') if att.gio_vao else '?'),
                        'goi_y_xu_ly': 'Nhắc nhở đi làm đúng giờ.',
                    })
                    created += 1
```

## Commands you will need

| Purpose   | Command                                                                            | Expected on success |
|-----------|------------------------------------------------------------------------------------|---------------------|
| Upgrade   | `docker exec -u 0 odoo15 odoo -d MaiLan -u cham_cong_tinh_luong --stop-after-init` | exit 0              |
| Restart   | `docker restart odoo15`                                                            | Container restarts  |

## Scope

**In scope**:
- `addons/cham_cong_tinh_luong/wizards/phan_tich_cham_cong_wizard.py`

**Out of scope**:
- Các file khác trong module.

## Steps

### Step 1: Thay thế logic `create` đơn lẻ bằng cách gom danh sách `alerts_to_create`

Cấu trúc lại phương thức `action_phan_tich_canh_bao` trong `addons/cham_cong_tinh_luong/wizards/phan_tich_cham_cong_wizard.py` theo mẫu sau:

1.  Khai báo mảng chứa `alerts_to_create = []` ở đầu hàm.
2.  Thay thế mọi lời gọi `Alert.create({ ... })` bằng `alerts_to_create.append({ ... })`.
3.  Thay vì bỏ qua điều kiện trùng lặp bằng cách tìm trực tiếp (`Alert.search(...)`) giữa chừng (gây N+1 query), hãy lấy ra tập hợp cảnh báo đã tồn tại trước (nếu không xóa cảnh báo cũ) hoặc lọc trong bộ nhớ tạm để tránh trùng lặp.
4.  Gọi `Alert.create(alerts_to_create)` ở cuối hàm.

Đoạn mã đề xuất tái cấu trúc:
```python
    def action_phan_tich_canh_bao(self):
        self.ensure_one()
        Alert = self.env['canh_bao_cham_cong']
        employee_model = self.env['nhan_vien']
        Salary = self.env['bang_luong']
        from datetime import timedelta

        old_domain = [('thang', '=', self.thang), ('nam', '=', self.nam)]
        if self.nhan_vien_id:
            old_domain.append(('nhan_vien_id', '=', self.nhan_vien_id.id))
        if self.xoa_canh_bao_cu:
            Alert.search(old_domain).unlink()

        employees = self.nhan_vien_id or employee_model.search([])
        alerts_to_create = []

        # Lấy danh sách các cảnh báo hiện tại trong kỳ để kiểm tra trùng lặp (tránh gọi search nhiều lần trong loop)
        existing_alerts = set()
        if not self.xoa_canh_bao_cu:
            alerts_in_db = Alert.search([('thang', '=', self.thang), ('nam', '=', self.nam)])
            for a in alerts_in_db:
                existing_alerts.add((a.nhan_vien_id.id, a.loai_canh_bao))

        for employee in employees:
            start_date, end_date = Salary.new({
                'nhan_vien_id': employee.id,
                'thang': self.thang,
                'nam': self.nam,
            })._get_month_range()
            attendances = self.env['cham_cong'].search([
                ('nhan_vien_id', '=', employee.id),
                ('ngay_cham_cong', '>=', start_date),
                ('ngay_cham_cong', '<', end_date),
                ('state', 'in', ['xac_nhan', 'confirmed']),
            ])
            late_count = len(attendances.filtered(lambda line: line.trang_thai == 'di_muon'))
            day_count = round(sum(attendances.mapped('so_ngay_cong')), 2)
            overtime_hours = sum(attendances.mapped('so_gio_tang_ca'))

            # Daily scans
            for att in attendances:
                # 1. Đi muộn
                if att.trang_thai == 'di_muon':
                    alerts_to_create.append({
                        'nhan_vien_id': employee.id,
                        'thang': self.thang,
                        'nam': self.nam,
                        'loai_canh_bao': 'di_muon',
                        'muc_do': 'trung_binh',
                        'noi_dung': 'Đi muộn ngày %s (vào lúc %s).' % (att.ngay_cham_cong.strftime('%d/%m/%Y'), (att.gio_vao + timedelta(hours=7)).strftime('%H:%M') if att.gio_vao else '?'),
                        'goi_y_xu_ly': 'Nhắc nhở đi làm đúng giờ.',
                    })

                # 2. Về sớm
                if att.gio_ra and att.trang_thai not in ('nghi', 'nghi_co_phep', 'nghi_khong_phep', 'nua_ngay'):
                    local_ra = att.gio_ra + timedelta(hours=7)
                    is_early = False
                    limit_time_str = ""
                    if att.ca_lam_viec == 'sang':
                        if local_ra.hour < 12:
                            is_early = True
                            limit_time_str = "12:00"
                    elif att.ca_lam_viec == 'toi':
                        if local_ra.hour < 22:
                            is_early = True
                            limit_time_str = "22:00"
                    else:
                        if local_ra.hour < 17:
                            is_early = True
                            limit_time_str = "17:00"
                    if is_early:
                        alerts_to_create.append({
                            'nhan_vien_id': employee.id,
                            'thang': self.thang,
                            'nam': self.nam,
                            'loai_canh_bao': 've_som',
                            'muc_do': 'trung_binh',
                            'noi_dung': 'Về sớm ngày %s (ra lúc %s, quy định %s).' % (att.ngay_cham_cong.strftime('%d/%m/%Y'), local_ra.strftime('%H:%M'), limit_time_str),
                            'goi_y_xu_ly': 'Nhắc nhở tuân thủ giờ ra về.',
                        })

                # 3. Thiếu giờ ra
                if att.gio_vao and not att.gio_ra:
                    today = fields.Date.context_today(self)
                    if att.ngay_cham_cong < today:
                        alerts_to_create.append({
                            'nhan_vien_id': employee.id,
                            'thang': self.thang,
                            'nam': self.nam,
                            'loai_canh_bao': 'thieu_gio_ra',
                            'muc_do': 'cao',
                            'noi_dung': 'Thiếu giờ ra ngày %s (vào lúc %s).' % (att.ngay_cham_cong.strftime('%d/%m/%Y'), (att.gio_vao + timedelta(hours=7)).strftime('%H:%M')),
                            'goi_y_xu_ly': 'Yêu cầu nhân viên bổ sung giờ ra.',
                        })

                # 4. Làm quá giờ
                if att.so_gio_lam > 10.0:
                    alerts_to_create.append({
                        'nhan_vien_id': employee.id,
                        'thang': self.thang,
                        'nam': self.nam,
                        'loai_canh_bao': 'lam_qua_gio',
                        'muc_do': 'cao',
                        'noi_dung': 'Làm quá giờ ngày %s (%s giờ).' % (att.ngay_cham_cong.strftime('%d/%m/%Y'), att.so_gio_lam),
                        'goi_y_xu_ly': 'Kiểm tra lý do tăng ca quá quy định.',
                    })

            # 5. Chấm công trùng ngày
            date_counts = {}
            for att in attendances:
                date_counts[att.ngay_cham_cong] = date_counts.get(att.ngay_cham_cong, 0) + 1
            for att_date, count in date_counts.items():
                if count > 1:
                    alerts_to_create.append({
                        'nhan_vien_id': employee.id,
                        'thang': self.thang,
                        'nam': self.nam,
                        'loai_canh_bao': 'trung_ngay',
                        'muc_do': 'cao',
                        'noi_dung': 'Trùng ngày chấm công: %s (%s bản ghi).' % (att_date.strftime('%d/%m/%Y'), count),
                        'goi_y_xu_ly': 'Xóa hoặc gộp bản ghi chấm công trùng lặp.',
                    })

            # 6. Chưa chấm công hôm nay
            today = fields.Date.context_today(self)
            if int(self.nam) == today.year and int(self.thang) == today.month:
                today_att = self.env['cham_cong'].search([
                    ('ngay_cham_cong', '=', today),
                    ('nhan_vien_id', '=', employee.id),
                ], limit=1)
                if not today_att and today.weekday() < 5:
                    alerts_to_create.append({
                        'nhan_vien_id': employee.id,
                        'thang': self.thang,
                        'nam': self.nam,
                        'loai_canh_bao': 'chua_cham_cong',
                        'muc_do': 'cao',
                        'noi_dung': 'Chưa chấm công hôm nay (%s).' % today.strftime('%d/%m/%Y'),
                        'goi_y_xu_ly': 'Nhắc nhở nhân viên chấm công.',
                    })

            salary_sheet = Salary.search([
                ('nhan_vien_id', '=', employee.id),
                ('thang', '=', self.thang),
                ('nam', '=', self.nam),
            ], limit=1)
            if salary_sheet:
                salary_values = salary_sheet._get_payroll_values(require_config=False)
            else:
                salary_values = Salary.new({'nhan_vien_id': employee.id, 'thang': self.thang, 'nam': self.nam})._get_payroll_values(require_config=False)

            has_config = bool(self.env['cau_hinh_luong'].search([
                ('nhan_vien_id', '=', employee.id),
                ('trang_thai', 'in', ['dang_ap_dung', 'ap_dung'])
            ], limit=1))
            invalid_attendance = bool(attendances.filtered(lambda line: line.trang_thai != 'nghi' and (not line.gio_vao or not line.gio_ra)))
            salary_unconfirmed = bool(salary_sheet and salary_sheet.state not in ('xac_nhan', 'confirmed', 'da_thanh_toan'))

            rule_values = [
                (
                    late_count >= 3,
                    'di_muon_nhieu',
                    'Đi muộn %s lần trong tháng %s/%s.' % (late_count, self.thang, self.nam),
                    'Nhắc nhở nhân viên hoặc kiểm tra ca làm việc.',
                    'trung_binh',
                ),
                (
                    day_count < 20,
                    'thieu_cong',
                    'Tổng ngày công chỉ đạt %s ngày trong tháng %s/%s.' % (day_count, self.thang, self.nam),
                    'Kiểm tra dữ liệu chấm công, lịch nghỉ hoặc tình trạng làm việc.',
                    'cao',
                ),
                (
                    overtime_hours > 30,
                    'tang_ca_qua_nhieu',
                    'Tổng giờ tăng ca là %s giờ trong tháng %s/%s.' % (round(overtime_hours, 2), self.thang, self.nam),
                    'Kiểm tra phân bổ công việc và sức khỏe nhân viên.',
                    'cao',
                ),
                (
                    salary_values.get('tong_luong', 0.0) and salary_values.get('luong_co_ban', 0.0) and salary_values.get('tong_luong', 0.0) < salary_values.get('luong_co_ban', 0.0) * 0.7,
                    'luong_thap_bat_thuong',
                    'Tổng lương thực nhận thấp bất thường: %s.' % salary_values.get('tong_luong', 0.0),
                    'Kiểm tra ngày công, khấu trừ và dữ liệu chấm công.',
                    'cao',
                ),
                (
                    has_config and not attendances,
                    'thieu_du_lieu_cham_cong',
                    'Nhân viên có cấu hình lương nhưng không có chấm công trong tháng %s/%s.' % (self.thang, self.nam),
                    'Cần bổ sung dữ liệu công trước khi tính lương.',
                    'cao',
                ),
                (
                    salary_unconfirmed,
                    'bang_luong_chua_xac_nhan',
                    'Bảng lương của nhân viên chưa được xác nhận trong tháng %s/%s.' % (self.thang, self.nam),
                    'Kiểm tra quy trình duyệt bảng lương và xác nhận dữ liệu.',
                    'trung_binh',
                ),
                (
                    invalid_attendance,
                    'du_lieu_cong_khong_hop_le',
                    'Tồn tại bản ghi chấm công chưa đầy đủ dữ liệu hoặc không hợp lệ trong tháng %s/%s.' % (self.thang, self.nam),
                    'Rà soát giờ vào/ra, ca làm việc và quy trình nhập công.',
                    'cao',
                ),
            ]
            for condition, code, content, advice, level in rule_values:
                if condition:
                    # Kiểm tra bộ nhớ tạm thay vì gọi search DB
                    if (employee.id, code) in existing_alerts:
                        continue
                    alerts_to_create.append({
                        'nhan_vien_id': employee.id,
                        'thang': self.thang,
                        'nam': self.nam,
                        'loai_canh_bao': code,
                        'muc_do': level,
                        'noi_dung': content,
                        'goi_y_xu_ly': advice,
                    })

        # Thực hiện bulk create một lần duy nhất
        if alerts_to_create:
            Alert.create(alerts_to_create)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Phân tích hoàn tất',
                'message': 'Đã tạo %s cảnh báo.' % len(alerts_to_create),
                'sticky': False,
            }
        }
```

**Verify**: Chạy nâng cấp module và khởi động lại Odoo. Chạy thử wizard và xác nhận tốc độ thực thi nhanh hơn đáng kể.

---

## Done criteria

- [ ] Toàn bộ hàm `action_phan_tich_canh_bao` không còn chứa lệnh `Alert.create` trong vòng lặp nhân viên.
- [ ] Odoo nâng cấp module và chạy thành công mà không báo lỗi.
