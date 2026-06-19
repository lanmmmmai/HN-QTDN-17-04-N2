# -*- coding: utf-8 -*-
import logging
import os
import json
from datetime import date, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


# Reusable JSON schema fragments -------------------------------------------------
_QUERY_PARAMS = {
    'type': 'object',
    'properties': {
        'employee_scope': {
            'type': 'string',
            'enum': ['self', 'specific_employee'],
            'description': 'Phạm vi nhân viên: "self" là bản thân người hỏi, '
                           '"specific_employee" là một nhân viên cụ thể (chỉ quản lý mới được dùng).',
        },
        'employee_name': {
            'type': ['string', 'null'],
            'description': 'Tên nhân viên cụ thể nếu employee_scope = specific_employee.',
        },
        'period': {
            'type': 'string',
            'enum': ['current_month', 'last_month', 'specific_month'],
            'description': 'Kỳ thời gian.',
        },
        'month': {'type': ['integer', 'null'], 'description': 'Tháng (1-12) nếu period = specific_month.'},
        'year': {'type': ['integer', 'null'], 'description': 'Năm nếu period = specific_month.'},
    },
    'required': ['employee_scope', 'employee_name', 'period', 'month', 'year'],
    'additionalProperties': False,
}


def _query_tool(name, description):
    return {
        'type': 'function',
        'name': name,
        'description': description,
        'strict': True,
        'parameters': _QUERY_PARAMS,
    }


class AiChatbotService(models.AbstractModel):
    _name = 'ai.chatbot.service'
    _description = 'Dịch vụ AI Chatbot (OpenAI + Function Calling)'

    # ------------------------------------------------------------------
    # Function-calling tool definitions (OpenAI Responses API format)
    # ------------------------------------------------------------------
    _FC_TOOLS = [
        _query_tool('get_attendance_days',
                    'Tra cứu số ngày công / số giờ làm của nhân viên trong một kỳ.'),
        _query_tool('get_overtime_hours',
                    'Tra cứu số giờ tăng ca của nhân viên trong một kỳ.'),
        _query_tool('get_salary_monthly',
                    'Tra cứu tổng lương / lương theo tháng của nhân viên.'),
        _query_tool('get_hourly_salary_and_allowance',
                    'Tra cứu đơn giá giờ và các khoản phụ cấp của nhân viên.'),
        {
            'type': 'function',
            'name': 'create_attendance_request',
            'description': 'Tạo một bản ghi chấm công mới (cần người dùng xác nhận trước khi lưu).',
            'strict': True,
            'parameters': {
                'type': 'object',
                'properties': {
                    'employee_scope': {'type': 'string', 'enum': ['self', 'specific_employee']},
                    'employee_name': {'type': ['string', 'null']},
                    'date_text': {'type': 'string', 'description': 'Ngày chấm công dạng tự nhiên: hôm nay, hôm qua, ngày mai, DD/MM, DD/MM/YYYY.'},
                    'check_in': {'type': ['string', 'null'], 'description': 'Giờ vào dạng HH:MM.'},
                    'check_out': {'type': ['string', 'null'], 'description': 'Giờ ra dạng HH:MM.'},
                    'reason': {'type': ['string', 'null'], 'description': 'Ghi chú/lý do.'},
                },
                'required': ['employee_scope', 'employee_name', 'date_text', 'check_in', 'check_out', 'reason'],
                'additionalProperties': False,
            },
        },
        {
            'type': 'function',
            'name': 'update_attendance_request',
            'description': 'Cập nhật một bản ghi chấm công đã có (cần người dùng xác nhận).',
            'strict': True,
            'parameters': {
                'type': 'object',
                'properties': {
                    'employee_scope': {'type': 'string', 'enum': ['self', 'specific_employee']},
                    'employee_name': {'type': ['string', 'null']},
                    'date_text': {'type': 'string', 'description': 'Ngày của bản ghi cần sửa.'},
                    'check_in': {'type': ['string', 'null'], 'description': 'Giờ vào mới HH:MM.'},
                    'check_out': {'type': ['string', 'null'], 'description': 'Giờ ra mới HH:MM.'},
                    'reason': {'type': ['string', 'null']},
                },
                'required': ['employee_scope', 'employee_name', 'date_text', 'check_in', 'check_out', 'reason'],
                'additionalProperties': False,
            },
        },
        {
            'type': 'function',
            'name': 'create_leave_request',
            'description': 'Tạo yêu cầu nghỉ phép (cần người dùng xác nhận).',
            'strict': True,
            'parameters': {
                'type': 'object',
                'properties': {
                    'employee_scope': {'type': 'string', 'enum': ['self', 'specific_employee']},
                    'employee_name': {'type': ['string', 'null']},
                    'date_from_text': {'type': 'string', 'description': 'Ngày bắt đầu nghỉ.'},
                    'date_to_text': {'type': 'string', 'description': 'Ngày kết thúc nghỉ.'},
                    'leave_type': {'type': ['string', 'null'], 'enum': ['paid', 'unpaid', 'sick', 'other', None]},
                    'reason': {'type': ['string', 'null']},
                },
                'required': ['employee_scope', 'employee_name', 'date_from_text', 'date_to_text', 'leave_type', 'reason'],
                'additionalProperties': False,
            },
        },
        {
            'type': 'function',
            'name': 'print_payroll',
            'description': 'In / mở bảng lương của nhân viên cho một kỳ (cần người dùng xác nhận).',
            'strict': True,
            'parameters': {
                'type': 'object',
                'properties': {
                    'employee_scope': {'type': 'string', 'enum': ['self', 'specific_employee']},
                    'employee_name': {'type': ['string', 'null']},
                    'period': {'type': 'string', 'enum': ['current_month', 'last_month', 'specific_month']},
                    'month': {'type': ['integer', 'null']},
                    'year': {'type': ['integer', 'null']},
                },
                'required': ['employee_scope', 'employee_name', 'period', 'month', 'year'],
                'additionalProperties': False,
            },
        },
        {
            'type': 'function',
            'name': 'get_attendance_alerts',
            'description': 'Tra cứu các cảnh báo chấm công (đi muộn, về sớm, thiếu giờ ra,...) của nhân viên trong một kỳ.',
            'strict': True,
            'parameters': _QUERY_PARAMS,
        },
    ]

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def _get_param(self, key, default=None):
        return self.env['ir.config_parameter'].sudo().get_param(key, default)

    def _get_api_key(self):
        config_key = self._get_param('cham_cong_ai_chatbot.openai_api_key', '')
        env_key = os.getenv('OPENAI_API_KEY', '')
        return (config_key or env_key or '').strip()

    def _get_base_url(self):
        url = self._get_param('cham_cong_ai_chatbot.openai_base_url', 'https://api.openai.com/v1')
        return (url or 'https://api.openai.com/v1').rstrip('/')

    def _get_model(self):
        return self._get_param('cham_cong_ai_chatbot.openai_model', 'gpt-4o') or 'gpt-4o'

    def _get_timeout(self):
        try:
            return int(self._get_param('cham_cong_ai_chatbot.openai_timeout', 30) or 30)
        except (ValueError, TypeError):
            return 30

    def _is_fc_enabled(self):
        val = self._get_param('cham_cong_ai_chatbot.enable_function_calling', 'True')
        return str(val).lower() not in ('false', '0', '')

    def _key_hint(self, key):
        if not key:
            return ''
        if len(key) <= 8:
            return 'sk-...' + key[-4:]
        return key[:3] + '...' + key[-4:]

    # ------------------------------------------------------------------
    # OpenAI HTTP calls (Responses API)
    # ------------------------------------------------------------------
    def _headers(self):
        return {
            'Authorization': 'Bearer %s' % self._get_api_key(),
            'Content-Type': 'application/json',
        }

    def _call_openai_first(self, question, system_prompt):
        if requests is None:
            return None, 'Thư viện requests chưa được cài đặt.'
        body = {
            'model': self._get_model(),
            'input': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': question},
            ],
        }
        if self._is_fc_enabled():
            body['tools'] = self._FC_TOOLS
            body['tool_choice'] = 'auto'
        try:
            resp = requests.post(
                '%s/responses' % self._get_base_url(),
                headers=self._headers(), json=body, timeout=self._get_timeout(),
            )
            _logger.info('AI_CHATBOT_TOOL: first_call_status=%s', resp.status_code)
            if resp.status_code >= 400:
                return None, 'OpenAI lỗi %s: %s' % (resp.status_code, resp.text[:300])
            return resp.json(), None
        except Exception as exc:  # noqa: BLE001
            _logger.exception('AI_CHATBOT_TOOL: first_call exception')
            return None, str(exc)

    def _call_openai_second(self, question, system_prompt, func_call_id, func_name,
                            func_args_str, tool_result_str):
        if requests is None:
            return None, 'Thư viện requests chưa được cài đặt.'
        body = {
            'model': self._get_model(),
            'input': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': question},
                {
                    'type': 'function_call',
                    'call_id': func_call_id,
                    'name': func_name,
                    'arguments': func_args_str or '{}',
                },
                {
                    'type': 'function_call_output',
                    'call_id': func_call_id,
                    'output': tool_result_str,
                },
            ],
        }
        try:
            resp = requests.post(
                '%s/responses' % self._get_base_url(),
                headers=self._headers(), json=body, timeout=self._get_timeout(),
            )
            _logger.info('AI_CHATBOT_TOOL: second_call_status=%s', resp.status_code)
            if resp.status_code >= 400:
                return None, 'OpenAI lỗi %s: %s' % (resp.status_code, resp.text[:300])
            return resp.json(), None
        except Exception as exc:  # noqa: BLE001
            _logger.exception('AI_CHATBOT_TOOL: second_call exception')
            return None, str(exc)

    def _extract_text(self, payload):
        """Extract assistant text from a Responses API payload."""
        if not payload:
            return ''
        if payload.get('output_text'):
            return payload['output_text']
        texts = []
        for item in payload.get('output', []) or []:
            if item.get('type') == 'message':
                for part in item.get('content', []) or []:
                    if part.get('type') in ('output_text', 'text') and part.get('text'):
                        texts.append(part['text'])
        return '\n'.join(texts).strip()

    def _extract_function_call(self, payload):
        """Return (call_id, name, arguments_str) or (None, None, None)."""
        if not payload:
            return None, None, None
        for item in payload.get('output', []) or []:
            if item.get('type') == 'function_call':
                return item.get('call_id') or item.get('id'), item.get('name'), item.get('arguments') or '{}'
        return None, None, None

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------
    def _resolve_employee(self, employee_scope, employee_name, current_employee, management_user):
        """Return (employee_recordset, error_message)."""
        if employee_scope == 'specific_employee':
            if not management_user:
                return None, 'Bạn không có quyền tra cứu thông tin của nhân viên khác.'
            if not employee_name:
                return None, 'Vui lòng cung cấp tên nhân viên cần tra cứu.'
            employee = self.env['nhan_vien'].sudo().search(
                [('ho_va_ten', 'ilike', employee_name)], limit=1)
            if not employee:
                return None, 'Không tìm thấy nhân viên có tên "%s".' % employee_name
            return employee, None
        # self
        if not current_employee:
            return None, 'Tài khoản của bạn chưa được liên kết với hồ sơ nhân viên.'
        return current_employee, None

    def _resolve_period(self, period, month, year):
        """Return (month, year, start_date, end_date)."""
        today = fields.Date.context_today(self)
        if period == 'last_month':
            first_this = today.replace(day=1)
            last_prev = first_this - timedelta(days=1)
            month, year = last_prev.month, last_prev.year
        elif period == 'specific_month':
            month = month or today.month
            year = year or today.year
        else:  # current_month
            month, year = today.month, today.year
        start = date(year, month, 1)
        if month == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)
        return month, year, start, end

    def _parse_date_text(self, date_text):
        """Resolve natural-language Vietnamese date text into a date object."""
        today = fields.Date.context_today(self)
        if not date_text:
            return today
        txt = date_text.strip().lower()
        if txt in ('hôm nay', 'hom nay', 'today'):
            return today
        if txt in ('hôm qua', 'hom qua', 'yesterday'):
            return today - timedelta(days=1)
        if txt in ('ngày mai', 'ngay mai', 'tomorrow', 'mai'):
            return today + timedelta(days=1)
        # DD/MM/YYYY or DD/MM or DD-MM-YYYY
        cleaned = txt.replace('-', '/').replace('.', '/')
        parts = [p for p in cleaned.split('/') if p.strip()]
        try:
            if len(parts) == 3:
                d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
                if y < 100:
                    y += 2000
                return date(y, m, d)
            if len(parts) == 2:
                d, m = int(parts[0]), int(parts[1])
                return date(today.year, m, d)
        except (ValueError, TypeError):
            pass
        return today

    # ------------------------------------------------------------------
    # MAIN entry point
    # ------------------------------------------------------------------
    def _build_system_prompt(self, management_user, current_employee):
        today = fields.Date.context_today(self)
        emp_name = current_employee.ho_va_ten if current_employee else 'Chưa liên kết'
        role = 'quản lý/nhân sự' if management_user else 'nhân viên'
        return (
            "Bạn là trợ lý AI nhân sự cho hệ thống chấm công và tính lương. "
            "Hôm nay là %s. Người dùng hiện tại là %s (vai trò: %s). "
            "Hãy trả lời ngắn gọn, lịch sự bằng tiếng Việt. "
            "Khi người dùng hỏi về dữ liệu chấm công/lương, hãy gọi function phù hợp. "
            "Nếu người dùng không phải quản lý, chỉ được dùng employee_scope='self'. "
            "Khi giải thích cách tính lương, hãy dùng công thức: "
            "(Lương cơ bản / 26) × Số ngày đi làm thực tế + Phụ cấp + Khen thưởng - Kỷ luật. "
            "Khi người dùng muốn tạo/sửa chấm công, tạo nghỉ phép hoặc in bảng lương, "
            "hãy gọi function tương ứng - hệ thống sẽ yêu cầu xác nhận trước khi thực hiện. "
            "Nếu người dùng muốn tạo hoặc sửa chấm công mà thiếu giờ vào hoặc giờ ra, bạn phải hỏi lại để họ cung cấp đầy đủ cả hai. "
            "Khi gọi hàm tạo hoặc sửa chấm công thành công và trả về trạng thái chờ xác nhận (pending: true), hãy trả lời người dùng chính xác theo mẫu: "
            "'Tôi hiểu bạn muốn tạo/cập nhật chấm công ngày DD/MM/YYYY từ HH:MM đến HH:MM. Bạn có muốn xác nhận không?'"
            % (today, emp_name, role)
        )

    def _build_recent_history(self, session, current_question, limit=8):
        if not session or not session.message_ids:
            return ''
        messages = session.message_ids.sorted(
            key=lambda m: (m.create_date or fields.Datetime.now(), m.id))
        if messages and (messages[-1].role == 'user') and \
                ((messages[-1].content or '').strip() == (current_question or '').strip()):
            messages = messages[:-1]
        messages = messages[-limit:]
        lines = []
        for msg in messages:
            speaker = 'Người dùng' if msg.role == 'user' else 'AI'
            content = (msg.content or '').strip()
            if not content:
                continue
            lines.append('%s: %s' % (speaker, content))
        return '\n'.join(lines)

    def process_message(self, session, question, management_user, current_employee):
        """Main orchestration. Returns (answer_text, action_log_id_or_None)."""
        _logger.info('AI_CHATBOT_TOOL: question=%s', question)
        system_prompt = self._build_system_prompt(management_user, current_employee)
        recent_history = self._build_recent_history(session, question)
        if recent_history:
            system_prompt += (
                "\n\nNgữ cảnh hội thoại gần đây để hiểu câu trả lời theo mạch cuộc trò chuyện:\n"
                "%s" % recent_history
            )

        if not self._get_api_key():
            return ('Chưa cấu hình OpenAI API key. Vui lòng vào Cấu hình Chatbot để thiết lập.', None)

        payload, err = self._call_openai_first(question, system_prompt)
        if err:
            return ('Xin lỗi, đã có lỗi khi gọi AI: %s' % err, None)

        call_id, func_name, func_args_str = self._extract_function_call(payload)

        # No function call -> return text answer directly.
        if not func_name:
            answer = self._extract_text(payload) or 'Xin lỗi, tôi chưa có câu trả lời.'
            _logger.info('AI_CHATBOT_FINAL: answer_len=%s', len(answer))
            return (answer, None)

        try:
            func_args = json.loads(func_args_str or '{}')
        except (ValueError, TypeError):
            func_args = {}
        _logger.info('AI_CHATBOT_TOOL: function=%s arguments=%s', func_name, func_args)

        tool_result, action_log = self._dispatch_tool(
            func_name, func_args, session, current_employee, management_user, question)
        tool_result_str = json.dumps(tool_result, ensure_ascii=False, default=str)
        _logger.info('AI_CHATBOT_TOOL_RESULT: result=%s', tool_result_str[:500])

        payload2, err2 = self._call_openai_second(
            question, system_prompt, call_id, func_name, func_args_str, tool_result_str)
        if err2 or not payload2:
            # Fall back to a result-derived message.
            answer = tool_result.get('message') or tool_result.get('summary') \
                or 'Đã xử lý yêu cầu của bạn.'
        else:
            answer = self._extract_text(payload2) or tool_result.get('message') \
                or 'Đã xử lý yêu cầu của bạn.'

        _logger.info('AI_CHATBOT_FINAL: answer_len=%s', len(answer))
        return (answer, action_log.id if action_log else None)

    # ------------------------------------------------------------------
    # Tool dispatcher
    # ------------------------------------------------------------------
    def _dispatch_tool(self, func_name, func_args, session, current_employee, management_user, question=None):
        """Return (tool_result_dict, action_log_or_None)."""
        scope = func_args.get('employee_scope', 'self')
        emp_name = func_args.get('employee_name')

        # Query tools execute immediately.
        if func_name in ('get_attendance_days', 'get_overtime_hours',
                         'get_salary_monthly', 'get_hourly_salary_and_allowance',
                         'get_attendance_alerts'):
            employee, err = self._resolve_employee(scope, emp_name, current_employee, management_user)
            if err:
                return ({'success': False, 'message': err}, None)
            if func_name == 'get_attendance_days':
                return (self._exec_get_attendance_days(func_args, employee), None)
            if func_name == 'get_overtime_hours':
                return (self._exec_get_overtime_hours(func_args, employee), None)
            if func_name == 'get_salary_monthly':
                return (self._exec_get_salary_monthly(func_args, employee), None)
            if func_name == 'get_attendance_alerts':
                return (self._exec_get_attendance_alerts(func_args, employee), None)
            return (self._exec_get_hourly_salary_and_allowance(func_args, employee), None)

        # Action tools create a pending confirmation log.
        if func_name == 'create_attendance_request':
            employee, err = self._resolve_employee(scope, emp_name, current_employee, management_user)
            if err:
                return ({'success': False, 'message': err}, None)
            return self._create_attendance_pending(func_args, employee, session, question)
        if func_name == 'update_attendance_request':
            employee, err = self._resolve_employee(scope, emp_name, current_employee, management_user)
            if err:
                return ({'success': False, 'message': err}, None)
            return self._create_update_attendance_pending(func_args, employee, session, question)
        if func_name == 'create_leave_request':
            employee, err = self._resolve_employee(scope, emp_name, current_employee, management_user)
            if err:
                return ({'success': False, 'message': err}, None)
            return self._create_leave_pending(func_args, employee, session, question)
        if func_name == 'print_payroll':
            employee, err = self._resolve_employee(scope, emp_name, current_employee, management_user)
            if err:
                return ({'success': False, 'message': err}, None)
            return self._create_print_payroll_pending(func_args, employee, session, question)

        return ({'success': False, 'message': 'Chức năng không được hỗ trợ.'}, None)

    # ------------------------------------------------------------------
    # Query executors
    # ------------------------------------------------------------------
    def _exec_get_attendance_days(self, args, employee):
        month, year, start, end = self._resolve_period(
            args.get('period', 'current_month'), args.get('month'), args.get('year'))
        records = self.env['cham_cong'].sudo().search([
            ('nhan_vien_id', '=', employee.id),
            ('ngay_cham_cong', '>=', start),
            ('ngay_cham_cong', '<=', end),
        ])
        total_hours = sum(records.mapped('so_gio_lam'))
        return {
            'success': True,
            'employee': employee.ho_va_ten,
            'month': month, 'year': year,
            'attendance_days': len(records),
            'total_hours': round(total_hours, 2),
            'message': '%s có %s ngày công, tổng %.2f giờ làm trong tháng %s/%s.'
                       % (employee.ho_va_ten, len(records), total_hours, month, year),
        }

    def _exec_get_overtime_hours(self, args, employee):
        month, year, start, end = self._resolve_period(
            args.get('period', 'current_month'), args.get('month'), args.get('year'))
        records = self.env['cham_cong'].sudo().search([
            ('nhan_vien_id', '=', employee.id),
            ('ngay_cham_cong', '>=', start),
            ('ngay_cham_cong', '<=', end),
        ])
        ot = sum(records.mapped('so_gio_tang_ca'))
        return {
            'success': True,
            'employee': employee.ho_va_ten,
            'month': month, 'year': year,
            'overtime_hours': round(ot, 2),
            'message': '%s có %.2f giờ tăng ca trong tháng %s/%s.'
                       % (employee.ho_va_ten, ot, month, year),
        }

    def _find_payroll(self, employee, month, year):
        return self.env['bang_luong'].sudo().search([
            ('nhan_vien_id', '=', employee.id),
            ('thang', '=', str(month)),
            ('nam', '=', year),
        ], limit=1)

    def _exec_get_salary_monthly(self, args, employee):
        month, year, _start, _end = self._resolve_period(
            args.get('period', 'current_month'), args.get('month'), args.get('year'))
        payroll = self._find_payroll(employee, month, year)
        if not payroll:
            return {
                'success': False,
                'message': 'Chưa có bảng lương cho %s tháng %s/%s.'
                           % (employee.ho_va_ten, month, year),
            }
        return {
            'success': True,
            'employee': employee.ho_va_ten,
            'month': month, 'year': year,
            'so_ngay_di_lam': payroll.so_ngay_di_lam,
            'luong_theo_cong': payroll.luong_theo_cong,
            'tong_luong': payroll.tong_luong,
            'thuc_linh': payroll.thuc_linh,
            'luong_co_ban': payroll.luong_co_ban,
            'tong_phu_cap': payroll.tong_phu_cap,
            'tong_khen_thuong': payroll.tong_khen_thuong,
            'tong_ky_luat': payroll.tong_ky_luat,
            'tong_khau_tru': payroll.tong_khau_tru,
            'thue_tncn': payroll.thue_tncn,
            'tien_bao_hiem': payroll.tien_bao_hiem,
            'message': 'Tổng lương tháng %s/%s của %s là %s VND theo công thức (lương cơ bản / 26) × số ngày đi làm + phụ cấp + khen thưởng - kỷ luật - khấu trừ.'
                       % (month, year, employee.ho_va_ten, '{:,.0f}'.format(payroll.tong_luong)),
        }

    def _exec_get_hourly_salary_and_allowance(self, args, employee):
        month, year, _start, _end = self._resolve_period(
            args.get('period', 'current_month'), args.get('month'), args.get('year'))
        payroll = self._find_payroll(employee, month, year)
        if not payroll:
            return {
                'success': False,
                'message': 'Chưa có bảng lương cho %s tháng %s/%s.'
                           % (employee.ho_va_ten, month, year),
            }
        return {
            'success': True,
            'employee': employee.ho_va_ten,
            'month': month, 'year': year,
            'don_gia_gio': payroll.don_gia_gio,
            'phu_cap_an_trua': payroll.phu_cap_an_trua,
            'phu_cap_xang_xe': payroll.phu_cap_xang_xe,
            'phu_cap_trach_nhiem': payroll.phu_cap_trach_nhiem,
            'phu_cap_khac': payroll.phu_cap_khac,
            'tong_phu_cap': payroll.tong_phu_cap,
            'message': 'Đơn giá giờ của %s là %s VND/giờ; tổng phụ cấp %s VND (ăn trưa %s, xăng xe %s, trách nhiệm %s, khác %s).'
                       % (employee.ho_va_ten,
                          '{:,.0f}'.format(payroll.don_gia_gio),
                          '{:,.0f}'.format(payroll.tong_phu_cap),
                          '{:,.0f}'.format(payroll.phu_cap_an_trua),
                          '{:,.0f}'.format(payroll.phu_cap_xang_xe),
                          '{:,.0f}'.format(payroll.phu_cap_trach_nhiem),
                          '{:,.0f}'.format(payroll.phu_cap_khac)),
        }

    def _exec_get_attendance_alerts(self, args, employee):
        month, year, _start, _end = self._resolve_period(
            args.get('period', 'current_month'), args.get('month'), args.get('year'))
        alerts = self.env['canh_bao_cham_cong'].sudo().search([
            ('nhan_vien_id', '=', employee.id),
            ('thang', '=', str(month)),
            ('nam', '=', year),
        ], order='ngay_tao desc')
        if not alerts:
            return {
                'success': True,
                'employee': employee.ho_va_ten,
                'month': month, 'year': year,
                'message': 'Tháng này %s không có cảnh báo chấm công nào bất thường.' % employee.ho_va_ten,
            }
        alert_types = {
            'di_muon_nhieu': 'Đi muộn nhiều',
            'thieu_cong': 'Thiếu công',
            'tang_ca_qua_nhieu': 'Tăng ca quá nhiều',
            'luong_thap_bat_thuong': 'Lương thấp bất thường',
            'thieu_du_lieu_cham_cong': 'Thiếu dữ liệu chấm công',
            'bang_luong_chua_xac_nhan': 'Bảng lương chưa xác nhận',
            'du_lieu_cong_khong_hop_le': 'Dữ liệu công không hợp lệ',
            'di_muon': 'Đi muộn',
            've_som': 'Về sớm',
            'thieu_gio_ra': 'Thiếu giờ ra',
            'lam_qua_gio': 'Làm quá giờ',
            'trung_ngay': 'Chấm công trùng ngày',
            'chua_cham_cong': 'Chưa chấm công hôm nay',
        }
        lines = []
        for idx, alert in enumerate(alerts, 1):
            type_label = alert_types.get(alert.loai_canh_bao, alert.loai_canh_bao)
            lines.append('%s. %s: %s' % (idx, type_label, alert.noi_dung))
        message = 'Danh sách cảnh báo chấm công tháng %s/%s của %s:\n%s' % (month, year, employee.ho_va_ten, '\n'.join(lines))
        return {
            'success': True,
            'employee': employee.ho_va_ten,
            'month': month, 'year': year,
            'alerts_count': len(alerts),
            'message': message,
        }

    # ------------------------------------------------------------------
    # Action creators (produce a pending confirmation log; no execution)
    # ------------------------------------------------------------------
    def _create_log(self, vals):
        return self.env['ai.chat.action.log'].sudo().create(vals)

    def _create_attendance_pending(self, args, employee, session, question=None):
        check_in = args.get('check_in')
        check_out = args.get('check_out')
        if not check_in or not check_out:
            missing = []
            if not check_in:
                missing.append("giờ vào")
            if not check_out:
                missing.append("giờ ra")
            return ({
                'success': False,
                'message': 'Thiếu thông tin: %s. Vui lòng cung cấp giờ vào và giờ ra cụ thể để tôi có thể tạo yêu cầu chấm công.' % (' và '.join(missing)),
            }, None)

        the_date = self._parse_date_text(args.get('date_text'))
        # Duplicate check.
        existing = self.env['cham_cong'].sudo().search([
            ('nhan_vien_id', '=', employee.id),
            ('ngay_cham_cong', '=', the_date),
        ], limit=1)
        if existing:
            return ({
                'success': False,
                'message': 'Đã tồn tại bản ghi chấm công cho %s ngày %s. '
                           'Bạn có thể yêu cầu cập nhật thay vì tạo mới.'
                           % (employee.ho_va_ten, the_date.strftime('%d/%m/%Y')),
            }, None)
        data = {
            'employee_id': employee.id,
            'date': str(the_date),
            'check_in': check_in,
            'check_out': check_out,
            'reason': args.get('reason'),
        }
        summary = ('Tạo chấm công cho %s ngày %s: vào %s - ra %s.%s'
                   % (employee.ho_va_ten, the_date.strftime('%d/%m/%Y'),
                      check_in or '?', check_out or '?',
                      ' Lý do: %s.' % args['reason'] if args.get('reason') else ''))
        log = self._create_log({
            'session_id': session.id if session else False,
            'user_id': self.env.user.id,
            'employee_id': employee.id,
            'action_type': 'create_attendance',
            'original_text': question or json.dumps(args, ensure_ascii=False),
            'extracted_data': json.dumps(data, ensure_ascii=False),
            'summary': summary,
            'state': 'pending_confirm',
            'target_model': 'cham_cong',
            'intent': 'Tạo chấm công',
            'function_name': 'create_attendance_request',
        })
        return ({'success': True, 'pending': True, 'summary': summary, 'message': summary}, log)

    def _create_update_attendance_pending(self, args, employee, session, question=None):
        check_in = args.get('check_in')
        check_out = args.get('check_out')
        if not check_in and not check_out:
            return ({
                'success': False,
                'message': 'Thiếu thông tin: giờ vào hoặc giờ ra mới. Vui lòng cung cấp giờ vào hoặc giờ ra mới để tôi có thể tạo yêu cầu cập nhật chấm công.',
            }, None)

        the_date = self._parse_date_text(args.get('date_text'))
        record = self.env['cham_cong'].sudo().search([
            ('nhan_vien_id', '=', employee.id),
            ('ngay_cham_cong', '=', the_date),
        ], limit=1)
        if not record:
            return ({
                'success': False,
                'message': 'Không tìm thấy bản ghi chấm công của %s ngày %s để cập nhật.'
                           % (employee.ho_va_ten, the_date.strftime('%d/%m/%Y')),
            }, None)
        data = {
            'employee_id': employee.id,
            'target_record_id': record.id,
            'date': str(the_date),
            'check_in': check_in,
            'check_out': check_out,
            'reason': args.get('reason'),
        }
        changes = []
        if check_in:
            changes.append('giờ vào -> %s' % check_in)
        if check_out:
            changes.append('giờ ra -> %s' % check_out)
        if args.get('reason'):
            changes.append('ghi chú -> %s' % args['reason'])
        summary = ('Cập nhật chấm công của %s ngày %s: %s.'
                   % (employee.ho_va_ten, the_date.strftime('%d/%m/%Y'),
                      ', '.join(changes) if changes else 'không có thay đổi'))
        log = self._create_log({
            'session_id': session.id if session else False,
            'user_id': self.env.user.id,
            'employee_id': employee.id,
            'action_type': 'update_attendance',
            'original_text': question or json.dumps(args, ensure_ascii=False),
            'extracted_data': json.dumps(data, ensure_ascii=False),
            'summary': summary,
            'state': 'pending_confirm',
            'target_model': 'cham_cong',
            'target_record_id': record.id,
            'intent': 'Cập nhật chấm công',
            'function_name': 'update_attendance_request',
        })
        return ({'success': True, 'pending': True, 'summary': summary, 'message': summary}, log)

    def _create_leave_pending(self, args, employee, session, question=None):
        date_from = self._parse_date_text(args.get('date_from_text'))
        date_to = self._parse_date_text(args.get('date_to_text'))
        data = {
            'employee_id': employee.id,
            'date_from': str(date_from),
            'date_to': str(date_to),
            'leave_type': args.get('leave_type'),
            'reason': args.get('reason'),
        }
        summary = ('Tạo nghỉ phép cho %s từ %s đến %s (loại: %s).%s'
                   % (employee.ho_va_ten, date_from.strftime('%d/%m/%Y'),
                      date_to.strftime('%d/%m/%Y'), args.get('leave_type') or 'không xác định',
                      ' Lý do: %s.' % args['reason'] if args.get('reason') else ''))
        log = self._create_log({
            'session_id': session.id if session else False,
            'user_id': self.env.user.id,
            'employee_id': employee.id,
            'action_type': 'create_leave',
            'original_text': question or json.dumps(args, ensure_ascii=False),
            'extracted_data': json.dumps(data, ensure_ascii=False),
            'summary': summary,
            'state': 'pending_confirm',
            'intent': 'Tạo nghỉ phép',
            'function_name': 'create_leave_request',
        })
        return ({'success': True, 'pending': True, 'summary': summary, 'message': summary}, log)

    def _create_print_payroll_pending(self, args, employee, session, question=None):
        month, year, _start, _end = self._resolve_period(
            args.get('period', 'current_month'), args.get('month'), args.get('year'))
        payroll = self._find_payroll(employee, month, year)
        if not payroll:
            return ({
                'success': False,
                'message': 'Chưa có bảng lương cho %s tháng %s/%s để in.'
                           % (employee.ho_va_ten, month, year),
            }, None)
        data = {
            'employee_id': employee.id,
            'target_record_id': payroll.id,
            'month': month, 'year': year,
        }
        summary = ('In bảng lương của %s tháng %s/%s (tổng lương %s VND).'
                   % (employee.ho_va_ten, month, year, '{:,.0f}'.format(payroll.tong_luong)))
        log = self._create_log({
            'session_id': session.id if session else False,
            'user_id': self.env.user.id,
            'employee_id': employee.id,
            'action_type': 'print_payroll',
            'original_text': question or json.dumps(args, ensure_ascii=False),
            'extracted_data': json.dumps(data, ensure_ascii=False),
            'summary': summary,
            'state': 'pending_confirm',
            'target_model': 'bang_luong',
            'target_record_id': payroll.id,
            'intent': 'In phiếu lương',
            'function_name': 'print_payroll',
        })
        return ({'success': True, 'pending': True, 'summary': summary, 'message': summary}, log)
