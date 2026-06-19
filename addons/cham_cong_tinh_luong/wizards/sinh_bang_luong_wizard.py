# -*- coding: utf-8 -*-

from odoo import fields, models


class SinhBangLuongWizard(models.TransientModel):
    _name = 'sinh_bang_luong_wizard'
    _description = 'Sinh bảng lương hàng loạt'

    thang = fields.Selection(
        [(str(i), 'Tháng %s' % i) for i in range(1, 13)],
        required=True,
        default=lambda self: str(fields.Date.context_today(self).month),
    )
    nam = fields.Integer(required=True, default=lambda self: fields.Date.context_today(self).year)
    nhan_vien_ids = fields.Many2many('nhan_vien', string='Nhân viên')

    def action_sinh_bang_luong(self):
        self.ensure_one()
        employee_ids = self.nhan_vien_ids.ids or None
        return self.env['bang_luong'].action_sinh_bang_luong_thang(self.thang, self.nam, employee_ids)
