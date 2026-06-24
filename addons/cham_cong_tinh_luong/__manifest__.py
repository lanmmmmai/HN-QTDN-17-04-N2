# -*- coding: utf-8 -*-
{
    'name': 'Chấm công và Tính lương',
    'summary': 'Quản lý chấm công, cấu hình lương và bảng lương nhân viên',
    'description': """
Module chấm công và tính lương tích hợp với module Quản lý nhân sự.
    """,
    'author': 'Business Internship',
    'website': '',
    'category': 'Human Resources',
    'version': '15.0.1.0.0',

    'depends': [
        'base',
        'web',
        'nhan_su',
        'mail',
    ],

    'assets': {
        'web.assets_backend': [
            'cham_cong_tinh_luong/static/src/scss/theme_global.scss',
            'cham_cong_tinh_luong/static/src/scss/cham_cong_tinh_luong.scss',
            'cham_cong_tinh_luong/static/src/js/dashboard_chart_widget.js',
        ],
    },

    'data': [
        # 1. Security group phải load trước access rights
        'security/security.xml',

        # 2. Access rights dùng group ở security.xml
        'security/ir.model.access.csv',

        # 3. Record rule load sau access rights
        'security/rules.xml',

        # Mail template data
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',

        # 4. View chính
        'views/cham_cong_view.xml',
        'views/cau_hinh_luong_view.xml',
        'views/canh_bao_cham_cong_view.xml',
        'views/nhan_vien_extend_view.xml',

        # 5. Wizard
        'wizards/phan_tich_cham_cong_wizard_view.xml',
        'wizards/xuat_bang_luong_wizard_view.xml',
        'wizards/sinh_bang_luong_wizard_view.xml',
        'wizards/import_cham_cong_wizard_view.xml',
        'wizards/phieu_luong_preview_wizard_view.xml',

        # 6. Report
        'report/bang_luong_report.xml',

        # 7. View dùng report/action nên nạp sau khi report đã có XML ID
        'views/bang_luong_view.xml',
        'views/khen_thuong_ky_luat_view.xml',
        'views/dashboard_views.xml',

        # 8. Menu nên để cuối cùng
        'views/menu.xml',
    ],

    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
