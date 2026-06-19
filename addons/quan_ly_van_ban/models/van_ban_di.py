# -*- coding: utf-8 -*-
from odoo import models, fields, api


class VanBanDi(models.Model):
    _name = 'van_ban_di'
    _description = 'Văn bản đi'
    _rec_name = 'ten_van_ban'
    _order = 'ngay_phat_hanh desc, id desc'

    so_van_ban_di = fields.Char(string='Số đi', required=True)
    so_hieu_van_ban = fields.Char(string='Số/Ký hiệu phát hành', required=True)
    ten_van_ban = fields.Char(string='Tên văn bản', required=True)

    loai_van_ban_id = fields.Many2one('loai_van_ban', string='Loại văn bản')

    ngay_phat_hanh = fields.Date(string='Ngày phát hành', default=fields.Date.context_today)
    trich_yeu = fields.Text(string='Trích yếu nội dung')

    don_vi_soan_thao_id = fields.Many2one('don_vi', string='Đơn vị soạn thảo')
    nguoi_ky_id = fields.Many2one('nhan_vien', string='Người ký')

    noi_nhan = fields.Char(string='Nơi nhận ngoài hệ thống')

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
            ('du_thao', 'Dự thảo'),
            ('cho_ky', 'Chờ ký'),
            ('da_ky', 'Đã ký'),
            ('da_phat_hanh', 'Đã phát hành'),
            ('luu_tru', 'Lưu trữ'),
        ],
        string='Trạng thái',
        default='du_thao',
    )

    ghi_chu = fields.Text(string='Ghi chú')

    # --- Onchange liên kết Đơn vị ↔ Nhân viên ---
    # nhan_vien.phong_ban_id là computed Many2one tới don_vi

    @api.onchange('don_vi_soan_thao_id')
    def _onchange_don_vi_soan_thao_id(self):
        if self.don_vi_soan_thao_id:
            if (self.nguoi_ky_id
                    and self.nguoi_ky_id.phong_ban_id != self.don_vi_soan_thao_id):
                self.nguoi_ky_id = False
            return {'domain': {'nguoi_ky_id': [('phong_ban_id', '=', self.don_vi_soan_thao_id.id)]}}
        return {'domain': {'nguoi_ky_id': []}}

    @api.onchange('nguoi_ky_id')
    def _onchange_nguoi_ky_id(self):
        if self.nguoi_ky_id and self.nguoi_ky_id.phong_ban_id:
            self.don_vi_soan_thao_id = self.nguoi_ky_id.phong_ban_id

    # --- Chuyển trạng thái ---

    def action_cho_ky(self):
        self.write({'trang_thai': 'cho_ky'})

    def action_da_ky(self):
        self.write({'trang_thai': 'da_ky'})

    def action_phat_hanh(self):
        self.write({'trang_thai': 'da_phat_hanh'})

    def action_luu_tru(self):
        self.write({'trang_thai': 'luu_tru'})

