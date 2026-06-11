# -*- coding: utf-8 -*-
from odoo import models, fields


class LoaiVanBan(models.Model):
    _name = 'loai_van_ban'
    _description = 'Loại văn bản'
    _rec_name = 'ten_loai'

    ten_loai = fields.Char(string='Tên loại văn bản', required=True)
    ma_loai = fields.Char(string='Mã loại')
    mo_ta = fields.Text(string='Mô tả')
    active = fields.Boolean(string='Đang sử dụng', default=True)

