# -*- coding: utf-8 -*-
import re
import unicodedata

from odoo import api, fields, models
from odoo.exceptions import UserError


class AiChatSession(models.Model):
    _name = 'ai.chat.session'
    _description = 'Phiên chat AI'
    _order = 'write_date desc, id desc'

    name = fields.Char(string='Tên phiên', required=True, default='Phiên chat mới')
    user_id = fields.Many2one(
        'res.users', string='Người dùng', required=True, readonly=True,
        default=lambda self: self.env.user, ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'nhan_vien', string='Nhân viên', readonly=True,
        compute='_compute_employee_id', store=True,
    )
    message_ids = fields.One2many(
        'ai.chat.message', 'session_id', string='Tin nhắn',
    )
    action_log_ids = fields.One2many(
        'ai.chat.action.log', 'session_id', string='Log hành động',
    )
    new_message = fields.Text(string='Nhập tin nhắn')
    last_message = fields.Char(
        string='Tin nhắn gần nhất', compute='_compute_last_message',
    )
    message_count = fields.Integer(
        string='Số tin nhắn', compute='_compute_message_count', store=True,
    )
    action_count = fields.Integer(
        string='Số hành động', compute='_compute_action_count', store=True,
    )
    pending_action_count = fields.Integer(
        string='Số hành động chờ xác nhận', compute='_compute_pending_action_count',
    )
    pending_action_id = fields.Many2one(
        'ai.chat.action.log', string='Bản ghi chờ xác nhận', compute='_compute_pending_action_id',
    )
    pending_action_summary = fields.Text(
        string='Tóm tắt hành động chờ xác nhận', compute='_compute_pending_action_summary',
    )
    state = fields.Selection(
        [('active', 'Đang dùng'), ('archived', 'Lưu trữ')],
        string='Trạng thái', default='active',
    )

    @api.depends('user_id')
    def _compute_employee_id(self):
        for rec in self:
            employee = False
            if rec.user_id:
                employee = self.env['nhan_vien'].sudo().search(
                    [('user_id', '=', rec.user_id.id)], limit=1)
            rec.employee_id = employee.id if employee else False

    def _compute_last_message(self):
        for rec in self:
            msg = rec.message_ids.sorted(key=lambda m: (m.create_date or fields.Datetime.now(), m.id))
            if msg:
                content = msg[-1].content or ''
                rec.last_message = content[:80]
            else:
                rec.last_message = ''

    @api.depends('message_ids')
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.message_ids)

    @api.depends('action_log_ids')
    def _compute_action_count(self):
        for rec in self:
            rec.action_count = len(rec.action_log_ids)

    @api.depends('action_log_ids', 'action_log_ids.state')
    def _compute_pending_action_count(self):
        for rec in self:
            rec.pending_action_count = len(
                rec.action_log_ids.filtered(lambda a: a.state == 'pending_confirm'))

    @api.depends('action_log_ids', 'action_log_ids.state', 'action_log_ids.create_date')
    def _compute_pending_action_id(self):
        for rec in self:
            pending_logs = rec.action_log_ids.filtered(
                lambda a: a.state == 'pending_confirm').sorted(
                    key=lambda a: (a.create_date or fields.Datetime.now(), a.id))
            rec.pending_action_id = pending_logs[-1] if pending_logs else False
            rec.pending_action_summary = rec.pending_action_id.summary if rec.pending_action_id else ''

    def _current_employee(self):
        self.ensure_one()
        return self.env['nhan_vien'].sudo().search(
            [('user_id', '=', self.env.user.id)], limit=1)

    def _open_form_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ai.chat.session',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }

    def _create_chat_message(self, role, content, employee=None):
        self.ensure_one()
        return self.env['ai.chat.message'].sudo().create({
            'session_id': self.id,
            'user_id': self.env.user.id,
            'employee_id': employee.id if employee else False,
            'role': role,
            'content': content or '',
        })

    def _normalize_reply_text(self, text):
        normalized = (text or '').replace('đ', 'd').replace('Đ', 'D')
        normalized = unicodedata.normalize('NFKD', normalized)
        normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = normalized.lower().strip()
        normalized = re.sub(r'[^a-z0-9]+', ' ', normalized)
        return re.sub(r'\s+', ' ', normalized).strip()

    def _is_affirmative_reply(self, text):
        normalized = self._normalize_reply_text(text)
        return normalized in {
            'co', 'ok', 'okay', 'dong y', 'dong y nhe', 'xac nhan',
            'yes', 'y', 'duoc', 'toi chac chan', 'chac chan',
            'chac chan roi', 'lam di', 'duyet', 'co nhe', 'dong y di',
        }

    def _get_latest_pending_action(self):
        self.ensure_one()
        return self.env['ai.chat.action.log'].sudo().search([
            ('session_id', '=', self.id),
            ('state', '=', 'pending_confirm'),
        ], order='create_date desc, id desc', limit=1)

    def _is_negative_reply(self, text):
        normalized = self._normalize_reply_text(text)
        return normalized in {
            'khong', 'khong nhe', 'huy', 'cancel', 'no', 'n', 'khong dong y',
            'khong phai', 'khong can', 'thoi', 'thoi bo', 'bo qua',
        } or normalized.startswith('khong ') or ' khong ' in normalized

    def _process_user_message(self, message):
        self.ensure_one()
        text = (message or '').strip()
        if not text:
            return {'success': False, 'error': 'Tin nhắn trống.'}

        employee = self._current_employee()
        is_manager = self.env.user.has_group('cham_cong_ai_chatbot.group_ai_chatbot_manager') or \
            self.env.user.has_group('cham_cong_ai_chatbot.group_ai_chatbot_admin') or \
            self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_nhan_su') or \
            self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_quan_tri')

        pending = self._get_latest_pending_action()
        if pending and (self._is_affirmative_reply(text) or self._is_negative_reply(text)):
            user_message = self._create_chat_message('user', text, employee)
            if self._is_affirmative_reply(text):
                pending.action_confirm()
                if pending.state == 'error':
                    answer = pending.error_message or 'Không thể tạo phiếu chấm công.'
                elif pending.action_type == 'create_attendance':
                    answer = 'Đã tạo phiếu chấm công thành công.'
                elif pending.action_type == 'update_attendance':
                    answer = 'Đã cập nhật phiếu chấm công thành công.'
                elif pending.action_type == 'create_leave':
                    answer = 'Đã tạo yêu cầu nghỉ phép thành công.'
                elif pending.action_type == 'print_payroll':
                    answer = 'Đã mở/in bảng lương thành công.'
                else:
                    answer = 'Đã thực hiện hành động thành công.'
            else:
                pending.action_cancel()
                answer = 'Đã hủy hành động.'

            assistant_message = self._create_chat_message('assistant', answer, employee)
            if pending.exists():
                pending.write({'message_id': assistant_message.id})
            return {
                'success': True,
                'session_id': self.id,
                'answer': answer,
                'pending_action': None,
                'user_message_id': user_message.id,
                'assistant_message_id': assistant_message.id,
            }

        user_message = self.env['ai.chat.message'].sudo().create({
            'session_id': self.id,
            'user_id': self.env.user.id,
            'employee_id': employee.id if employee else False,
            'role': 'user',
            'content': text,
        })

        if self.name in ('Phiên chat mới', False):
            self.write({'name': text[:40]})

        answer, action_log_id = self.env['ai.chatbot.service'].sudo().process_message(
            self, text, is_manager, employee)

        assistant_message = self.env['ai.chat.message'].sudo().create({
            'session_id': self.id,
            'user_id': self.env.user.id,
            'employee_id': employee.id if employee else False,
            'role': 'assistant',
            'content': answer or 'Đã xử lý yêu cầu.',
        })

        pending = None
        if action_log_id:
            log = self.env['ai.chat.action.log'].sudo().browse(action_log_id)
            if log.exists():
                log.write({'message_id': assistant_message.id})
                pending = {
                    'id': log.id,
                    'summary': log.summary or '',
                    'action_type': log.action_type,
                }

        return {
            'success': True,
            'session_id': self.id,
            'answer': answer or 'Đã xử lý yêu cầu.',
            'pending_action': pending,
            'user_message_id': user_message.id,
            'assistant_message_id': assistant_message.id,
        }

    def action_new_session(self):
        session = self.env['ai.chat.session'].sudo().create({
            'user_id': self.env.user.id,
        })
        return session._open_form_action()

    def action_send_message(self):
        self.ensure_one()
        text = (self.new_message or '').strip()
        if not text:
            raise UserError('Tin nhắn trống.')
        result = self._process_user_message(text)
        if not result.get('success'):
            raise UserError(result.get('error') or 'Không thể gửi tin nhắn.')

        self.write({'new_message': False})
        return self._open_form_action()

    def action_confirm_pending_action(self):
        self.ensure_one()
        pending = self._get_latest_pending_action()
        if pending:
            pending.action_confirm()
        return self._open_form_action()

    def action_cancel_pending_action(self):
        self.ensure_one()
        pending = self._get_latest_pending_action()
        if pending:
            pending.action_cancel()
        return self._open_form_action()

    def action_archive(self):
        self.write({'state': 'archived'})
        return True

    def action_activate(self):
        self.write({'state': 'active'})
        return True
