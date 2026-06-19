# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class TaoTaiKhoanNhanVienWizard(models.TransientModel):
    _name = 'tao_tai_khoan_nhan_vien_wizard'
    _description = 'Wizard tạo tài khoản người dùng cho nhân viên'

    nhan_vien_id = fields.Many2one(
        'nhan_vien',
        string='Nhân viên',
        required=True,
        readonly=True,
    )
    name = fields.Char(string='Tên người dùng', required=True)
    login = fields.Char(string='Email / Login', required=True)
    password = fields.Char(string='Mật khẩu', required=True)
    confirm_password = fields.Char(string='Nhập lại mật khẩu', required=True)

    @api.constrains('password', 'confirm_password')
    def _check_password_match(self):
        for rec in self:
            if rec.password and rec.confirm_password and rec.password != rec.confirm_password:
                raise ValidationError("Mật khẩu và xác nhận mật khẩu không khớp nhau.")

    def action_tao_tai_khoan(self):
        self.ensure_one()

        if not (
            self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_nhan_su')
            or self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_quan_tri')
        ):
            raise UserError('Bạn không có quyền tạo tài khoản hệ thống.')

        if self.password != self.confirm_password:
            raise UserError("Mật khẩu và xác nhận mật khẩu không khớp nhau.")

        if len(self.password) < 4:
            raise UserError("Mật khẩu phải có ít nhất 4 ký tự.")

        existing_user = self.env['res.users'].sudo().search(
            [('login', '=', self.login)], limit=1
        )

        if existing_user:
            # Email đã có user — kiểm tra tài khoản này chưa thuộc nhân viên khác
            other_employee = self.env['nhan_vien'].sudo().search(
                [('user_id', '=', existing_user.id), ('id', '!=', self.nhan_vien_id.id)],
                limit=1,
            )
            if other_employee:
                raise UserError(
                    'Email "%s" đã được liên kết với nhân viên khác (%s). '
                    'Vui lòng dùng email khác.' % (self.login, other_employee.ho_va_ten)
                )
            self.nhan_vien_id.sudo().write({'user_id': existing_user.id})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Đã gán tài khoản',
                    'message': 'Email "%s" đã có tài khoản. Đã gán tài khoản đó vào nhân viên.' % self.login,
                    'type': 'warning',
                    'sticky': False,
                },
            }

        group_user = self.env.ref('base.group_user')
        group_self_service = self.env.ref(
            'cham_cong_tinh_luong.group_cham_cong_self_service',
            raise_if_not_found=False,
        )

        groups = [group_user.id]
        if group_self_service:
            groups.append(group_self_service.id)

        try:
            with self.env.cr.savepoint():
                user = self.env['res.users'].sudo().create({
                    'name': self.name,
                    'login': self.login,
                    'email': self.login,
                    'password': self.password,
                    'groups_id': [(6, 0, groups)],
                })
        except Exception:
            raise UserError(
                'Email "%s" đã tồn tại trong hệ thống. Vui lòng dùng email khác.' % self.login
            )

        self.nhan_vien_id.sudo().write({'user_id': user.id})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': 'Đã tạo tài khoản "%s" cho nhân viên %s.' % (
                    self.login, self.nhan_vien_id.ho_va_ten
                ),
                'type': 'success',
                'sticky': False,
            },
        }
