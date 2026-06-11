# -*- coding: utf-8 -*-
from odoo import models, fields


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

    trang_thai = fields.Selection(
        [
            ('du_thao', 'Dự thảo'),
            ('cho_ky', 'Chờ ký'),
            ('da_phat_hanh', 'Đã phát hành'),
            ('luu_tru', 'Lưu trữ'),
        ],
        string='Trạng thái',
        default='du_thao',
    )

    ghi_chu = fields.Text(string='Ghi chú')

