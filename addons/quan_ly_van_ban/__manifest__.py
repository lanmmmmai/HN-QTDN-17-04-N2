# -*- coding: utf-8 -*-
{
    'name': 'Quản lý văn bản',
    'summary': 'Quản lý văn bản đến, văn bản đi và liên kết với nhân sự',
    'description': '''
Module Quản lý văn bản liên kết với module Quản lý nhân sự.
Cho phép chọn đơn vị xử lý, nhân viên xử lý, đơn vị soạn thảo và người ký từ dữ liệu nhân sự.
    ''',
    'author': 'Business Internship',
    'category': 'Document Management',
    'version': '15.0.1.0.0',
    'depends': ['base', 'nhan_su'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/loai_van_ban_views.xml',
        'views/van_ban_den_views.xml',
        'views/van_ban_di_views.xml',
        'views/dashboard_van_ban_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
