# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DashboardVanBan(models.Model):
    _name = 'dashboard_van_ban'
    _description = 'Dashboard Quản lý Văn bản'

    name = fields.Char(string='Tên', required=True, default='Dashboard văn bản')

    tong_van_ban_den = fields.Integer(string='Tổng văn bản đến', compute='_compute_stats')
    tong_van_ban_di = fields.Integer(string='Tổng văn bản đi', compute='_compute_stats')
    den_dang_xu_ly = fields.Integer(string='VBĐ đang xử lý', compute='_compute_stats')
    den_da_xu_ly = fields.Integer(string='VBĐ đã xử lý', compute='_compute_stats')
    den_qua_han = fields.Integer(string='VBĐ quá hạn', compute='_compute_stats')
    di_du_thao = fields.Integer(string='VBDi dự thảo', compute='_compute_stats')
    di_cho_ky = fields.Integer(string='VBDi chờ ký', compute='_compute_stats')
    di_da_phat_hanh = fields.Integer(string='VBDi đã phát hành', compute='_compute_stats')

    @api.depends()
    def _compute_stats(self):
        today = fields.Date.context_today(self)
        VBD = self.env['van_ban_den']
        VBI = self.env['van_ban_di']
        tong_den = VBD.search_count([])
        tong_di = VBI.search_count([])
        dang_xl = VBD.search_count([('trang_thai', 'in', ['moi', 'vao_so', 'dang_xu_ly'])])
        da_xl = VBD.search_count([('trang_thai', '=', 'da_xu_ly')])
        qua_han = VBD.search_count([
            ('han_xu_ly', '<', today),
            ('trang_thai', 'not in', ['da_xu_ly', 'luu_tru']),
        ])
        du_thao = VBI.search_count([('trang_thai', '=', 'du_thao')])
        cho_ky = VBI.search_count([('trang_thai', '=', 'cho_ky')])
        da_ph = VBI.search_count([('trang_thai', '=', 'da_phat_hanh')])
        for record in self:
            record.tong_van_ban_den = tong_den
            record.tong_van_ban_di = tong_di
            record.den_dang_xu_ly = dang_xl
            record.den_da_xu_ly = da_xl
            record.den_qua_han = qua_han
            record.di_du_thao = du_thao
            record.di_cho_ky = cho_ky
            record.di_da_phat_hanh = da_ph

    def action_refresh(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_open_van_ban_den(self):
        return self.env.ref('quan_ly_van_ban.action_van_ban_den').read()[0]

    def action_tao_van_ban_den(self):
        action = self.env.ref('quan_ly_van_ban.action_van_ban_den').read()[0]
        action['view_mode'] = 'form'
        action['views'] = [(False, 'form')]
        action['target'] = 'current'
        action['context'] = dict(self.env.context, form_view_initial_mode='edit')
        return action

    def action_open_van_ban_di(self):
        return self.env.ref('quan_ly_van_ban.action_van_ban_di').read()[0]

    def action_tao_van_ban_di(self):
        action = self.env.ref('quan_ly_van_ban.action_van_ban_di').read()[0]
        action['view_mode'] = 'form'
        action['views'] = [(False, 'form')]
        action['target'] = 'current'
        action['context'] = dict(self.env.context, form_view_initial_mode='edit')
        return action

    def action_open_dang_xu_ly(self):
        return self.env.ref('quan_ly_van_ban.action_van_ban_den_dang_xu_ly').read()[0]

    def action_open_qua_han(self):
        return self.env.ref('quan_ly_van_ban.action_van_ban_den_qua_han').read()[0]

    def action_open_cho_ky(self):
        return self.env.ref('quan_ly_van_ban.action_van_ban_di_cho_ky').read()[0]

    def action_open_da_phat_hanh(self):
        return self.env.ref('quan_ly_van_ban.action_van_ban_di_da_phat_hanh').read()[0]

    def action_open_loai_van_ban(self):
        return self.env.ref('quan_ly_van_ban.action_loai_van_ban').read()[0]

    @api.model
    def open_dashboard(self):
        record = self.search([], limit=1)
        if not record:
            record = self.sudo().create({'name': 'Dashboard văn bản'})
        return {
            'name': 'Dashboard văn bản',
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': record.id,
            'views': [(False, 'form')],
            'target': 'current',
        }
