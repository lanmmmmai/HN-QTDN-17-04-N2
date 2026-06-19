# -*- coding: utf-8 -*-
from odoo import fields, models


class AiChatMessage(models.Model):
    _name = 'ai.chat.message'
    _description = 'Tin nhắn chat AI'
    _order = 'create_date asc, id asc'

    session_id = fields.Many2one(
        'ai.chat.session', string='Phiên chat', required=True, ondelete='cascade',
    )
    user_id = fields.Many2one('res.users', string='Người dùng')
    employee_id = fields.Many2one('nhan_vien', string='Nhân viên')
    role = fields.Selection(
        [('user', 'Người dùng'), ('assistant', 'AI'), ('system', 'Hệ thống')],
        string='Vai trò', default='user',
    )
    content = fields.Text(string='Nội dung', required=True)
    intent = fields.Char(string='Ý định')
    function_name = fields.Char(string='Hàm gọi')
    raw_payload = fields.Text(string='Dữ liệu thô')
    error_message = fields.Text(string='Lỗi')
    sequence = fields.Integer(string='Thứ tự', default=10)
