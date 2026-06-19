# -*- coding: utf-8 -*-

from datetime import date
from odoo import api, fields, models


def get_month_range(thang, nam):
    """Trở về (ngay_bat_dau, ngay_ket_thuc) cho tháng và năm tương ứng."""
    month = int(thang)
    year = int(nam)
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    return start_date, end_date


class NhanVienThongTinMixin(models.AbstractModel):
    _name = 'nhan_vien_thong_tin.mixin'
    _description = 'Mixin thông tin nhân viên'

    phong_ban_id = fields.Many2one(
        'don_vi',
        string='Phòng ban',
        compute='_compute_thong_tin_nhan_vien',
        readonly=True,
    )
    chuc_vu_id = fields.Many2one(
        'chuc_vu',
        string='Chức vụ',
        compute='_compute_thong_tin_nhan_vien',
        readonly=True,
    )

    @api.depends('nhan_vien_id')
    def _compute_thong_tin_nhan_vien(self):
        employee_ids = self.mapped('nhan_vien_id').ids
        latest_histories = {}
        if employee_ids:
            histories = self.env['lich_su_cong_tac'].search(
                [('nhan_vien_id', 'in', employee_ids)],
                order='nhan_vien_id desc, id desc',
            )
            for history in histories:
                latest_histories.setdefault(history.nhan_vien_id.id, history)

        for record in self:
            history = latest_histories.get(record.nhan_vien_id.id)
            record.phong_ban_id = history.don_vi_id if history else False
            record.chuc_vu_id = history.chuc_vu_id if history else False
