# -*- coding: utf-8 -*-

from datetime import date

from odoo import api, fields, models


class DashboardChamCongLuong(models.Model):
    _name = 'dashboard_cham_cong_luong'
    _description = 'Dashboard Chấm công và Tính lương'
    _order = 'nam desc, thang desc, id desc'

    name = fields.Char(string='Tên dashboard', required=True, default='Dashboard chấm công')
    thang = fields.Selection(
        [(str(i), 'Tháng %s' % i) for i in range(1, 13)],
        string='Tháng',
        required=True,
        default=lambda self: str(fields.Date.context_today(self).month),
    )
    nam = fields.Integer(
        string='Năm',
        required=True,
        default=lambda self: fields.Date.context_today(self).year,
    )
    tong_nhan_vien = fields.Integer(string='Tổng số nhân viên', compute='_compute_dashboard')
    so_nhan_vien_da_cham_cong_hom_nay = fields.Integer(string='Đã chấm công hôm nay', compute='_compute_dashboard')
    so_nhan_vien_chua_cham_cong_hom_nay = fields.Integer(string='Chưa chấm công hôm nay', compute='_compute_dashboard')
    so_nhan_vien_da_cham_cong = fields.Integer(string='Số nhân viên đã chấm công', compute='_compute_dashboard')
    tong_cham_cong = fields.Integer(string='Tổng bản ghi chấm công', compute='_compute_dashboard')
    tong_ngay_cong = fields.Float(string='Tổng ngày công', compute='_compute_dashboard')
    tong_gio_lam = fields.Float(string='Tổng giờ làm', compute='_compute_dashboard')
    tong_gio_tang_ca = fields.Float(string='Tổng giờ tăng ca', compute='_compute_dashboard')
    tong_tang_ca = fields.Integer(string='Số lượt tăng ca', compute='_compute_dashboard')
    so_luot_di_muon = fields.Integer(string='Số lượt đi muộn', compute='_compute_dashboard')
    so_ngay_nghi = fields.Integer(string='Số ngày nghỉ', compute='_compute_dashboard')
    tong_quy_luong = fields.Float(string='Tổng quỹ lương', compute='_compute_dashboard')
    tong_bao_hiem = fields.Float(string='Tổng tiền bảo hiểm', compute='_compute_dashboard')
    tong_phu_cap = fields.Float(string='Tổng phụ cấp', compute='_compute_dashboard')
    so_bang_luong_thang = fields.Integer(string='Số bảng lương trong tháng', compute='_compute_dashboard')
    bang_luong_da_tinh = fields.Integer(string='Bảng lương đã tính', compute='_compute_dashboard')
    bang_luong_xac_nhan = fields.Integer(string='Bảng lương đã xác nhận', compute='_compute_dashboard')
    bang_luong_chua_xac_nhan = fields.Integer(string='Bảng lương chưa xác nhận', compute='_compute_dashboard')
    bang_luong_da_thanh_toan = fields.Integer(string='Bảng lương đã thanh toán', compute='_compute_dashboard')
    tong_canh_bao = fields.Integer(string='Cảnh báo thông minh', compute='_compute_dashboard')
    so_canh_bao_cao = fields.Integer(string='Cảnh báo mức cao', compute='_compute_dashboard')

    @api.depends('thang', 'nam')
    def _compute_dashboard(self):
        employee_model = self.env['nhan_vien']
        attendance_model = self.env['cham_cong']
        salary_model = self.env['bang_luong']
        warning_model = self.env['canh_bao_cham_cong']
        current_employee = self.env['nhan_vien'].search([('user_id', '=', self.env.uid)], limit=1)
        scope_mine = self.env.context.get('dashboard_scope') == 'mine'

        for record in self:
            start_date, end_date = record._get_month_range()
            attendance_domain = [
                ('ngay_cham_cong', '>=', start_date),
                ('ngay_cham_cong', '<', end_date),
            ]
            salary_domain = [
                ('thang', '=', record.thang),
                ('nam', '=', record.nam),
            ]
            warning_domain = [
                ('thang', '=', record.thang),
                ('nam', '=', record.nam),
            ]
            if scope_mine and not current_employee:
                record.tong_nhan_vien = 0
                record.so_nhan_vien_da_cham_cong_hom_nay = 0
                record.so_nhan_vien_chua_cham_cong_hom_nay = 0
                record.so_nhan_vien_da_cham_cong = 0
                record.tong_cham_cong = 0
                record.tong_ngay_cong = 0.0
                record.tong_gio_lam = 0.0
                record.tong_gio_tang_ca = 0.0
                record.tong_tang_ca = 0
                record.so_luot_di_muon = 0
                record.so_ngay_nghi = 0
                record.tong_quy_luong = 0.0
                record.tong_bao_hiem = 0.0
                record.tong_phu_cap = 0.0
                record.so_bang_luong_thang = 0
                record.bang_luong_da_tinh = 0
                record.bang_luong_xac_nhan = 0
                record.bang_luong_chua_xac_nhan = 0
                record.bang_luong_da_thanh_toan = 0
                record.tong_canh_bao = 0
                record.so_canh_bao_cao = 0
                continue
            if scope_mine and current_employee:
                attendance_domain.append(('nhan_vien_id', '=', current_employee.id))
                salary_domain.append(('nhan_vien_id', '=', current_employee.id))
                warning_domain.append(('nhan_vien_id', '=', current_employee.id))

            attendance_total = attendance_model.search_count(attendance_domain)
            attendance_aggregates = attendance_model.read_group(
                attendance_domain,
                ['so_gio_lam:sum', 'so_gio_tang_ca:sum', 'so_ngay_cong:sum'],
                [],
            )
            attendance_totals = attendance_aggregates[0] if attendance_aggregates else {}
            salary_total = salary_model.search_count(salary_domain)
            salary_aggregates = salary_model.read_group(
                salary_domain,
                ['tong_luong:sum', 'tien_bao_hiem:sum', 'tong_phu_cap:sum'],
                [],
            )
            salary_totals = salary_aggregates[0] if salary_aggregates else {}
            warnings_count = warning_model.search_count(warning_domain)

            today = fields.Date.context_today(self)
            if scope_mine and current_employee:
                today_att = attendance_model.search([
                    ('ngay_cham_cong', '=', today),
                    ('nhan_vien_id', '=', current_employee.id),
                    ('state', 'in', ['xac_nhan', 'confirmed', 'nhap', 'draft'])
                ], limit=1)
                record.so_nhan_vien_da_cham_cong_hom_nay = 1 if today_att else 0
                record.so_nhan_vien_chua_cham_cong_hom_nay = 0 if today_att else 1
            else:
                today_att = attendance_model.search([
                    ('ngay_cham_cong', '=', today),
                    ('state', 'in', ['xac_nhan', 'confirmed', 'nhap', 'draft'])
                ])
                today_employee_ids = today_att.mapped('nhan_vien_id').ids
                record.so_nhan_vien_da_cham_cong_hom_nay = len(set(today_employee_ids))
                total_emp = employee_model.search_count([])
                record.so_nhan_vien_chua_cham_cong_hom_nay = max(0, total_emp - record.so_nhan_vien_da_cham_cong_hom_nay)

            if scope_mine and current_employee:
                record.tong_nhan_vien = 1
            else:
                record.tong_nhan_vien = employee_model.search_count([])
            record.so_nhan_vien_da_cham_cong = len(attendance_model.read_group(attendance_domain, ['nhan_vien_id'], ['nhan_vien_id']))
            record.tong_cham_cong = attendance_total
            record.tong_ngay_cong = round(attendance_totals.get('so_ngay_cong', 0.0) or 0.0, 2)
            record.tong_gio_lam = round(attendance_totals.get('so_gio_lam', 0.0) or 0.0, 2)
            record.tong_gio_tang_ca = round(attendance_totals.get('so_gio_tang_ca', 0.0) or 0.0, 2)
            record.tong_tang_ca = attendance_model.search_count(attendance_domain + [('so_gio_tang_ca', '>', 0)])
            record.so_luot_di_muon = attendance_model.search_count(attendance_domain + [('trang_thai', '=', 'di_muon')])
            record.so_ngay_nghi = attendance_model.search_count(attendance_domain + [('trang_thai', 'in', ['nghi', 'nghi_co_phep', 'nghi_khong_phep'])])
            record.so_bang_luong_thang = salary_total
            record.tong_quy_luong = round(salary_totals.get('tong_luong', 0.0) or 0.0, 2)
            record.tong_bao_hiem = round(salary_totals.get('tien_bao_hiem', 0.0) or 0.0, 2)
            record.tong_phu_cap = round(salary_totals.get('tong_phu_cap', 0.0) or 0.0, 2)
            record.bang_luong_da_tinh = salary_model.search_count(salary_domain + [('state', 'in', ['da_tinh', 'computed'])])
            record.bang_luong_xac_nhan = salary_model.search_count(salary_domain + [('state', 'in', ['xac_nhan', 'confirmed'])])
            record.bang_luong_da_thanh_toan = salary_model.search_count(salary_domain + [('state', '=', 'da_thanh_toan')])
            record.bang_luong_chua_xac_nhan = salary_model.search_count(salary_domain + [('state', 'not in', ['xac_nhan', 'confirmed', 'da_thanh_toan'])])
            record.tong_canh_bao = warnings_count
            record.so_canh_bao_cao = warning_model.search_count(warning_domain + [('muc_do', '=', 'cao')])

    def _get_month_range(self):
        self.ensure_one()
        month = int(self.thang)
        year = self.nam
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        return start_date, end_date

    def _build_action(self, xmlid, domain=None, context=None):
        self.ensure_one()
        action = self.env.ref(xmlid).read()[0]
        if domain is not None:
            action['domain'] = domain
        if context:
            merged_context = dict(self.env.context, **context)
            # Không kế thừa các cờ UI từ dashboard/form hiện tại sang action mới.
            # Nếu không, các action danh sách sẽ bị ẩn nút Create/Add dù ACL vẫn cho phép.
            for key in ('create', 'edit', 'delete'):
                merged_context.pop(key, None)
            action['context'] = merged_context
        return action

    def _open_payroll_list(self, extra_domain=None, action_xmlid='cham_cong_tinh_luong.action_bang_luong'):
        self.ensure_one()
        domain = [('thang', '=', self.thang), ('nam', '=', self.nam)]
        if extra_domain:
            domain.extend(extra_domain)
        return self._build_action(
            action_xmlid,
            domain=domain,
            context={'search_default_filter_month': 1},
        )

    def action_refresh_dashboard(self):
        today = fields.Date.context_today(self)
        self.write({
            'thang': str(today.month),
            'nam': today.year,
        })
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_open_cham_cong(self):
        self.ensure_one()
        start_date, end_date = self._get_month_range()
        return self._build_action(
            'cham_cong_tinh_luong.action_thong_ke_cham_cong',
            domain=[('ngay_cham_cong', '>=', start_date), ('ngay_cham_cong', '<', end_date)],
            context={'search_default_filter_confirmed': 1},
        )

    def action_create_cham_cong(self):
        self.ensure_one()
        action = self.env.ref('cham_cong_tinh_luong.action_cham_cong').read()[0]
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('cham_cong_tinh_luong.view_cham_cong_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = dict(self.env.context, form_view_initial_mode='edit')
        return action

    def action_open_import_cham_cong(self):
        self.ensure_one()
        return self.env.ref('cham_cong_tinh_luong.action_import_cham_cong_wizard').read()[0]

    def action_open_phan_tich_canh_bao(self):
        self.ensure_one()
        return self.env.ref('cham_cong_tinh_luong.action_phan_tich_canh_bao_wizard').read()[0]

    def action_open_bang_luong(self):
        return self._open_payroll_list()

    def action_open_canh_bao(self):
        self.ensure_one()
        return self._build_action(
            'cham_cong_tinh_luong.action_canh_bao_cham_cong',
            domain=[('thang', '=', self.thang), ('nam', '=', self.nam)],
        )

    def action_open_thong_ke_luong(self):
        return self._open_payroll_list(action_xmlid='cham_cong_tinh_luong.action_thong_ke_bang_luong')

    def action_open_bang_luong_list(self):
        return self._open_payroll_list()

    def action_open_in_phieu_luong_pdf(self):
        return self._open_payroll_list(action_xmlid='cham_cong_tinh_luong.action_in_phieu_luong_pdf')

    def action_open_bang_luong_da_tinh(self):
        return self._open_payroll_list([('state', 'in', ['da_tinh', 'computed'])])

    def action_open_bang_luong_da_xac_nhan(self):
        return self._open_payroll_list([('state', 'in', ['xac_nhan', 'confirmed'])])

    def action_open_bang_luong_chua_xac_nhan(self):
        return self._open_payroll_list([('state', 'not in', ['xac_nhan', 'confirmed', 'da_thanh_toan', 'huy', 'cancel'])])

    def action_open_bang_luong_da_thanh_toan(self):
        return self._open_payroll_list([('state', '=', 'da_thanh_toan')])

    def action_open_tong_quy_luong(self):
        return self._open_payroll_list()

    def action_open_tong_phu_cap(self):
        return self._open_payroll_list()

    def action_open_tong_bao_hiem(self):
        return self._open_payroll_list()

    def action_open_cau_hinh_luong(self):
        self.ensure_one()
        return self._build_action('cham_cong_tinh_luong.action_cau_hinh_luong')

    def action_open_xuat_bang_luong(self):
        self.ensure_one()
        return self.env.ref('cham_cong_tinh_luong.action_xuat_bang_luong_wizard').read()[0]

    def action_open_sinh_bang_luong(self):
        self.ensure_one()
        return self.env.ref('cham_cong_tinh_luong.action_sinh_bang_luong_wizard').read()[0]

    def action_open_my_dashboard(self):
        self.ensure_one()
        return self._build_action(
            'cham_cong_tinh_luong.action_dashboard_cua_toi',
            context={'dashboard_scope': 'mine'},
        )

    def action_open_my_cham_cong(self):
        self.ensure_one()
        return self._build_action('cham_cong_tinh_luong.action_cham_cong_cua_toi')

    def action_open_my_bang_luong(self):
        self.ensure_one()
        return self._build_action('cham_cong_tinh_luong.action_bang_luong_cua_toi')

    def action_open_my_canh_bao(self):
        self.ensure_one()
        return self._build_action('cham_cong_tinh_luong.action_canh_bao_cua_toi')

    @api.model
    def open_dashboard_cham_cong(self):
        record = self.search([], limit=1)
        if not record:
            record = self.create({'name': 'Dashboard Chấm công'})
        view = self.env.ref('cham_cong_tinh_luong.dashboard_cham_cong_form_cham_cong_view')
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'res_id': record.id,
            'target': 'current',
        }

    @api.model
    def open_dashboard_tinh_luong(self):
        record = self.search([], limit=1)
        if not record:
            record = self.create({'name': 'Dashboard tính lương'})
        view = self.env.ref('cham_cong_tinh_luong.dashboard_tinh_luong_form_view')
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'res_id': record.id,
            'target': 'current',
        }
