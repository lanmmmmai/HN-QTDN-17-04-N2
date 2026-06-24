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
        
        # Để gọi được get_attendance_days, ta cần có nhân viên tương ứng liên kết với user
        employee = self.env['nhan_vien'].search([('user_id', '=', self.env.user.id)], limit=1)
        if not employee:
            import random
            ma_random = 'NV_TEST_%s' % random.randint(1000, 9999)
            employee = self.env['nhan_vien'].create({
                'ho_ten_dem': 'Test',
                'ten': 'Employee',
                'ma_dinh_danh': ma_random,
                'user_id': self.env.user.id,
            })
        
        result = self.session._process_user_message('Tháng này tôi đi làm bao nhiêu ngày?')
        self.assertTrue(result['success'])
        self.assertEqual(result['answer'], 'Bạn đã đi làm 22 ngày công trong tháng này.')
        self.assertEqual(mock_post.call_count, 2)
