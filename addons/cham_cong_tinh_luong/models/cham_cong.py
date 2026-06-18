# -*- coding: utf-8 -*-

from datetime import datetime

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ChamCong(models.Model):
    _name = 'cham_cong'
    _description = 'Chấm công'
    _order = 'ngay_cham_cong desc, gio_vao desc, id desc'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'nhan_vien_id' in fields_list and not res.get('nhan_vien_id'):
            employee = self.env['nhan_vien'].search(
                [('user_id', '=', self.env.user.id)], limit=1
            )
            if employee:
                res['nhan_vien_id'] = employee.id
        return res

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
    ngay_cham_cong = fields.Date(
        string='Ngày chấm công',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    ca_lam_viec = fields.Selection(
        [
            ('hanh_chinh', 'Hành chính'),
            ('sang', 'Ca sáng'),
            ('chieu', 'Ca chiều'),
            ('toi', 'Ca tối'),
        ],
        string='Ca làm việc',
        required=True,
        default='hanh_chinh',
    )
    gio_vao = fields.Datetime(string='Giờ vào')
    gio_ra = fields.Datetime(string='Giờ ra')
    so_gio_lam = fields.Float(
        string='Số giờ làm',
        compute='_compute_so_gio_lam',
        store=True,
        digits=(16, 2),
    )
    so_gio_tang_ca = fields.Float(
        string='Số giờ tăng ca',
        compute='_compute_so_gio_tang_ca',
        store=True,
        digits=(16, 2),
    )
    loai_cong = fields.Selection(
        [
            ('cong_thuong', 'Công thường'),
            ('cong_phep', 'Công phép'),
            ('cong_khong_luong', 'Công không lương'),
            ('cong_tang_ca', 'Công tăng ca'),
        ],
        string='Loại công',
        required=True,
        default='cong_thuong',
    )
    ly_do_di_muon = fields.Text(string='Lý do đi muộn')
    trang_thai = fields.Selection(
        [
            ('di_lam', 'Đi làm'),
            ('nua_ngay', 'Nửa ngày'),
            ('nghi_co_phep', 'Nghỉ có phép'),
            ('nghi_khong_phep', 'Nghỉ không phép'),
            ('di_muon', 'Đi muộn'),
            ('nghi', 'Nghỉ'),
            ('tang_ca', 'Tăng ca'),
        ],
        string='Trạng thái công',
        required=True,
        default='di_lam',
    )
    so_ngay_cong = fields.Float(
        string='Số ngày công quy đổi',
        compute='_compute_so_ngay_cong',
        store=True,
        digits=(16, 2),
    )
    state = fields.Selection(
        [
            ('nhap', 'Nháp'),
            ('xac_nhan', 'Đã xác nhận'),
            ('huy', 'Hủy'),
            ('draft', 'Nháp'),
            ('confirmed', 'Đã xác nhận'),
            ('cancel', 'Hủy'),
        ],
        string='Trạng thái',
        required=True,
        default='nhap',
    )
    ghi_chu = fields.Text(string='Ghi chú')

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

    @api.depends('gio_vao', 'gio_ra', 'trang_thai')
    def _compute_so_gio_lam(self):
        for record in self:
            if record.trang_thai in ('nghi', 'nghi_co_phep', 'nghi_khong_phep'):
                record.so_gio_lam = 0.0
            elif record.gio_vao and record.gio_ra and record.gio_ra >= record.gio_vao:
                delta = record.gio_ra - record.gio_vao
                record.so_gio_lam = round(delta.total_seconds() / 3600.0, 2)
            else:
                record.so_gio_lam = 0.0

    @api.depends('so_gio_lam')
    def _compute_so_gio_tang_ca(self):
        for record in self:
            if record.so_gio_lam > 8.0:
                record.so_gio_tang_ca = round(record.so_gio_lam - 8.0, 2)
            else:
                record.so_gio_tang_ca = 0.0

    @api.depends('trang_thai')
    def _compute_so_ngay_cong(self):
        for record in self:
            if record.trang_thai == 'nua_ngay':
                record.so_ngay_cong = 0.5
            elif record.trang_thai in ('nghi', 'nghi_co_phep', 'nghi_khong_phep'):
                record.so_ngay_cong = 0.0
            else:
                record.so_ngay_cong = 1.0

    def action_xac_nhan(self):
        self.write({'state': 'xac_nhan'})

    def action_draft(self):
        self.write({'state': 'nhap'})

    def action_huy(self):
        self.write({'state': 'huy'})

    @api.constrains('nhan_vien_id', 'ngay_cham_cong', 'ca_lam_viec')
    def _check_unique_cham_cong(self):
        for record in self:
            if not record.nhan_vien_id or not record.ngay_cham_cong or not record.ca_lam_viec:
                continue
            domain = [
                ('id', '!=', record.id),
                ('nhan_vien_id', '=', record.nhan_vien_id.id),
                ('ngay_cham_cong', '=', record.ngay_cham_cong),
                ('ca_lam_viec', '=', record.ca_lam_viec),
            ]
            if self.search(domain, limit=1):
                raise ValidationError('Một nhân viên không được có 2 bản ghi chấm công cùng ngày và cùng ca làm việc.')

    @api.constrains('trang_thai', 'ly_do_di_muon')
    def _check_ly_do_di_muon(self):
        for record in self:
            if record.trang_thai == 'di_muon' and not record.ly_do_di_muon:
                raise ValidationError('Nếu đi muộn thì phải nhập lý do đi muộn.')

    @api.model
    def _local_datetime_to_utc_naive(self, day_value, hour_value):
        """Convert a local date + time string into a UTC-naive datetime for storage."""
        if not day_value or not hour_value:
            return False
        if isinstance(day_value, str):
            day_value = fields.Date.from_string(day_value)
        try:
            hh, mm = (hour_value.strip().split(':') + ['0'])[:2]
            local_dt = datetime(day_value.year, day_value.month, day_value.day, int(hh), int(mm))
        except (ValueError, TypeError):
            return False
        tz_name = self.env.user.tz or self.env.context.get('tz') or 'Asia/Ho_Chi_Minh'
        try:
            tz = pytz.timezone(tz_name)
        except Exception:  # noqa: BLE001
            tz = pytz.timezone('Asia/Ho_Chi_Minh')
        localized = tz.localize(local_dt, is_dst=None)
        return localized.astimezone(pytz.UTC).replace(tzinfo=None)

    @api.constrains('gio_vao', 'gio_ra')
    def _check_gio_ra_sau_gio_vao(self):
        for record in self:
            if record.gio_vao and record.gio_ra and record.gio_ra < record.gio_vao:
                raise ValidationError('Giờ ra phải lớn hơn hoặc bằng giờ vào.')
