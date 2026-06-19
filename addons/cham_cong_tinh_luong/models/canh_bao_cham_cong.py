# -*- coding: utf-8 -*-

from odoo import fields, models


class CanhBaoChamCong(models.Model):
    _name = 'canh_bao_cham_cong'
    _description = 'Cảnh báo chấm công'
    _order = 'ngay_tao desc, muc_do desc, id desc'

    nhan_vien_id = fields.Many2one('nhan_vien', string='Nhân viên', required=True, ondelete='cascade')
    thang = fields.Selection([(str(i), 'Tháng %s' % i) for i in range(1, 13)], string='Tháng', required=True)
    nam = fields.Integer(string='Năm', required=True)
    loai_canh_bao = fields.Selection(
        [
            ('di_muon_nhieu', 'Đi muộn nhiều'),
            ('thieu_cong', 'Thiếu công'),
            ('tang_ca_qua_nhieu', 'Tăng ca quá nhiều'),
            ('luong_thap_bat_thuong', 'Lương thấp bất thường'),
            ('thieu_du_lieu_cham_cong', 'Thiếu dữ liệu chấm công'),
            ('bang_luong_chua_xac_nhan', 'Bảng lương chưa xác nhận'),
            ('du_lieu_cong_khong_hop_le', 'Dữ liệu công không hợp lệ'),
            ('di_muon', 'Đi muộn'),
            ('ve_som', 'Về sớm'),
            ('thieu_gio_ra', 'Thiếu giờ ra'),
            ('lam_qua_gio', 'Làm quá giờ'),
            ('trung_ngay', 'Chấm công trùng ngày'),
            ('chua_cham_cong', 'Chưa chấm công hôm nay'),
        ],
        string='Loại cảnh báo',
        required=True,
    )
    muc_do = fields.Selection(
        [('thap', 'Thấp'), ('trung_binh', 'Trung bình'), ('cao', 'Cao')],
        string='Mức độ',
        required=True,
        default='trung_binh',
    )
    noi_dung = fields.Text(string='Nội dung', required=True)
    goi_y_xu_ly = fields.Text(string='Gợi ý xử lý')
    ngay_tao = fields.Datetime(string='Ngày tạo', default=fields.Datetime.now, required=True)
    state = fields.Selection(
        [('moi', 'Mới'), ('da_xem', 'Đã xem'), ('da_xu_ly', 'Đã xử lý')],
        string='Trạng thái',
        default='moi',
        required=True,
    )

    def action_danh_dau_da_xem(self):
        self.write({'state': 'da_xem'})

    def action_danh_dau_da_xu_ly(self):
        self.write({'state': 'da_xu_ly'})
