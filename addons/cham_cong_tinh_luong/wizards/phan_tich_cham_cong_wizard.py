from datetime import timedelta
from odoo import fields, models
from odoo.addons.cham_cong_tinh_luong.models.nhan_vien_thong_tin_mixin import get_month_range

MAX_DAILY_WORK_HOURS = 10.0
MIN_MONTHLY_WORK_DAYS = 20.0
MAX_MONTHLY_OVERTIME_HOURS = 30.0
MAX_LATE_COUNT_THRESHOLD = 3


class PhanTichChamCongWizard(models.TransientModel):
    _name = 'phan_tich_cham_cong_wizard'
    _description = 'Phân tích cảnh báo chấm công'

    thang = fields.Selection([(str(i), 'Tháng %s' % i) for i in range(1, 13)], required=True, default=lambda self: str(fields.Date.context_today(self).month))
    nam = fields.Integer(required=True, default=lambda self: fields.Date.context_today(self).year)
    nhan_vien_id = fields.Many2one('nhan_vien', string='Nhân viên')
    xoa_canh_bao_cu = fields.Boolean(string='Xóa cảnh báo cũ', default=True)

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

        start_date, end_date = get_month_range(self.thang, self.nam)

        for employee in employees:
            attendances = self.env['cham_cong'].search([
                ('nhan_vien_id', '=', employee.id),
                ('ngay_cham_cong', '>=', start_date),
                ('ngay_cham_cong', '<', end_date),
                ('state', '=', 'xac_nhan'),
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
                if att.so_gio_lam > MAX_DAILY_WORK_HOURS:
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
                    ('nhan_vien_id', '=', employee.id),
                    ('ngay_cham_cong', '=', today),
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
                ('trang_thai', '=', 'dang_ap_dung')
            ], limit=1))
            invalid_attendance = bool(attendances.filtered(lambda line: line.trang_thai != 'nghi' and (not line.gio_vao or not line.gio_ra)))
            salary_unconfirmed = bool(salary_sheet and salary_sheet.state not in ('xac_nhan', 'da_thanh_toan'))

            rule_values = [
                (
                    late_count >= MAX_LATE_COUNT_THRESHOLD,
                    'di_muon_nhieu',
                    'Đi muộn %s lần trong tháng %s/%s.' % (late_count, self.thang, self.nam),
                    'Nhắc nhở nhân viên hoặc kiểm tra ca làm việc.',
                    'trung_binh',
                ),
                (
                    day_count < MIN_MONTHLY_WORK_DAYS,
                    'thieu_cong',
                    'Tổng ngày công chỉ đạt %s ngày trong tháng %s/%s.' % (day_count, self.thang, self.nam),
                    'Kiểm tra dữ liệu chấm công, lịch nghỉ hoặc tình trạng làm việc.',
                    'cao',
                ),
                (
                    overtime_hours > MAX_MONTHLY_OVERTIME_HOURS,
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
