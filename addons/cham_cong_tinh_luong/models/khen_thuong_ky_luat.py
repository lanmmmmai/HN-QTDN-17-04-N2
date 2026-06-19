# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class KhenThuongKyLuat(models.Model):
    _name = 'khen_thuong_ky_luat'
    _description = 'Khen thưởng / kỷ luật'
    _order = 'ngay_ap_dung desc, id desc'

    name = fields.Char(string='Diễn giải', compute='_compute_name', store=True)
    nhan_vien_id = fields.Many2one('nhan_vien', string='Nhân viên', required=True, ondelete='cascade')
    ma_nhan_vien = fields.Char(related='nhan_vien_id.ma_dinh_danh', string='Mã nhân viên', store=True, readonly=True)
    loai_quyet_dinh = fields.Selection(
        [
            ('khen_thuong', 'Khen thưởng'),
            ('ky_luat', 'Kỷ luật'),
        ],
        string='Loại quyết định',
        required=True,
    )
    so_tien = fields.Float(string='Số tiền', required=True, default=0.0)
    ngay_ap_dung = fields.Date(string='Ngày áp dụng', required=True, default=lambda self: fields.Date.context_today(self))
    thang = fields.Selection([(str(i), 'Tháng %s' % i) for i in range(1, 13)], string='Tháng', compute='_compute_thang_nam', store=True)
    nam = fields.Integer(string='Năm', compute='_compute_thang_nam', store=True)
    ghi_chu = fields.Text(string='Ghi chú')

    @api.depends('nhan_vien_id', 'loai_quyet_dinh', 'so_tien', 'ngay_ap_dung')
    def _compute_name(self):
        for record in self:
            loai = dict(self._fields['loai_quyet_dinh'].selection).get(record.loai_quyet_dinh, '')
            ngay = record.ngay_ap_dung.strftime('%d/%m/%Y') if record.ngay_ap_dung else ''
            record.name = '%s - %s - %s' % (record.nhan_vien_id.ho_va_ten or '', loai, ngay)

    @api.depends('ngay_ap_dung')
    def _compute_thang_nam(self):
        for record in self:
            if record.ngay_ap_dung:
                record.thang = str(record.ngay_ap_dung.month)
                record.nam = record.ngay_ap_dung.year
            else:
                record.thang = False
                record.nam = 0

    @api.constrains('so_tien')
    def _check_so_tien(self):
        for record in self:
            if record.so_tien < 0:
                raise ValidationError('Số tiền khen thưởng/kỷ luật không được âm.')
