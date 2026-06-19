# -*- coding: utf-8 -*-

from odoo import fields, models


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

        old_domain = [('thang', '=', self.thang), ('nam', '=', self.nam)]
        if self.nhan_vien_id:
            old_domain.append(('nhan_vien_id', '=', self.nhan_vien_id.id))
        if self.xoa_canh_bao_cu:
            Alert.search(old_domain).unlink()

        employees = self.nhan_vien_id or employee_model.search([])
        if self.nhan_vien_id:
            employees = self.nhan_vien_id
        created = 0
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
                    existing = Alert.search([
                        ('nhan_vien_id', '=', employee.id),
                        ('thang', '=', self.thang),
                        ('nam', '=', self.nam),
                        ('loai_canh_bao', '=', code),
                    ], limit=1)
                    if existing:
                        continue
                    Alert.create({
                        'nhan_vien_id': employee.id,
                        'thang': self.thang,
                        'nam': self.nam,
                        'loai_canh_bao': code,
                        'muc_do': level,
                        'noi_dung': content,
                        'goi_y_xu_ly': advice,
                    })
                    created += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Phân tích hoàn tất',
                'message': 'Đã tạo %s cảnh báo.' % created,
                'sticky': False,
            }
        }
