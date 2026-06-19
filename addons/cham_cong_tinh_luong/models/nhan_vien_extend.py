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
    khen_thuong_ky_luat_ids = fields.One2many(
        'khen_thuong_ky_luat',
        inverse_name='nhan_vien_id',
        string='Khen thưởng / Kỷ luật',
    )
    canh_bao_cham_cong_ids = fields.One2many(
        'canh_bao_cham_cong',
        inverse_name='nhan_vien_id',
        string='Cảnh báo thông minh',
    )

    def _open_related_action(self, xmlid, domain=None, context=None):
        self.ensure_one()
        action = self.env.ref(xmlid).read()[0]
        if domain is not None:
            action['domain'] = domain
        if context:
            action['context'] = dict(self.env.context, **context)
        return action

    def action_open_cham_cong(self):
        return self._open_related_action(
            'cham_cong_tinh_luong.action_cham_cong_cua_toi',
            domain=[('nhan_vien_id', '=', self.id)],
        )

    def action_open_bang_luong(self):
        return self._open_related_action(
            'cham_cong_tinh_luong.action_bang_luong_cua_toi',
            domain=[('nhan_vien_id', '=', self.id)],
        )

    def action_open_cau_hinh_luong(self):
        return self._open_related_action(
            'cham_cong_tinh_luong.action_cau_hinh_luong',
            domain=[('nhan_vien_id', '=', self.id)],
        )

    def action_open_canh_bao(self):
        return self._open_related_action(
            'cham_cong_tinh_luong.action_canh_bao_cua_toi',
            domain=[('nhan_vien_id', '=', self.id)],
        )
