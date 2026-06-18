{
    'name': 'AI Chatbot Nhân sự - Cấp độ 3',
    'summary': 'AI Chatbot với Function Calling + Action Confirmation',
    'version': '15.0.3.0.0',
    'category': 'Human Resources',
    'author': 'Business Internship',
    'depends': [
        'base',
        'web',
        'mail',
        'cham_cong_tinh_luong',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/ai_chatbot_views.xml',
        'views/ai_chatbot_admin_views.xml',
        'views/ai_chatbot_settings_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cham_cong_ai_chatbot/static/src/js/ai_chatbot_client_action.js',
            'cham_cong_ai_chatbot/static/src/scss/ai_chatbot.scss',
        ],
        'web.assets_qweb': [
            'cham_cong_ai_chatbot/static/src/xml/ai_chatbot_client_action.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
