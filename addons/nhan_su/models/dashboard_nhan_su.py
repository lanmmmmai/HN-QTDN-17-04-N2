# -*- coding: utf-8 -*-

from odoo import api, fields, models


class DashboardNhanSu(models.Model):
    _name = 'dashboard_nhan_su'
    _description = 'Dashboard Quản lý Nhân sự'

    name = fields.Char(string='Tên', required=True, default='Dashboard nhân sự')

    tong_nhan_vien = fields.Integer(string='Tổng nhân viên', compute='_compute_stats')
    tong_don_vi = fields.Integer(string='Tổng đơn vị/phòng ban', compute='_compute_stats')
    tong_chuc_vu = fields.Integer(string='Tổng chức vụ', compute='_compute_stats')
    nhan_vien_co_chung_chi = fields.Integer(string='Nhân viên có chứng chỉ/bằng cấp', compute='_compute_stats')
    tong_lich_su_cong_tac = fields.Integer(string='Tổng lịch sử công tác', compute='_compute_stats')
    tong_loai_chung_chi = fields.Integer(string='Loại chứng chỉ/bằng cấp', compute='_compute_stats')
    recent_nhan_vien_ids = fields.Many2many(
        'nhan_vien',
        string='Nhân viên mới thêm gần đây',
        compute='_compute_stats',
    )

    @api.depends()
    def _compute_stats(self):
        tong_nv = self.env['nhan_vien'].search_count([])
        tong_dv = self.env['don_vi'].search_count([])
        tong_cv = self.env['chuc_vu'].search_count([])
        tong_ls = self.env['lich_su_cong_tac'].search_count([])
        tong_loai_cc = self.env['chung_chi_bang_cap'].search_count([])
        nv_co_cc = len(self.env['danh_sach_chung_chi_bang_cap'].read_group([], ['nhan_vien_id'], ['nhan_vien_id']))
        recent_nhan_vien_ids = self.env['nhan_vien'].search([], order='id desc', limit=5)
        for record in self:
            record.tong_nhan_vien = tong_nv
            record.tong_don_vi = tong_dv
            record.tong_chuc_vu = tong_cv
            record.nhan_vien_co_chung_chi = nv_co_cc
            record.tong_lich_su_cong_tac = tong_ls
            record.tong_loai_chung_chi = tong_loai_cc
            record.recent_nhan_vien_ids = recent_nhan_vien_ids

    def action_refresh(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_open_nhan_vien(self):
        return self.env.ref('nhan_su.action_nhan_vien').read()[0]

    def action_create_nhan_vien(self):
        action = self.env.ref('nhan_su.action_nhan_vien').read()[0]
        action['view_mode'] = 'form'
        action['views'] = [(self.env.ref('nhan_su.view_nhan_vien_form').id, 'form')]
        action['target'] = 'current'
        action['context'] = dict(self.env.context, form_view_initial_mode='edit')
        return action

    def action_open_don_vi(self):
        return self.env.ref('nhan_su.action_don_vi').read()[0]

    def action_open_chuc_vu(self):
        return self.env.ref('nhan_su.action_chuc_vu').read()[0]

    def action_open_chung_chi(self):
        return self.env.ref('nhan_su.action_chung_chi_bang_cap').read()[0]

    def action_open_danh_sach_chung_chi(self):
        return self.env.ref('nhan_su.action_danh_sach_chung_chi_bang_cap').read()[0]

    def action_open_lich_su(self):
        return self.env.ref('nhan_su.action_lich_su_cong_tac').read()[0]

    @api.model
    def open_dashboard(self):
        record = self.search([], limit=1)
        if not record:
            record = self.sudo().create({'name': 'Dashboard nhân sự'})
        return {
            'name': 'Dashboard nhân sự',
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': record.id,
            'views': [(False, 'form')],
            'target': 'current',
        }
