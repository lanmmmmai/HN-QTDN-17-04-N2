# -*- coding: utf-8 -*-
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

MANAGER_GROUPS = [
    'cham_cong_tinh_luong.group_cham_cong_nhan_su',
    'cham_cong_tinh_luong.group_cham_cong_quan_tri',
    'cham_cong_ai_chatbot.group_ai_chatbot_manager',
]

EMPLOYEE_GROUP = 'cham_cong_ai_chatbot.group_ai_chatbot_employee_user'
SYSTEM_GROUP = 'base.group_system'


class AiChatbotController(http.Controller):

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _current_employee(self):
        return request.env['nhan_vien'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1)

    def _is_manager(self):
        user = request.env.user
        for grp in MANAGER_GROUPS:
            try:
                if user.has_group(grp):
                    return True
            except ValueError:
                continue
        return False

    def _can_use_employee_chatbot(self):
        user = request.env.user
        return user.has_group(EMPLOYEE_GROUP) or user.has_group(SYSTEM_GROUP) or self._is_manager()

    def _owns_session(self, session):
        return session and (session.user_id.id == request.env.user.id or self._is_manager())

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    @http.route('/ai_chatbot/send_message', type='json', auth='user')
    def send_message(self, **kwargs):
        try:
            if not self._can_use_employee_chatbot():
                return {'success': False, 'error': 'Bạn không có quyền dùng chatbot nhân viên.'}
            session_id = kwargs.get('session_id')
            message = (kwargs.get('message') or '').strip()
            if not message:
                return {'success': False, 'error': 'Tin nhắn trống.'}

            Session = request.env['ai.chat.session'].sudo()
            session = Session.browse(int(session_id)) if session_id else Session
            if not session or not session.exists():
                session = Session.create({'user_id': request.env.user.id})
            elif not self._owns_session(session):
                return {'success': False, 'error': 'Bạn không có quyền truy cập phiên chat này.'}

            result = session._process_user_message(message)
            if not result.get('success'):
                return {'success': False, 'error': result.get('error') or 'Đã có lỗi xảy ra.'}
            return result
        except Exception as exc:  # noqa: BLE001
            _logger.exception('AI_CHATBOT_CONTROLLER: send_message failed')
            return {'success': False, 'error': str(exc)}

    @http.route('/ai_chatbot/get_sessions', type='json', auth='user')
    def get_sessions(self, **kwargs):
        try:
            if not self._can_use_employee_chatbot():
                return {'success': False, 'error': 'Bạn không có quyền dùng chatbot nhân viên.', 'sessions': []}
            domain = [('state', '=', 'active'), ('user_id', '=', request.env.user.id)]
            if self._is_manager():
                domain = [('state', '=', 'active')]
            sessions = request.env['ai.chat.session'].sudo().search(
                domain, order='write_date desc')
            data = [{
                'id': s.id,
                'name': s.name,
                'last_message': s.last_message or '',
                'message_count': s.message_count,
                'write_date': str(s.write_date) if s.write_date else '',
            } for s in sessions]
            return {'success': True, 'sessions': data}
        except Exception as exc:  # noqa: BLE001
            _logger.exception('AI_CHATBOT_CONTROLLER: get_sessions failed')
            return {'success': False, 'error': str(exc), 'sessions': []}

    @http.route('/ai_chatbot/get_messages', type='json', auth='user')
    def get_messages(self, **kwargs):
        try:
            if not self._can_use_employee_chatbot():
                return {'success': False, 'error': 'Bạn không có quyền dùng chatbot nhân viên.', 'messages': []}
            session_id = kwargs.get('session_id')
            if not session_id:
                return {'success': False, 'error': 'Thiếu session_id.', 'messages': []}
            session = request.env['ai.chat.session'].sudo().browse(int(session_id))
            if not session.exists() or not self._owns_session(session):
                return {'success': False, 'error': 'Không có quyền truy cập.', 'messages': []}
            messages = [{
                'id': m.id,
                'role': m.role,
                'content': m.content or '',
                'function_name': m.function_name or '',
                'create_date': str(m.create_date) if m.create_date else '',
            } for m in session.message_ids]
            return {'success': True, 'messages': messages}
        except Exception as exc:  # noqa: BLE001
            _logger.exception('AI_CHATBOT_CONTROLLER: get_messages failed')
            return {'success': False, 'error': str(exc), 'messages': []}

    @http.route('/ai_chatbot/create_session', type='json', auth='user')
    def create_session(self, **kwargs):
        try:
            if not self._can_use_employee_chatbot():
                return {'success': False, 'error': 'Bạn không có quyền dùng chatbot nhân viên.'}
            session = request.env['ai.chat.session'].sudo().create({
                'user_id': request.env.user.id,
            })
            return {'success': True, 'session_id': session.id, 'name': session.name}
        except Exception as exc:  # noqa: BLE001
            _logger.exception('AI_CHATBOT_CONTROLLER: create_session failed')
            return {'success': False, 'error': str(exc)}

    @http.route('/ai_chatbot/confirm_action', type='json', auth='user')
    def confirm_action(self, **kwargs):
        try:
            if not self._can_use_employee_chatbot():
                return {'success': False, 'error': 'Bạn không có quyền dùng chatbot nhân viên.'}
            log_id = kwargs.get('action_log_id')
            if not log_id:
                return {'success': False, 'error': 'Thiếu action_log_id.'}
            log = request.env['ai.chat.action.log'].sudo().browse(int(log_id))
            if not log.exists():
                return {'success': False, 'error': 'Không tìm thấy hành động.'}
            if log.user_id.id != request.env.user.id and not self._is_manager():
                return {'success': False, 'error': 'Bạn không có quyền xác nhận hành động này.'}
            action_dict = log.action_confirm()
            if log.state == 'error':
                return {'success': False, 'error': log.error_message or 'Lỗi khi thực hiện.'}
            res = {
                'success': True,
                'message': 'Đã thực hiện: %s' % (log.summary or log.name),
                'error': None,
            }
            if isinstance(action_dict, dict):
                res['action'] = action_dict
            return res
        except Exception as exc:  # noqa: BLE001
            _logger.exception('AI_CHATBOT_CONTROLLER: confirm_action failed')
            return {'success': False, 'error': str(exc)}

    @http.route('/ai_chatbot/cancel_action', type='json', auth='user')
    def cancel_action(self, **kwargs):
        try:
            if not self._can_use_employee_chatbot():
                return {'success': False, 'error': 'Bạn không có quyền dùng chatbot nhân viên.'}
            log_id = kwargs.get('action_log_id')
            if not log_id:
                return {'success': False, 'error': 'Thiếu action_log_id.'}
            log = request.env['ai.chat.action.log'].sudo().browse(int(log_id))
            if not log.exists():
                return {'success': False, 'error': 'Không tìm thấy hành động.'}
            if log.user_id.id != request.env.user.id and not self._is_manager():
                return {'success': False, 'error': 'Bạn không có quyền hủy hành động này.'}
            log.action_cancel()
            return {'success': True, 'message': 'Đã hủy hành động.'}
        except Exception as exc:  # noqa: BLE001
            _logger.exception('AI_CHATBOT_CONTROLLER: cancel_action failed')
            return {'success': False, 'error': str(exc)}

    @http.route('/ai_chatbot/delete_session', type='json', auth='user')
    def delete_session(self, **kwargs):
        try:
            if not self._can_use_employee_chatbot():
                return {'success': False, 'error': 'Bạn không có quyền dùng chatbot nhân viên.'}
            session_id = kwargs.get('session_id')
            if not session_id:
                return {'success': False, 'error': 'Thiếu session_id.'}
            session = request.env['ai.chat.session'].sudo().browse(int(session_id))
            if not session.exists() or not self._owns_session(session):
                return {'success': False, 'error': 'Không có quyền.'}
            session.action_archive()
            return {'success': True}
        except Exception as exc:  # noqa: BLE001
            _logger.exception('AI_CHATBOT_CONTROLLER: delete_session failed')
            return {'success': False, 'error': str(exc)}
