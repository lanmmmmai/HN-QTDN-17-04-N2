# -*- coding: utf-8 -*-
from odoo import models, fields


class VanBanDen(models.Model):
    _name = 'van_ban_den'
    _description = 'Văn bản đến'
    _rec_name = 'ten_van_ban'
    _order = 'ngay_den desc, id desc'

    so_van_ban_den = fields.Char(string='Số đến', required=True)
    so_hieu_van_ban = fields.Char(string='Số/Ký hiệu gốc', required=True)
    ten_van_ban = fields.Char(string='Tên văn bản', required=True)

    loai_van_ban_id = fields.Many2one('loai_van_ban', string='Loại văn bản')

    ngay_den = fields.Date(string='Ngày đến', default=fields.Date.context_today)
    ngay_ban_hanh = fields.Date(string='Ngày ban hành')
    co_quan_ban_hanh = fields.Char(string='Cơ quan ban hành')
    trich_yeu = fields.Text(string='Trích yếu nội dung')

    don_vi_nhan_id = fields.Many2one('don_vi', string='Đơn vị nhận xử lý')
    nhan_vien_xu_ly_id = fields.Many2one('nhan_vien', string='Người xử lý chính')

    han_xu_ly = fields.Date(string='Hạn xử lý')

    trang_thai = fields.Selection(
        [
            ('moi', 'Mới'),
            ('dang_xu_ly', 'Đang xử lý'),
            ('da_xu_ly', 'Đã xử lý'),
            ('luu_tru', 'Lưu trữ'),
        ],
        string='Trạng thái',
        default='moi',
    )

    ghi_chu = fields.Text(string='Ghi chú')

