# -*- coding: utf-8 -*-

from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


DEFAULT_INSURANCE_RATE = 10.5


class CauHinhLuong(models.Model):
    _name = 'cau_hinh_luong'
    _inherit = ['nhan_vien_thong_tin.mixin']
    _description = 'Cấu hình lương'
    _order = 'trang_thai desc, ngay_bat_dau desc, nhan_vien_id, id desc'

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
    luong_co_ban = fields.Float(string='Lương cơ bản', required=True, default=0.0)
    so_ngay_cong_chuan = fields.Float(string='Số ngày công chuẩn', default=26.0, required=True)
    so_gio_cong_chuan = fields.Float(string='Số giờ công chuẩn/ngày', default=8.0, required=True)
    phu_cap_an_trua = fields.Float(string='Phụ cấp ăn trưa', default=0.0)
    phu_cap_xang_xe = fields.Float(string='Phụ cấp xăng xe', default=0.0)
    phu_cap_trach_nhiem = fields.Float(string='Phụ cấp trách nhiệm', default=0.0)
    phu_cap_khac = fields.Float(string='Phụ cấp khác', default=0.0)
    tong_phu_cap = fields.Float(
        string='Tổng phụ cấp',
        compute='_compute_tong_phu_cap',
        store=True,
    )
    ty_le_bao_hiem = fields.Float(string='Tỷ lệ bảo hiểm (%)', default=DEFAULT_INSURANCE_RATE)
    thue_tncn = fields.Float(string='Thuế TNCN', default=0.0)
    khau_tru_khac = fields.Float(string='Khấu trừ khác', default=0.0)
    ngay_bat_dau = fields.Date(
        string='Ngày bắt đầu áp dụng',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    ngay_ket_thuc = fields.Date(string='Ngày kết thúc')
    trang_thai = fields.Selection(
        [
            ('dang_ap_dung', 'Đang áp dụng'),
            ('ngung_ap_dung', 'Ngừng áp dụng'),
        ],
        string='Trạng thái',
        required=True,
        default='dang_ap_dung',
    )

    @api.depends(
        'phu_cap_an_trua',
        'phu_cap_xang_xe',
        'phu_cap_trach_nhiem',
        'phu_cap_khac',
    )
    def _compute_tong_phu_cap(self):
        for record in self:
            record.tong_phu_cap = (
                record.phu_cap_an_trua
                + record.phu_cap_xang_xe
                + record.phu_cap_trach_nhiem
                + record.phu_cap_khac
            )

    def action_ap_dung(self):
        self.write({'trang_thai': 'dang_ap_dung'})

    def action_ngung_ap_dung(self):
        self.write({'trang_thai': 'ngung_ap_dung'})

    @api.constrains(
        'luong_co_ban',
        'so_ngay_cong_chuan',
        'so_gio_cong_chuan',
        'phu_cap_an_trua',
        'phu_cap_xang_xe',
        'phu_cap_trach_nhiem',
        'phu_cap_khac',
        'ty_le_bao_hiem',
        'thue_tncn',
        'khau_tru_khac',
    )
    def _check_so_tien_va_ty_le(self):
        for record in self:
            if record.luong_co_ban < 0:
                raise ValidationError('Lương cơ bản không được âm.')
            if record.so_ngay_cong_chuan <= 0:
                raise ValidationError('Số ngày công chuẩn phải lớn hơn 0.')
            if record.so_gio_cong_chuan <= 0:
                raise ValidationError('Số giờ công chuẩn/ngày phải lớn hơn 0.')
            if record.phu_cap_an_trua < 0:
                raise ValidationError('Phụ cấp ăn trưa không được âm.')
            if record.phu_cap_xang_xe < 0:
                raise ValidationError('Phụ cấp xăng xe không được âm.')
            if record.phu_cap_trach_nhiem < 0:
                raise ValidationError('Phụ cấp trách nhiệm không được âm.')
            if record.phu_cap_khac < 0:
                raise ValidationError('Phụ cấp khác không được âm.')
            if record.ty_le_bao_hiem < 0 or record.ty_le_bao_hiem > 100:
                raise ValidationError('Tỷ lệ bảo hiểm phải từ 0 đến 100.')
            if record.thue_tncn < 0:
                raise ValidationError('Thuế TNCN không được âm.')
            if record.khau_tru_khac < 0:
                raise ValidationError('Khấu trừ khác không được âm.')
            if record.ngay_bat_dau and record.ngay_ket_thuc and record.ngay_ket_thuc < record.ngay_bat_dau:
                raise ValidationError('Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu áp dụng.')

    @api.constrains('nhan_vien_id', 'ngay_bat_dau', 'ngay_ket_thuc', 'trang_thai')
    def _check_overlap_active_configs(self):
        for record in self:
            if record.trang_thai != 'dang_ap_dung' or not record.nhan_vien_id:
                continue
            start_1 = record.ngay_bat_dau or date(1900, 1, 1)
            end_1 = record.ngay_ket_thuc or date(2999, 12, 31)
            others = self.search([
                ('id', '!=', record.id),
                ('nhan_vien_id', '=', record.nhan_vien_id.id),
                ('trang_thai', '=', 'dang_ap_dung'),
            ])
            for other in others:
                start_2 = other.ngay_bat_dau or date(1900, 1, 1)
                end_2 = other.ngay_ket_thuc or date(2999, 12, 31)
                if start_1 <= end_2 and start_2 <= end_1:
                    raise ValidationError('Mỗi nhân viên chỉ được có một cấu hình lương đang áp dụng tại một thời điểm.')
