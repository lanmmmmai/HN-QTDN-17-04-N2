# Plan 008: Nâng cấp AI Chatbot Nhân sự lên chuẩn OpenAI Chat Completions API

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Goal:** Nâng cấp cơ chế kết nối từ API không chuẩn (`/responses`) sang chuẩn REST API `/chat/completions` (Chat Completions) của OpenAI hỗ trợ Function Calling (Tool Calling).
>
> **Architecture:**
> - Chuyển đổi định dạng khai báo công cụ (`_FC_TOOLS`) sang chuẩn cấu trúc OpenAI `{"type": "function", "function": {...}}`.
> - Sửa đổi các phương thức kết nối HTTP trong `ai_chatbot_service.py` để trỏ tới `%s/chat/completions` thay vì `%s/responses`.
> - Định cấu hình gửi/nhận payload đúng định dạng tin nhắn chuẩn của OpenAI (`messages` thay vì `input`, `tool_calls` và `role: tool` thay vì `function_call`).
>
> **Tech Stack:** Python 3, Odoo 15.0 model API, `requests` library.

## Global Constraints

- Tương thích hoàn toàn với Odoo 15.0.
- Trả về mã lỗi và thông điệp lỗi tiếng Việt thân thiện thay vì crash.
- Phải duy trì tất cả các hàm nghiệp vụ Odoo sẵn có (`get_attendance_days`, `get_overtime_hours`, v.v.).

---

### Task 1: Định nghĩa lại cấu trúc công cụ chuẩn và hàm tiện ích trong `ai_chatbot_service.py`

**Files:**
- Modify: `addons/cham_cong_ai_chatbot/models/ai_chatbot_service.py:17-153`

- [ ] **Step 1: Cấu trúc lại hàm helper `_query_tool` và danh sách `_FC_TOOLS`**
  Thay thế `_query_tool` và `_FC_TOOLS` để đóng gói các tham số đúng chuẩn `function` của OpenAI:
  
  ```python
  def _query_tool(name, description):
      return {
          'type': 'function',
          'function': {
              'name': name,
              'description': description,
              'strict': True,
              'parameters': _QUERY_PARAMS,
          }
      }
  ```

  Cập nhật tất cả khai báo phần tử trong `_FC_TOOLS` theo định dạng chuẩn:
  
  ```python
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
              'function': {
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
              }
          },
          {
              'type': 'function',
              'function': {
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
              }
          },
          {
              'type': 'function',
              'function': {
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
              }
          },
          {
              'type': 'function',
              'function': {
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
              }
          },
          {
              'type': 'function',
              'function': {
                  'name': 'get_attendance_alerts',
                  'description': 'Tra cứu các cảnh báo chấm công (đi muộn, về sớm, thiếu giờ ra,...) của nhân viên trong một kỳ.',
                  'strict': True,
                  'parameters': _QUERY_PARAMS,
              }
          },
      ]
  ```

- [ ] **Step 2: Commit**
  ```bash
  git add addons/cham_cong_ai_chatbot/models/ai_chatbot_service.py
  git commit -m "refactor: update chatbot tool definitions to standard OpenAI schema"
  ```

---

### Task 2: Cập nhật hàm gọi HTTP và bóc tách dữ liệu phản hồi

**Files:**
- Modify: `addons/cham_cong_ai_chatbot/models/ai_chatbot_service.py:198-281`

- [ ] **Step 1: Thay thế hàm `_call_openai_first`, `_call_openai_second`, `_extract_text` và `_extract_function_call`**
  Cập nhật mã nguồn thành:
  
  ```python
      def _call_openai_first(self, question, system_prompt):
          if requests is None:
              return None, 'Thư viện requests chưa được cài đặt.'
          body = {
              'model': self._get_model(),
              'messages': [
                  {'role': 'system', 'content': system_prompt},
                  {'role': 'user', 'content': question},
              ],
          }
          if self._is_fc_enabled():
              body['tools'] = self._FC_TOOLS
              body['tool_choice'] = 'auto'
          try:
              resp = requests.post(
                  '%s/chat/completions' % self._get_base_url(),
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
          
          # Định dạng OpenAI chuẩn yêu cầu chứa message role 'assistant' với tool_calls,
          # theo sau là message role 'tool' chứa output của tool.
          assistant_message = {
              'role': 'assistant',
              'tool_calls': [
                  {
                      'id': func_call_id,
                      'type': 'function',
                      'function': {
                          'name': func_name,
                          'arguments': func_args_str or '{}',
                      }
                  }
              ]
          }
          tool_message = {
              'role': 'tool',
              'tool_call_id': func_call_id,
              'name': func_name,
              'content': tool_result_str,
          }
          
          body = {
              'model': self._get_model(),
              'messages': [
                  {'role': 'system', 'content': system_prompt},
                  {'role': 'user', 'content': question},
                  assistant_message,
                  tool_message,
              ],
          }
          try:
              resp = requests.post(
                  '%s/chat/completions' % self._get_base_url(),
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
          if not payload:
              return ''
          choices = payload.get('choices', [])
          if choices:
              return choices[0].get('message', {}).get('content', '') or ''
          return ''
  
      def _extract_function_call(self, payload):
          if not payload:
              return None, None, None
          choices = payload.get('choices', [])
          if not choices:
              return None, None, None
          message = choices[0].get('message', {})
          tool_calls = message.get('tool_calls', [])
          if tool_calls:
              tool_call = tool_calls[0]
              func = tool_call.get('function', {})
              return tool_call.get('id'), func.get('name'), func.get('arguments') or '{}'
          return None, None, None
  ```

- [ ] **Step 2: Commit**
  ```bash
  git add addons/cham_cong_ai_chatbot/models/ai_chatbot_service.py
  git commit -m "feat: upgrade chatbot HTTP calling logic to use standard Chat Completions endpoint"
  ```

---

### Task 3: Viết bộ kiểm thử tích hợp (Unit Tests) giả lập cho AI Chatbot

**Files:**
- Create: `addons/cham_cong_ai_chatbot/tests/__init__.py`
- Create: `addons/cham_cong_ai_chatbot/tests/test_chatbot.py`
- Modify: `addons/cham_cong_ai_chatbot/__init__.py`

- [ ] **Step 1: Đăng ký thư mục tests**
  Thêm import `tests` vào `addons/cham_cong_ai_chatbot/__init__.py`:
  
  ```python
  # -*- coding: utf-8 -*-
  from . import models
  from . import controllers
  from . import tests
  ```

- [ ] **Step 2: Tạo tệp `addons/cham_cong_ai_chatbot/tests/__init__.py`**
  ```python
  # -*- coding: utf-8 -*-
  from . import test_chatbot
  ```

- [ ] **Step 3: Tạo tệp `addons/cham_cong_ai_chatbot/tests/test_chatbot.py`**
  Viết mock cho cuộc gọi `requests` để kiểm thử logic xử lý:
  
  ```python
  # -*- coding: utf-8 -*-
  from unittest.mock import patch
  from odoo.tests.common import TransactionCase
  
  class TestAIChatbot(TransactionCase):
  
      def setUp(self):
          super(TestAIChatbot, self).setUp()
          self.session = self.env['ai.chat.session'].create({
              'user_id': self.env.user.id,
              'name': 'Test Session',
          })
          self.chatbot_service = self.env['ai.chatbot.service']
          
          # Thiết lập cấu hình API key giả định
          self.env['ir.config_parameter'].set_param('cham_cong_ai_chatbot.openai_api_key', 'mock-key')
          self.env['ir.config_parameter'].set_param('cham_cong_ai_chatbot.openai_base_url', 'https://api.mock.openai/v1')
  
      @patch('requests.post')
      def test_chatbot_text_response(self, mock_post):
          """Kiểm thử chatbot khi nhận câu trả lời dạng text thuần túy"""
          mock_post.return_value.status_code = 200
          mock_post.return_value.json.return_value = {
              'choices': [{
                  'message': {
                      'role': 'assistant',
                      'content': 'Xin chào, tôi là trợ lý AI nhân sự.'
                  }
              }]
          }
          
          result = self.session._process_user_message('Xin chào')
          self.assertTrue(result['success'])
          self.assertEqual(result['answer'], 'Xin chào, tôi là trợ lý AI nhân sự.')
          
          # Kiểm tra tin nhắn được lưu
          messages = self.session.message_ids.sorted('id')
          self.assertEqual(len(messages), 2)
          self.assertEqual(messages[0].role, 'user')
          self.assertEqual(messages[0].content, 'Xin chào')
          self.assertEqual(messages[1].role, 'assistant')
          self.assertEqual(messages[1].content, 'Xin chào, tôi là trợ lý AI nhân sự.')
  
      @patch('requests.post')
      def test_chatbot_function_calling_flow(self, mock_post):
          """Kiểm thử luồng Function Calling: hỏi ngày công và tự động điền kết quả vào context"""
          # Lần gọi thứ 1: Trả về yêu cầu gọi hàm get_attendance_days
          response_1 = {
              'choices': [{
                  'message': {
                      'role': 'assistant',
                      'tool_calls': [{
                          'id': 'call_123',
                          'type': 'function',
                          'function': {
                              'name': 'get_attendance_days',
                              'arguments': '{"employee_scope": "self", "period": "current_month"}'
                          }
                      }]
                  }
              }]
          }
          
          # Lần gọi thứ 2: Trả về câu trả lời tổng hợp cuối cùng
          response_2 = {
              'choices': [{
                  'message': {
                      'role': 'assistant',
                      'content': 'Bạn đã đi làm 22 ngày công trong tháng này.'
                  }
              }]
          }
          
          class MockResponse:
              def __init__(self, json_data, status_code=200):
                  self.json_data = json_data
                  self.status_code = status_code
                  self.text = ""
              def json(self):
                  return self.json_data
                  
          mock_post.side_effect = [
              MockResponse(response_1),
              MockResponse(response_2)
          ]
          
          result = self.session._process_user_message('Tháng này tôi đi làm bao nhiêu ngày?')
          self.assertTrue(result['success'])
          self.assertEqual(result['answer'], 'Bạn đã đi làm 22 ngày công trong tháng này.')
          self.assertEqual(mock_post.call_count, 2)
  ```

- [ ] **Step 4: Chạy kiểm thử tự động bằng Odoo test runner**
  Chạy lệnh test (Giả định Odoo đang chạy trong môi trường host):
  `python3 odoo-bin -d odoo -i cham_cong_ai_chatbot --test-enable --stop-after-init`
  (Hoặc chạy qua container Docker nếu Docker đang hoạt động).

- [ ] **Step 5: Commit**
  ```bash
  git add addons/cham_cong_ai_chatbot/tests/
  git add addons/cham_cong_ai_chatbot/__init__.py
  git commit -m "test: add unit tests for chatbot standard API and function calling"
  ```

---

## Done criteria

- [ ] `_FC_TOOLS` được đổi tên trường tham số và cấu trúc đúng chuẩn.
- [ ] Endpoint `/chat/completions` hoạt động hoàn hảo khi kết nối với OpenAI thực tế (hoặc proxy tương thích).
- [ ] Logic xử lý Tool Calls đệ trình kết quả với vai trò `tool` chuẩn xác, không bị API từ chối.
- [ ] Bộ test `TestAIChatbot` chạy qua màu xanh (PASS) hoàn toàn.

## STOP conditions

- Lỗi API 400 Bad Request trả về từ OpenAI khi gửi cấu trúc tin nhắn.
- Lỗi logic bóc tách `tool_calls` gây treo phiên xử lý hoặc đệ quy vô hạn.
