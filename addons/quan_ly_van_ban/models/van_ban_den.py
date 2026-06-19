# -*- coding: utf-8 -*-
from odoo import models, fields, api


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

    do_mat = fields.Selection(
        [
            ('thuong', 'Thường'),
            ('mat', 'Mật'),
            ('toi_mat', 'Tối mật'),
            ('tuyet_mat', 'Tuyệt mật'),
        ],
        string='Độ mật',
        default='thuong',
    )
    do_khan = fields.Selection(
        [
            ('thuong', 'Thường'),
            ('khan', 'Khẩn'),
            ('hoa_toc', 'Hỏa tốc'),
            ('thuong_khan', 'Thượng khẩn'),
        ],
        string='Độ khẩn',
        default='thuong',
    )

    trang_thai = fields.Selection(
        [
            ('moi', 'Mới'),
            ('vao_so', 'Đã vào sổ'),
            ('dang_xu_ly', 'Đang xử lý'),
            ('da_xu_ly', 'Đã xử lý'),
            ('luu_tru', 'Lưu trữ'),
        ],
        string='Trạng thái',
        default='moi',
    )

    ghi_chu = fields.Text(string='Ghi chú')

    # --- Onchange liên kết Đơn vị ↔ Nhân viên ---
    # nhan_vien.phong_ban_id là computed Many2one tới don_vi

    @api.onchange('don_vi_nhan_id')
    def _onchange_don_vi_nhan_id(self):
        if self.don_vi_nhan_id:
            if (self.nhan_vien_xu_ly_id
                    and self.nhan_vien_xu_ly_id.phong_ban_id != self.don_vi_nhan_id):
                self.nhan_vien_xu_ly_id = False
            return {'domain': {'nhan_vien_xu_ly_id': [('phong_ban_id', '=', self.don_vi_nhan_id.id)]}}
        return {'domain': {'nhan_vien_xu_ly_id': []}}

    @api.onchange('nhan_vien_xu_ly_id')
    def _onchange_nhan_vien_xu_ly_id(self):
        if self.nhan_vien_xu_ly_id and self.nhan_vien_xu_ly_id.phong_ban_id:
            self.don_vi_nhan_id = self.nhan_vien_xu_ly_id.phong_ban_id

    # --- Chuyển trạng thái ---

    def action_vao_so(self):
        self.write({'trang_thai': 'vao_so'})

    def action_chuyen_xu_ly(self):
        self.write({'trang_thai': 'dang_xu_ly'})

    def action_da_xu_ly(self):
        self.write({'trang_thai': 'da_xu_ly'})

    def action_luu_tru(self):
        self.write({'trang_thai': 'luu_tru'})

