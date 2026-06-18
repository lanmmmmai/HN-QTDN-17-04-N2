# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_chatbot_enable_openai = fields.Boolean(
        string='Bật OpenAI',
        config_parameter='cham_cong_ai_chatbot.enable_openai',
    )
    ai_chatbot_api_key = fields.Char(
        string='OpenAI API Key',
        config_parameter='cham_cong_ai_chatbot.openai_api_key',
    )
    ai_chatbot_base_url = fields.Char(
        string='OpenAI Base URL', default='https://api.openai.com/v1',
        config_parameter='cham_cong_ai_chatbot.openai_base_url',
    )
    ai_chatbot_model = fields.Char(
        string='Model', default='gpt-4o',
        config_parameter='cham_cong_ai_chatbot.openai_model',
    )
    ai_chatbot_enable_fc = fields.Boolean(
        string='Bật Function Calling', default=True,
        config_parameter='cham_cong_ai_chatbot.enable_function_calling',
    )
    ai_chatbot_enable_confirm = fields.Boolean(
        string='Bật xác nhận hành động', default=True,
        config_parameter='cham_cong_ai_chatbot.enable_action_confirmation',
    )
    ai_chatbot_allow_create_attendance = fields.Boolean(
        string='Cho phép tạo chấm công', default=True,
        config_parameter='cham_cong_ai_chatbot.allow_create_attendance',
    )
    ai_chatbot_allow_update_attendance = fields.Boolean(
        string='Cho phép sửa chấm công', default=True,
        config_parameter='cham_cong_ai_chatbot.allow_update_attendance',
    )
    ai_chatbot_allow_create_leave = fields.Boolean(
        string='Cho phép tạo nghỉ phép', default=True,
        config_parameter='cham_cong_ai_chatbot.allow_create_leave',
    )
    ai_chatbot_allow_print_payroll = fields.Boolean(
        string='Cho phép in bảng lương', default=True,
        config_parameter='cham_cong_ai_chatbot.allow_print_payroll',
    )
    ai_chatbot_use_fallback = fields.Boolean(
        string='Dùng fallback rule-based', default=True,
        config_parameter='cham_cong_ai_chatbot.use_rule_based_fallback',
    )
    ai_chatbot_save_history = fields.Boolean(
        string='Lưu lịch sử chat', default=True,
        config_parameter='cham_cong_ai_chatbot.save_chat_history',
    )
    ai_chatbot_timeout = fields.Integer(
        string='Timeout (giây)', default=30,
        config_parameter='cham_cong_ai_chatbot.openai_timeout',
    )
