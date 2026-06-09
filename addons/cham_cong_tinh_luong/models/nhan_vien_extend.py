# -*- coding: utf-8 -*-

from odoo import fields, models


class NhanVien(models.Model):
    _inherit = 'nhan_vien'

    cham_cong_ids = fields.One2many(
        'cham_cong',
        inverse_name='nhan_vien_id',
        string='Danh sách chấm công',
    )
    cau_hinh_luong_ids = fields.One2many(
        'cau_hinh_luong',
        inverse_name='nhan_vien_id',
        string='Cấu hình lương',
    )
    bang_luong_ids = fields.One2many(
        'bang_luong',
        inverse_name='nhan_vien_id',
        string='Danh sách bảng lương',
    )
    canh_bao_cham_cong_ids = fields.One2many(
        'canh_bao_cham_cong',
        inverse_name='nhan_vien_id',
        string='Cảnh báo thông minh',
    )
