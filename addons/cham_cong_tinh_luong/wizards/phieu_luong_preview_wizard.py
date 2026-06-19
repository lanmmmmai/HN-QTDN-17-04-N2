# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.exceptions import AccessError


class PhieuLuongPreviewWizard(models.TransientModel):
    _name = 'phieu_luong_preview_wizard'
    _description = 'Xem trước phiếu lương'

    bang_luong_id = fields.Many2one('bang_luong', string='Bảng lương', required=True)

    nhan_vien_id = fields.Many2one(related='bang_luong_id.nhan_vien_id', string='Nhân viên', readonly=True)
    thang = fields.Selection(related='bang_luong_id.thang', string='Tháng', readonly=True)
    nam = fields.Integer(related='bang_luong_id.nam', string='Năm', readonly=True)
    state = fields.Selection(related='bang_luong_id.state', string='Trạng thái', readonly=True)

    tong_ngay_cong = fields.Float(related='bang_luong_id.tong_ngay_cong', string='Tổng ngày công', readonly=True)
    so_ngay_di_lam = fields.Float(related='bang_luong_id.so_ngay_di_lam', string='Số ngày đi làm', readonly=True)
    tong_gio_lam = fields.Float(related='bang_luong_id.tong_gio_lam', string='Tổng giờ làm', readonly=True)
    tong_gio_tang_ca = fields.Float(related='bang_luong_id.tong_gio_tang_ca', string='Tổng giờ tăng ca', readonly=True)
    so_ngay_nghi = fields.Float(related='bang_luong_id.so_ngay_nghi', string='Số ngày nghỉ', readonly=True)

    luong_co_ban = fields.Float(related='bang_luong_id.luong_co_ban', string='Lương cơ bản', readonly=True)
    luong_theo_cong = fields.Float(related='bang_luong_id.luong_theo_cong', string='Lương theo ngày công', readonly=True)
    tong_phu_cap = fields.Float(related='bang_luong_id.tong_phu_cap', string='Tổng phụ cấp', readonly=True)
    tong_khen_thuong = fields.Float(related='bang_luong_id.tong_khen_thuong', string='Tổng khen thưởng', readonly=True)
    tong_ky_luat = fields.Float(related='bang_luong_id.tong_ky_luat', string='Tổng kỷ luật', readonly=True)
    tien_tang_ca = fields.Float(related='bang_luong_id.tien_tang_ca', string='Tiền tăng ca', readonly=True)
    tien_bao_hiem = fields.Float(related='bang_luong_id.tien_bao_hiem', string='Bảo hiểm', readonly=True)
    thue_tncn = fields.Float(related='bang_luong_id.thue_tncn', string='Thuế TNCN', readonly=True)
    khau_tru_khac = fields.Float(related='bang_luong_id.khau_tru_khac', string='Khấu trừ khác', readonly=True)
    tong_khau_tru = fields.Float(related='bang_luong_id.tong_khau_tru', string='Tổng khấu trừ', readonly=True)
    tong_luong = fields.Float(related='bang_luong_id.tong_luong', string='Tổng lương thực nhận', readonly=True)
    ghi_chu = fields.Text(related='bang_luong_id.ghi_chu', string='Ghi chú', readonly=True)

    def action_tai_pdf(self):
        self.ensure_one()
        bang_luong = self.bang_luong_id
        is_manager = (
            self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_quan_tri')
            or self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_ke_toan')
            or self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_nhan_su')
        )
        is_owner = (
            bang_luong.nhan_vien_id.user_id
            and bang_luong.nhan_vien_id.user_id.id == self.env.user.id
        )
        if not is_manager and not is_owner:
            raise AccessError('Bạn chỉ được tải phiếu lương của chính mình.')
        return self.env.ref('cham_cong_tinh_luong.action_report_bang_luong').report_action(bang_luong)
