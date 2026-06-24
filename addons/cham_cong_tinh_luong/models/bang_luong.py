import logging
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .nhan_vien_thong_tin_mixin import get_month_range

_logger = logging.getLogger(__name__)
DEFAULT_OVERTIME_MULTIPLIER = 1.5


class BangLuong(models.Model):
    _name = 'bang_luong'
    _inherit = ['nhan_vien_thong_tin.mixin']
    _description = 'Bảng lương'
    _order = 'nam desc, thang_so desc, nhan_vien_id'
    _sql_constraints = [
        (
            'uniq_bang_luong_nhan_vien_thang_nam',
            'unique(nhan_vien_id, thang, nam)',
            'Không được tạo trùng bảng lương cho cùng nhân viên, cùng tháng, cùng năm.',
        ),
    ]

    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên',
        required=True,
        ondelete='cascade',
    )
    ma_nhan_vien = fields.Char(
        string='Mã nhân viên',
        related='nhan_vien_id.ma_dinh_danh',
        store=True,
        readonly=True,
    )
    ngay_tao = fields.Date(
        string='Ngày tạo',
        default=lambda self: fields.Date.context_today(self),
        required=True,
    )
    ngay_tao_bang_luong = fields.Date(
        string='Ngày tạo bảng lương',
        related='ngay_tao',
        store=True,
        readonly=False,
    )
    thang = fields.Selection(
        [(str(i), 'Tháng %s' % i) for i in range(1, 13)],
        string='Tháng',
        required=True,
        default=lambda self: str(fields.Date.context_today(self).month),
    )
    thang_so = fields.Integer(string='Tháng số', compute='_compute_thang_so', store=True)
    nam = fields.Integer(
        string='Năm',
        required=True,
        default=lambda self: fields.Date.context_today(self).year,
    )
    so_ngay_di_lam = fields.Float(string='Số ngày đi làm', compute='_compute_bang_luong', store=True, digits=(16, 2))
    tong_ngay_cong = fields.Float(string='Tổng ngày công', compute='_compute_bang_luong', store=True, digits=(16, 2))
    tong_gio_lam = fields.Float(string='Tổng giờ làm', compute='_compute_bang_luong', store=True, digits=(16, 2))
    tong_gio_tang_ca = fields.Float(string='Tổng giờ tăng ca', compute='_compute_bang_luong', store=True, digits=(16, 2))
    so_ngay_nghi = fields.Float(string='Số ngày nghỉ', compute='_compute_bang_luong', store=True, digits=(16, 2))
    luong_co_ban = fields.Float(string='Lương cơ bản', compute='_compute_bang_luong', store=True)
    luong_theo_cong = fields.Float(string='Lương theo ngày công', compute='_compute_bang_luong', store=True)
    luong_theo_ngay_cong = fields.Float(string='Lương theo ngày công', related='luong_theo_cong', store=True, readonly=True)
    don_gia_gio = fields.Float(string='Đơn giá giờ', compute='_compute_bang_luong', store=True)
    he_so_tang_ca = fields.Float(string='Hệ số tăng ca', default=DEFAULT_OVERTIME_MULTIPLIER)
    tien_tang_ca = fields.Float(string='Tiền tăng ca', compute='_compute_bang_luong', store=True)
    tong_phu_cap = fields.Float(string='Tổng phụ cấp', compute='_compute_bang_luong', store=True)
    phu_cap_an_trua = fields.Float(string='Phụ cấp ăn trưa', compute='_compute_bang_luong', store=True)
    phu_cap_xang_xe = fields.Float(string='Phụ cấp xăng xe', compute='_compute_bang_luong', store=True)
    phu_cap_trach_nhiem = fields.Float(string='Phụ cấp trách nhiệm', compute='_compute_bang_luong', store=True)
    phu_cap_khac = fields.Float(string='Phụ cấp khác', compute='_compute_bang_luong', store=True)
    tong_khen_thuong = fields.Float(string='Tổng khen thưởng', compute='_compute_bang_luong', store=True)
    tong_ky_luat = fields.Float(string='Tổng kỷ luật', compute='_compute_bang_luong', store=True)
    tien_bao_hiem = fields.Float(string='Tiền bảo hiểm', compute='_compute_bang_luong', store=True)
    thue_tncn = fields.Float(string='Thuế TNCN', compute='_compute_bang_luong', store=True)
    khau_tru_khac = fields.Float(string='Khấu trừ khác', compute='_compute_bang_luong', store=True)
    tong_khau_tru = fields.Float(string='Tổng khấu trừ', compute='_compute_bang_luong', store=True)
    tong_luong = fields.Float(string='Tổng lương', compute='_compute_bang_luong', store=True)
    thuc_linh = fields.Float(string='Thực lĩnh', compute='_compute_bang_luong', store=True, readonly=True)
    cong_thuc_tinh_luong = fields.Text(string='Công thức tính lương', compute='_compute_bang_luong', store=True)
    canh_bao = fields.Text(string='Cảnh báo', compute='_compute_bang_luong', store=True)
    state = fields.Selection(
        [
            ('nhap', 'Nháp'),
            ('da_tinh', 'Đã tính'),
            ('xac_nhan', 'Đã xác nhận'),
            ('da_thanh_toan', 'Đã thanh toán'),
            ('huy', 'Hủy'),
        ],
        string='Trạng thái',
        required=True,
        default='nhap',
    )
    ghi_chu = fields.Text(string='Ghi chú')
    cham_cong_ids = fields.Many2many(
        'cham_cong',
        string='Chi tiết chấm công',
        compute='_compute_cham_cong_ids',
        readonly=True,
    )

    def _get_month_range(self):
        self.ensure_one()
        return get_month_range(self.thang, self.nam)

    @api.depends('thang')
    def _compute_thang_so(self):
        for record in self:
            record.thang_so = int(record.thang) if record.thang else 0

    def _get_active_salary_config(self):
        self.ensure_one()
        payroll_date = self.ngay_tao or self._get_month_range()[0]
        configs = self.env['cau_hinh_luong'].search([
            ('nhan_vien_id', '=', self.nhan_vien_id.id),
            ('trang_thai', '=', 'dang_ap_dung'),
        ], order='ngay_bat_dau desc, id desc')
        for config in configs:
            start_date = config.ngay_bat_dau or date(1900, 1, 1)
            end_date = config.ngay_ket_thuc or date(2999, 12, 31)
            if start_date <= payroll_date <= end_date:
                return config
        return self.env['cau_hinh_luong']

    def _attendance_day_credit(self, attendance):
        status = attendance.trang_thai
        if status == 'nua_ngay':
            return 0.5
        if status in ('nghi', 'nghi_co_phep', 'nghi_khong_phep'):
            return 0.0
        return 1.0

    def _get_reward_discipline_totals(self, start_date, end_date):
        self.ensure_one()
        Result = self.env['khen_thuong_ky_luat'].sudo()
        reward_domain = [
            ('nhan_vien_id', '=', self.nhan_vien_id.id),
            ('ngay_ap_dung', '>=', start_date),
            ('ngay_ap_dung', '<', end_date),
            ('loai_quyet_dinh', '=', 'khen_thuong'),
        ]
        discipline_domain = [
            ('nhan_vien_id', '=', self.nhan_vien_id.id),
            ('ngay_ap_dung', '>=', start_date),
            ('ngay_ap_dung', '<', end_date),
            ('loai_quyet_dinh', '=', 'ky_luat'),
        ]
        tong_khen_thuong = sum(Result.search(reward_domain).mapped('so_tien'))
        tong_ky_luat = sum(Result.search(discipline_domain).mapped('so_tien'))
        return round(tong_khen_thuong, 2), round(tong_ky_luat, 2)

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

        config = self.env['cau_hinh_luong']
        if prefetched_data and 'configs' in prefetched_data:
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
                ('state', '=', 'xac_nhan'),
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
        standard_days = config.so_ngay_cong_chuan or 26.0
        values['luong_theo_cong'] = round(config.luong_co_ban / standard_days * values['so_ngay_di_lam'], 2)
        values['tien_tang_ca'] = round(values['don_gia_gio'] * self.he_so_tang_ca * values['tong_gio_tang_ca'], 2)
        values['tien_bao_hiem'] = round(config.luong_co_ban * config.ty_le_bao_hiem / 100.0, 2)
        values['thue_tncn'] = round(config.thue_tncn, 2)
        values['khau_tru_khac'] = round(config.khau_tru_khac, 2)
        values['tong_khau_tru'] = round(
            values['tien_bao_hiem'] + values['thue_tncn'] + values['khau_tru_khac'],
            2,
        )

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
            + values['tien_tang_ca']
            + values['tong_khen_thuong'],
            2,
        )
        values['thuc_linh'] = round(
            values['tong_luong']
            - values['tong_khau_tru']
            - values['tong_ky_luat'],
            2,
        )
        values['cong_thuc_tinh_luong'] = (
            'Lương theo ngày công = Lương cơ bản / Số ngày công chuẩn * Số ngày đi làm thực tế\n'
            'Tổng lương = Lương theo ngày công + Tổng phụ cấp + Tiền tăng ca + Khen thưởng\n'
            'Thực lĩnh = Tổng lương - Tổng khấu trừ - Kỷ luật'
        )
        return values

    @api.depends('nhan_vien_id', 'thang', 'nam')
    def _compute_cham_cong_ids(self):
        for record in self:
            if not (record.nhan_vien_id and record.thang and record.nam):
                record.cham_cong_ids = False
                continue
            start_date, end_date = record._get_month_range()
            record.cham_cong_ids = self.env['cham_cong'].search([
                ('nhan_vien_id', '=', record.nhan_vien_id.id),
                ('ngay_cham_cong', '>=', start_date),
                ('ngay_cham_cong', '<', end_date),
            ])

    @api.depends('nhan_vien_id', 'thang', 'nam', 'ngay_tao', 'he_so_tang_ca')
    def _compute_bang_luong(self):
        employee_ids = self.mapped('nhan_vien_id').ids
        prefetched = {}

        if len(self) > 1 and employee_ids:
            configs = self.env['cau_hinh_luong'].search([
                ('nhan_vien_id', 'in', employee_ids),
                ('trang_thai', 'in', ['dang_ap_dung', 'ap_dung']),
            ], order='ngay_bat_dau desc, id desc')

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
                    ('state', '=', 'xac_nhan'),
                ], order='ngay_cham_cong, gio_vao, id')

                rewards_disciplines = self.env['khen_thuong_ky_luat'].search([
                    ('nhan_vien_id', 'in', employee_ids),
                    ('ngay_ap_dung', '>=', min_start),
                    ('ngay_ap_dung', '<', max_end),
                ])

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
            record.thuc_linh = values['thuc_linh']
            record.cong_thuc_tinh_luong = values['cong_thuc_tinh_luong']
            record.canh_bao = values['canh_bao']

    def _is_payroll_manager(self):
        return (
            self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_quan_tri')
            or self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_ke_toan')
            or self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_nhan_su')
        )

    def _check_payroll_manager_rights(self):
        if not self._is_payroll_manager():
            raise AccessError(
                'Bạn không có quyền thực hiện thao tác quản lý bảng lương. '
                'Chỉ Nhân sự, Kế toán hoặc Quản trị mới được phép.'
            )

    @api.model
    def action_sinh_bang_luong_thang(self, thang, nam, nhan_vien_ids=None):
        self._check_payroll_manager_rights()
        employees = self.env['nhan_vien'].search([])
        if nhan_vien_ids:
            employees = employees.filtered(lambda emp: emp.id in nhan_vien_ids)

        existing_payrolls = self.search([
            ('nhan_vien_id', 'in', employees.ids),
            ('thang', '=', str(thang)),
            ('nam', '=', int(nam)),
        ])
        payroll_map = {p.nhan_vien_id.id: p for p in existing_payrolls}

        # Bulk pre-fetching configs, attendance, and rewards/disciplines to prevent N+1 queries
        configs = self.env['cau_hinh_luong'].search([
            ('nhan_vien_id', 'in', employees.ids),
            ('trang_thai', '=', 'dang_ap_dung'),
        ], order='ngay_bat_dau desc, id desc')

        start_date = date(int(nam), int(thang), 1)
        if int(thang) == 12:
            end_date = date(int(nam) + 1, 1, 1)
        else:
            end_date = date(int(nam), int(thang) + 1, 1)

        cham_cong = self.env['cham_cong'].search([
            ('nhan_vien_id', 'in', employees.ids),
            ('ngay_cham_cong', '>=', start_date),
            ('ngay_cham_cong', '<', end_date),
            ('state', '=', 'xac_nhan'),
        ], order='ngay_cham_cong, gio_vao, id')

        rewards_disciplines = self.env['khen_thuong_ky_luat'].search([
            ('nhan_vien_id', 'in', employees.ids),
            ('ngay_ap_dung', '>=', start_date),
            ('ngay_ap_dung', '<', end_date),
        ])

        prefetched = {
            'configs': configs,
            'cham_cong': cham_cong,
            'rewards_disciplines': rewards_disciplines,
        }

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
            values = payroll._get_payroll_values(require_config=False, prefetched_data=prefetched)
            if values['canh_bao'] and not values['luong_co_ban']:
                skipped += 1
                messages.append('%s: %s' % (employee.ho_va_ten, values['canh_bao']))
                continue
            values.pop('cham_cong_ids', None)
            values['state'] = draft.state if draft else 'da_tinh'
            if draft:
                super(BangLuong, draft).write(values)
                updated += 1
            else:
                record = super(BangLuong, self).create({
                    'nhan_vien_id': employee.id,
                    'thang': str(thang),
                    'nam': int(nam),
                    'ngay_tao': fields.Date.context_today(self),
                    'state': 'nhap',
                })
                super(BangLuong, record).write({**values, 'state': 'da_tinh'})
                created += 1

        _logger.info('Sinh bảng lương hoàn tất: tạo %s, cập nhật %s, bỏ qua %s bảng lương.', created, updated, skipped)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sinh bảng lương hoàn tất',
                'message': 'Đã tạo %s, cập nhật %s, bỏ qua %s bảng lương.' % (created, updated, skipped),
                'sticky': False,
            },
            'details': messages,
        }

    def action_tinh_luong(self):
        self._check_payroll_manager_rights()
        for record in self:
            values = record._get_payroll_values(require_config=True)
            values.pop('cham_cong_ids', None)
            record.write({**values, 'state': 'da_tinh'})

    def action_tinh_lai_luong(self):
        self._check_payroll_manager_rights()
        for record in self:
            if record.state in ('huy', 'cancel', 'da_thanh_toan'):
                raise ValidationError(
                    'Không thể tính lại bảng lương đã hủy hoặc đã thanh toán. '
                    'Vui lòng đặt về Nháp trước.'
                )
            values = record._get_payroll_values(require_config=True)
            values.pop('cham_cong_ids', None)
            super(BangLuong, record).write({**values, 'state': 'da_tinh'})

    def action_xac_nhan(self):
        self._check_payroll_manager_rights()
        self.write({'state': 'xac_nhan'})

    def action_gui_email_phieu_luong(self):
        self.ensure_one()
        if not self.nhan_vien_id.email:
            raise ValidationError('Nhân viên %s chưa cấu hình địa chỉ Email.' % self.nhan_vien_id.ho_va_ten)
        
        template = self.env.ref('cham_cong_tinh_luong.mail_template_phieu_luong', raise_if_not_found=False)
        if not template:
            raise ValidationError('Không tìm thấy mẫu email Phiếu lương.')
            
        template.send_mail(self.id, force_send=True)
        self.message_post(body='Đã gửi phiếu lương tháng %s/%s qua email cho nhân viên.' % (self.thang, self.nam))
        return True

    def action_da_thanh_toan(self):
        self._check_payroll_manager_rights()
        self.write({'state': 'da_thanh_toan'})
        for record in self:
            if record.nhan_vien_id.email:
                try:
                    record.action_gui_email_phieu_luong()
                except Exception as e:
                    _logger.error('Lỗi khi gửi email tự động cho nhân viên %s: %s', record.nhan_vien_id.ho_va_ten, str(e))

    def action_huy(self):
        self._check_payroll_manager_rights()
        self.write({'state': 'huy'})

    def action_draft(self):
        self._check_payroll_manager_rights()
        self.write({'state': 'nhap'})

    def action_in_phieu_luong(self):
        self.ensure_one()
        is_manager = self._is_payroll_manager()
        is_owner = (
            self.nhan_vien_id.user_id
            and self.nhan_vien_id.user_id.id == self.env.user.id
        )
        if not is_manager and not is_owner:
            raise AccessError('Bạn chỉ được xem phiếu lương của chính mình.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Xem trước phiếu lương',
            'res_model': 'phieu_luong_preview_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bang_luong_id': self.id,
            },
        }

    def write(self, vals):
        if self._is_payroll_manager():
            return super().write(vals)
        protected_fields = {
            'nhan_vien_id',
            'thang',
            'nam',
            'ngay_tao',
            'ngay_tao_bang_luong',
            'he_so_tang_ca',
            'ghi_chu',
            'so_ngay_di_lam',
            'tong_ngay_cong',
            'tong_gio_lam',
            'tong_gio_tang_ca',
            'so_ngay_nghi',
            'luong_co_ban',
            'luong_theo_cong',
            'luong_theo_ngay_cong',
            'don_gia_gio',
            'tien_tang_ca',
            'tong_phu_cap',
            'phu_cap_an_trua',
            'phu_cap_xang_xe',
            'phu_cap_trach_nhiem',
            'phu_cap_khac',
            'tong_khen_thuong',
            'tong_ky_luat',
            'tien_bao_hiem',
            'thue_tncn',
            'khau_tru_khac',
            'tong_khau_tru',
            'tong_luong',
            'thuc_linh',
            'cong_thuc_tinh_luong',
            'canh_bao',
        }
        if protected_fields.intersection(vals.keys()):
            for record in self:
                if record.state != 'nhap':
                    raise ValidationError('Chỉ được chỉnh sửa bảng lương ở trạng thái Nháp.')
        return super().write(vals)

    @api.constrains('nhan_vien_id', 'thang', 'nam')
    def _check_duplicate_salary_sheet(self):
        for record in self:
            if not record.nhan_vien_id or not record.thang or not record.nam:
                continue
            if self.search_count([
                ('id', '!=', record.id),
                ('nhan_vien_id', '=', record.nhan_vien_id.id),
                ('thang', '=', record.thang),
                ('nam', '=', record.nam),
            ]):
                raise ValidationError('Không được tạo trùng bảng lương cho cùng nhân viên, cùng tháng, cùng năm.')

    @api.constrains('nam')
    def _check_nam(self):
        for record in self:
            if record.nam < 1900 or record.nam > 2100:
                raise ValidationError('Năm phải nằm trong khoảng từ 1900 đến 2100.')
