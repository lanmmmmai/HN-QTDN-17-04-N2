from datetime import date

from odoo import api, fields, models
from .nhan_vien_thong_tin_mixin import get_month_range


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
    chart_payroll_history = fields.Text(string='Dữ liệu biểu đồ quỹ lương', compute='_compute_charts')
    chart_warning_distribution = fields.Text(string='Dữ liệu biểu đồ cảnh báo', compute='_compute_charts')

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

            # optimized attendance calculation: group by trang_thai to fetch sums & counts
            att_groups = attendance_model.read_group(
                attendance_domain,
                ['trang_thai', 'so_ngay_cong:sum', 'so_gio_lam:sum', 'so_gio_tang_ca:sum'],
                ['trang_thai']
            )
            so_luot_di_muon = 0
            so_ngay_nghi = 0
            tong_ngay_cong = 0.0
            tong_gio_lam = 0.0
            tong_gio_tang_ca = 0.0
            tong_cham_cong = 0
            for group in att_groups:
                count = group.get('trang_thai_count', 0)
                tong_cham_cong += count
                tong_ngay_cong += group.get('so_ngay_cong', 0.0) or 0.0
                tong_gio_lam += group.get('so_gio_lam', 0.0) or 0.0
                tong_gio_tang_ca += group.get('so_gio_tang_ca', 0.0) or 0.0
                status = group.get('trang_thai')
                if status == 'di_muon':
                    so_luot_di_muon = count
                elif status in ('nghi', 'nghi_co_phep', 'nghi_khong_phep'):
                    so_ngay_nghi += count

            # optimized salary calculation: group by state
            sal_groups = salary_model.read_group(
                salary_domain,
                ['state', 'tong_luong:sum', 'tien_bao_hiem:sum', 'tong_phu_cap:sum'],
                ['state']
            )
            tong_quy_luong = 0.0
            tong_bao_hiem = 0.0
            tong_phu_cap = 0.0
            so_bang_luong_thang = 0
            bang_luong_da_tinh = 0
            bang_luong_xac_nhan = 0
            bang_luong_da_thanh_toan = 0
            bang_luong_chua_xac_nhan = 0
            for group in sal_groups:
                count = group.get('state_count', 0)
                so_bang_luong_thang += count
                tong_quy_luong += group.get('tong_luong', 0.0) or 0.0
                tong_bao_hiem += group.get('tien_bao_hiem', 0.0) or 0.0
                tong_phu_cap += group.get('tong_phu_cap', 0.0) or 0.0
                state = group.get('state')
                if state == 'da_tinh':
                    bang_luong_da_tinh = count
                elif state == 'xac_nhan':
                    bang_luong_xac_nhan = count
                elif state == 'da_thanh_toan':
                    bang_luong_da_thanh_toan = count
                if state not in ('xac_nhan', 'da_thanh_toan'):
                    bang_luong_chua_xac_nhan += count

            # optimized warnings calculation: group by muc_do
            warn_groups = warning_model.read_group(
                warning_domain,
                ['muc_do'],
                ['muc_do']
            )
            tong_canh_bao = 0
            so_canh_bao_cao = 0
            for group in warn_groups:
                count = group.get('muc_do_count', 0)
                tong_canh_bao += count
                if group.get('muc_do') == 'cao':
                    so_canh_bao_cao = count

            today = fields.Date.context_today(self)
            if scope_mine and current_employee:
                today_att_count = attendance_model.search_count([
                    ('ngay_cham_cong', '=', today),
                    ('nhan_vien_id', '=', current_employee.id),
                    ('state', 'in', ['xac_nhan', 'nhap'])
                ])
                record.so_nhan_vien_da_cham_cong_hom_nay = 1 if today_att_count else 0
                record.so_nhan_vien_chua_cham_cong_hom_nay = 0 if today_att_count else 1
            else:
                today_att_groups = attendance_model.read_group(
                    [
                        ('ngay_cham_cong', '=', today),
                        ('state', 'in', ['xac_nhan', 'nhap'])
                    ],
                    ['nhan_vien_id'],
                    ['nhan_vien_id']
                )
                record.so_nhan_vien_da_cham_cong_hom_nay = len(today_att_groups)
                total_emp = employee_model.search_count([])
                record.so_nhan_vien_chua_cham_cong_hom_nay = max(0, total_emp - record.so_nhan_vien_da_cham_cong_hom_nay)

            if scope_mine and current_employee:
                record.tong_nhan_vien = 1
            else:
                record.tong_nhan_vien = employee_model.search_count([])
            
            # Count distinct employees checked-in
            record.so_nhan_vien_da_cham_cong = len(attendance_model.read_group(attendance_domain, ['nhan_vien_id'], ['nhan_vien_id']))
            record.tong_cham_cong = tong_cham_cong
            record.tong_ngay_cong = round(tong_ngay_cong, 2)
            record.tong_gio_lam = round(tong_gio_lam, 2)
            record.tong_gio_tang_ca = round(tong_gio_tang_ca, 2)
            record.tong_tang_ca = attendance_model.search_count(attendance_domain + [('so_gio_tang_ca', '>', 0)])
            record.so_luot_di_muon = so_luot_di_muon
            record.so_ngay_nghi = so_ngay_nghi
            record.so_bang_luong_thang = so_bang_luong_thang
            record.tong_quy_luong = round(tong_quy_luong, 2)
            record.tong_bao_hiem = round(tong_bao_hiem, 2)
            record.tong_phu_cap = round(tong_phu_cap, 2)
            record.bang_luong_da_tinh = bang_luong_da_tinh
            record.bang_luong_xac_nhan = bang_luong_xac_nhan
            record.bang_luong_da_thanh_toan = bang_luong_da_thanh_toan
            record.bang_luong_chua_xac_nhan = bang_luong_chua_xac_nhan
            record.tong_canh_bao = tong_canh_bao
            record.so_canh_bao_cao = so_canh_bao_cao

    @api.depends('thang', 'nam')
    def _compute_charts(self):
        import json
        salary_model = self.env['bang_luong']
        warning_model = self.env['canh_bao_cham_cong']
        
        for rec in self:
            # --- 1. Dữ liệu Quỹ lương 6 tháng gần nhất ---
            labels_payroll = []
            data_payroll = []
            
            try:
                current_month = int(rec.thang)
            except (ValueError, TypeError):
                current_month = 1
            current_year = rec.nam or 2026
            
            for i in range(5, -1, -1):
                m = current_month - i
                y = current_year
                if m <= 0:
                    m += 12
                    y -= 1
                labels_payroll.append('T%s/%s' % (m, y))
                
                # Query tổng thực lĩnh của các bảng lương đã thanh toán hoặc đã xác nhận
                salaries = salary_model.sudo().search([
                    ('thang', '=', str(m)),
                    ('nam', '=', y),
                    ('state', 'in', ['xac_nhan', 'confirmed', 'da_thanh_toan']),
                ])
                data_payroll.append(sum(salaries.mapped('thuc_linh')))
                
            rec.chart_payroll_history = json.dumps({
                'type': 'bar',
                'labels': labels_payroll,
                'datasets': [{
                    'label': 'Quỹ lương thực lĩnh (VND)',
                    'data': data_payroll,
                    'backgroundColor': 'rgba(102, 16, 242, 0.65)', # HSL Purple
                    'borderColor': 'rgb(102, 16, 242)',
                    'borderWidth': 1
                }],
                'options': {
                    'responsive': True,
                    'maintainAspectRatio': False,
                    'plugins': {
                        'legend': {'display': True}
                    }
                }
            }, ensure_ascii=False)
            
            # --- 2. Dữ liệu Phân bổ Cảnh báo Chấm công ---
            warn_groups = warning_model.read_group(
                [('thang', '=', rec.thang), ('nam', '=', rec.nam)],
                ['loai_canh_bao'],
                ['loai_canh_bao']
            )
            
            alert_types = {
                'di_muon_nhieu': 'Đi muộn nhiều',
                'thieu_cong': 'Thiếu công',
                'tang_ca_qua_nhieu': 'Tăng ca quá nhiều',
                'thieu_du_lieu_cham_cong': 'Thiếu giờ vào/ra',
                'di_muon': 'Đi muộn',
                've_som': 'Về sớm',
                'thieu_gio_ra': 'Thiếu giờ ra',
            }
            
            labels_warn = []
            data_warn = []
            for group in warn_groups:
                loai = group.get('loai_canh_bao')
                lbl = alert_types.get(loai, loai or 'Khác')
                count = group.get('loai_canh_bao_count', 0)
                if lbl in labels_warn:
                    idx = labels_warn.index(lbl)
                    data_warn[idx] += count
                else:
                    labels_warn.append(lbl)
                    data_warn.append(count)
                    
            if not labels_warn or sum(data_warn) == 0:
                labels_warn = ['Không có cảnh báo']
                data_warn = [0]
                
            rec.chart_warning_distribution = json.dumps({
                'type': 'doughnut',
                'labels': labels_warn,
                'datasets': [{
                    'label': 'Số lượng cảnh báo',
                    'data': data_warn,
                    'backgroundColor': [
                        '#dc3545', '#ffc107', '#28a745', '#17a2b8', '#6610f2', '#e83e8c', '#6c757d'
                    ]
                }],
                'options': {
                    'responsive': True,
                    'maintainAspectRatio': False,
                }
            }, ensure_ascii=False)

    def _get_month_range(self):
        self.ensure_one()
        return get_month_range(self.thang, self.nam)

    def _build_action(self, xmlid, domain=None, context=None):
        self.ensure_one()
        action = self.env.ref(xmlid).sudo().read()[0]
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

    def _is_payroll_manager(self):
        return self.env['bang_luong']._is_payroll_manager()

    def _check_payroll_manager_rights(self):
        self.env['bang_luong']._check_payroll_manager_rights()

    def action_chot_cong_va_tinh_luong(self):

        self.ensure_one()
        # 1. Kiểm tra phân quyền cho 3 role bảo mật
        self._check_payroll_manager_rights()
        
        start_date, end_date = self._get_month_range()
        
        # 2. Chốt công hàng loạt trong kỳ
        cham_cong_records = self.env['cham_cong'].search([
            ('ngay_cham_cong', '>=', start_date),
            ('ngay_cham_cong', '<', end_date),
            ('state', '!=', 'xac_nhan'),
        ])
        if cham_cong_records:
            cham_cong_records.sudo().write({'state': 'xac_nhan'})
            
        # 3. Kích hoạt sinh bảng lương nháp hàng loạt
        self.env['bang_luong'].action_sinh_bang_luong_thang(self.thang, self.nam)
        
        # 4. Chuyển hướng sang danh sách bảng lương của kỳ này
        action = self.env.ref('cham_cong_tinh_luong.action_thong_ke_bang_luong').sudo().read()[0]
        action['domain'] = [('thang', '=', self.thang), ('nam', '=', self.nam)]
        return action


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
        action = self.env.ref('cham_cong_tinh_luong.action_cham_cong').sudo().read()[0]
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('cham_cong_tinh_luong.view_cham_cong_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = dict(self.env.context, form_view_initial_mode='edit')
        return action

    def action_open_import_cham_cong(self):
        self.ensure_one()
        return self.env.ref('cham_cong_tinh_luong.action_import_cham_cong_wizard').sudo().read()[0]

    def action_open_phan_tich_canh_bao(self):
        self.ensure_one()
        return self.env.ref('cham_cong_tinh_luong.action_phan_tich_canh_bao_wizard').sudo().read()[0]

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
        return self.env.ref('cham_cong_tinh_luong.action_xuat_bang_luong_wizard').sudo().read()[0]

    def action_open_sinh_bang_luong(self):
        self.ensure_one()
        return self.env.ref('cham_cong_tinh_luong.action_sinh_bang_luong_wizard').sudo().read()[0]

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
