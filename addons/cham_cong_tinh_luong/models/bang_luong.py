# -*- coding: utf-8 -*-

from datetime import date

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class BangLuong(models.Model):
    _name = 'bang_luong'
    _description = 'Bảng lương'
    _order = 'nam desc, thang desc, nhan_vien_id'

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
    phong_ban_id = fields.Many2one(
        'don_vi',
        string='Phòng ban',
        compute='_compute_thong_tin_nhan_vien',
        readonly=True,
    )
    chuc_vu_id = fields.Many2one(
        'chuc_vu',
        string='Chức vụ',
        compute='_compute_thong_tin_nhan_vien',
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
    tong_ngay_cong = fields.Float(string='Tổng ngày công', compute='_compute_bang_luong', store=True, digits=(16, 2))
    tong_gio_lam = fields.Float(string='Tổng giờ làm', compute='_compute_bang_luong', store=True, digits=(16, 2))
    tong_gio_tang_ca = fields.Float(string='Tổng giờ tăng ca', compute='_compute_bang_luong', store=True, digits=(16, 2))
    so_ngay_nghi = fields.Float(string='Số ngày nghỉ', compute='_compute_bang_luong', store=True, digits=(16, 2))
    luong_co_ban = fields.Float(string='Lương cơ bản', compute='_compute_bang_luong', store=True)
    luong_theo_cong = fields.Float(string='Lương theo công', compute='_compute_bang_luong', store=True)
    luong_theo_ngay_cong = fields.Float(string='Lương theo ngày công', related='luong_theo_cong', store=True, readonly=True)
    don_gia_gio = fields.Float(string='Đơn giá giờ', compute='_compute_bang_luong', store=True)
    he_so_tang_ca = fields.Float(string='Hệ số tăng ca', default=1.5)
    tien_tang_ca = fields.Float(string='Tiền tăng ca', compute='_compute_bang_luong', store=True)
    tong_phu_cap = fields.Float(string='Tổng phụ cấp', compute='_compute_bang_luong', store=True)
    phu_cap_an_trua = fields.Float(string='Phụ cấp ăn trưa', compute='_compute_bang_luong', store=True)
    phu_cap_xang_xe = fields.Float(string='Phụ cấp xăng xe', compute='_compute_bang_luong', store=True)
    phu_cap_trach_nhiem = fields.Float(string='Phụ cấp trách nhiệm', compute='_compute_bang_luong', store=True)
    phu_cap_khac = fields.Float(string='Phụ cấp khác', compute='_compute_bang_luong', store=True)
    tien_bao_hiem = fields.Float(string='Tiền bảo hiểm', compute='_compute_bang_luong', store=True)
    thue_tncn = fields.Float(string='Thuế TNCN', compute='_compute_bang_luong', store=True)
    khau_tru_khac = fields.Float(string='Khấu trừ khác', compute='_compute_bang_luong', store=True)
    tong_luong = fields.Float(string='Tổng lương', compute='_compute_bang_luong', store=True)
    cong_thuc_tinh_luong = fields.Text(string='Công thức tính lương', compute='_compute_bang_luong', store=True)
    canh_bao = fields.Text(string='Cảnh báo', compute='_compute_bang_luong', store=True)
    state = fields.Selection(
        [
            ('nhap', 'Nháp'),
            ('da_tinh', 'Đã tính'),
            ('xac_nhan', 'Đã xác nhận'),
            ('da_thanh_toan', 'Đã thanh toán'),
            ('huy', 'Hủy'),
            ('draft', 'Nháp'),
            ('computed', 'Đã tính'),
            ('confirmed', 'Đã xác nhận'),
            ('cancel', 'Hủy'),
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

    @api.depends('nhan_vien_id')
    def _compute_thong_tin_nhan_vien(self):
        employee_ids = self.mapped('nhan_vien_id').ids
        latest_histories = {}
        if employee_ids:
            histories = self.env['lich_su_cong_tac'].search(
                [('nhan_vien_id', 'in', employee_ids)],
                order='nhan_vien_id desc, id desc',
            )
            for history in histories:
                latest_histories.setdefault(history.nhan_vien_id.id, history)

        for record in self:
            history = latest_histories.get(record.nhan_vien_id.id)
            record.phong_ban_id = history.don_vi_id if history else False
            record.chuc_vu_id = history.chuc_vu_id if history else False

    @api.depends('thang')
    def _compute_thang_so(self):
        for record in self:
            record.thang_so = int(record.thang) if record.thang else 0

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

    def _get_active_salary_config(self):
        self.ensure_one()
        payroll_date = self.ngay_tao or fields.Date.context_today(self)
        configs = self.env['cau_hinh_luong'].search([
            ('nhan_vien_id', '=', self.nhan_vien_id.id),
            ('trang_thai', 'in', ['dang_ap_dung', 'ap_dung']),
        ], order='ngay_bat_dau desc, id desc')
        for config in configs:
            start_date = config.ngay_bat_dau or date(1900, 1, 1)
            end_date = config.ngay_ket_thuc or date(2999, 12, 31)
            if start_date <= payroll_date <= end_date:
                return config
        return self.env['cau_hinh_luong']

    def _get_payroll_values(self, require_config=False):
        self.ensure_one()
        values = {
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
            'tien_bao_hiem': 0.0,
            'thue_tncn': 0.0,
            'khau_tru_khac': 0.0,
            'tong_luong': 0.0,
            'cong_thuc_tinh_luong': '',
            'canh_bao': '',
            'cham_cong_ids': [(5, 0, 0)],
        }

        if not self.nhan_vien_id or not self.thang or not self.nam:
            return values

        config = self._get_active_salary_config()
        if not config:
            if require_config:
                raise ValidationError('Chưa có cấu hình lương đang áp dụng cho nhân viên này.')
            values['canh_bao'] = 'Chưa có cấu hình lương đang áp dụng cho nhân viên này.'
            return values

        start_date, end_date = self._get_month_range()
        cham_cong_records = self.env['cham_cong'].search([
            ('nhan_vien_id', '=', self.nhan_vien_id.id),
            ('ngay_cham_cong', '>=', start_date),
            ('ngay_cham_cong', '<', end_date),
            ('state', 'in', ['xac_nhan', 'confirmed']),
        ], order='ngay_cham_cong, gio_vao, id')

        values['cham_cong_ids'] = [(6, 0, cham_cong_records.ids)]
        if not cham_cong_records:
            values['canh_bao'] = 'Không có chấm công trong kỳ lương, tổng ngày công = 0.'

        values['tong_ngay_cong'] = float(len(cham_cong_records.filtered(lambda item: item.trang_thai != 'nghi')))
        values['tong_gio_lam'] = round(sum(cham_cong_records.mapped('so_gio_lam')), 2)
        values['tong_gio_tang_ca'] = round(sum(cham_cong_records.mapped('so_gio_tang_ca')), 2)
        values['so_ngay_nghi'] = float(len(cham_cong_records.filtered(lambda item: item.trang_thai == 'nghi')))

        values['luong_co_ban'] = config.luong_co_ban
        values['tong_phu_cap'] = config.tong_phu_cap
        values['phu_cap_an_trua'] = config.phu_cap_an_trua
        values['phu_cap_xang_xe'] = config.phu_cap_xang_xe
        values['phu_cap_trach_nhiem'] = config.phu_cap_trach_nhiem
        values['phu_cap_khac'] = config.phu_cap_khac
        values['thue_tncn'] = config.thue_tncn
        values['khau_tru_khac'] = config.khau_tru_khac
        values['don_gia_gio'] = round(config.luong_co_ban / config.so_ngay_cong_chuan / config.so_gio_cong_chuan, 2)
        values['luong_theo_cong'] = round(
            config.luong_co_ban / config.so_ngay_cong_chuan * values['tong_ngay_cong'],
            2,
        )
        values['tien_tang_ca'] = round(values['don_gia_gio'] * self.he_so_tang_ca * values['tong_gio_tang_ca'], 2)
        values['tien_bao_hiem'] = round(config.luong_co_ban * config.ty_le_bao_hiem / 100.0, 2)
        values['tong_luong'] = round(
            values['luong_theo_cong']
            + values['tien_tang_ca']
            + values['tong_phu_cap']
            - values['tien_bao_hiem']
            - values['thue_tncn']
            - values['khau_tru_khac'],
            2,
        )
        values['cong_thuc_tinh_luong'] = (
            'Lương theo công = Lương cơ bản / Số ngày công chuẩn * Tổng ngày công\n'
            'Đơn giá giờ = Lương cơ bản / Số ngày công chuẩn / Số giờ công chuẩn\n'
            'Tiền tăng ca = Đơn giá giờ * Hệ số tăng ca * Tổng giờ tăng ca\n'
            'Tiền bảo hiểm = Lương cơ bản * Tỷ lệ bảo hiểm / 100\n'
            'Tổng lương = Lương theo công + Tiền tăng ca + Tổng phụ cấp - Tiền bảo hiểm - Thuế TNCN - Khấu trừ khác'
        )
        return values

    @api.depends('nhan_vien_id', 'thang', 'nam', 'ngay_tao', 'he_so_tang_ca')
    def _compute_cham_cong_ids(self):
        for record in self:
            values = record._get_payroll_values() if record.nhan_vien_id and record.thang and record.nam else {'cham_cong_ids': [(5, 0, 0)]}
            record.cham_cong_ids = values['cham_cong_ids']

    @api.depends('nhan_vien_id', 'thang', 'nam', 'ngay_tao', 'he_so_tang_ca')
    def _compute_bang_luong(self):
        for record in self:
            values = record._get_payroll_values()
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
            record.tien_bao_hiem = values['tien_bao_hiem']
            record.thue_tncn = values['thue_tncn']
            record.khau_tru_khac = values['khau_tru_khac']
            record.tong_luong = values['tong_luong']
            record.cong_thuc_tinh_luong = values['cong_thuc_tinh_luong']
            record.canh_bao = values['canh_bao']

    # ── Helpers kiểm tra quyền ──────────────────────────────────────

    def _is_payroll_manager(self):
        return (
            self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_quan_tri')
            or self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_ke_toan')
        )

    def _check_payroll_manager_rights(self):
        if not self._is_payroll_manager():
            raise AccessError(
                'Bạn không có quyền thực hiện thao tác quản lý bảng lương. '
                'Chỉ Kế toán hoặc Quản trị mới được phép.'
            )

    # ── Actions chuyển trạng thái ────────────────────────────────

    def action_tinh_luong(self):
        self._check_payroll_manager_rights()
        for record in self:
            values = record._get_payroll_values(require_config=True)
            values.pop('cham_cong_ids', None)
            record.write({**values, 'state': 'da_tinh'})

    def action_tinh_lai_luong(self):
        """Cập nhật/tính lại lương — hoạt động ở mọi trạng thái (trừ hủy và đã thanh toán)."""
        self._check_payroll_manager_rights()
        for record in self:
            if record.state in ('huy', 'da_thanh_toan'):
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

    def action_da_thanh_toan(self):
        self._check_payroll_manager_rights()
        self.write({'state': 'da_thanh_toan'})

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
            raise AccessError('Bạn chỉ được in phiếu lương của chính mình.')
        return self.env.ref('cham_cong_tinh_luong.action_report_bang_luong').report_action(self)

    def write(self, vals):
        # Admin/Kế toán được sửa tự do không bị chặn bởi state
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
            'tong_ngay_cong',
            'tong_gio_lam',
            'tong_gio_tang_ca',
            'so_ngay_nghi',
            'luong_co_ban',
            'luong_theo_cong',
            'don_gia_gio',
            'tien_tang_ca',
            'tong_phu_cap',
            'tien_bao_hiem',
            'thue_tncn',
            'khau_tru_khac',
            'tong_luong',
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
