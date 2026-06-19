# -*- coding: utf-8 -*-

from odoo import api, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _ai_chatbot_group_refs(self):
        return {
            'employee': self.env.ref(
                'cham_cong_ai_chatbot.group_ai_chatbot_employee_user',
                raise_if_not_found=False,
            ),
            'manager': self.env.ref(
                'cham_cong_ai_chatbot.group_ai_chatbot_manager',
                raise_if_not_found=False,
            ),
            'admin': self.env.ref(
                'cham_cong_ai_chatbot.group_ai_chatbot_admin',
                raise_if_not_found=False,
            ),
            'payroll_hr': self.env.ref(
                'cham_cong_tinh_luong.group_cham_cong_nhan_su',
                raise_if_not_found=False,
            ),
            'payroll_admin': self.env.ref(
                'cham_cong_tinh_luong.group_cham_cong_quan_tri',
                raise_if_not_found=False,
            ),
            'base_admin': self.env.ref('base.user_admin', raise_if_not_found=False),
            'system_group': self.env.ref('base.group_system', raise_if_not_found=False),
        }

    def _sync_ai_chatbot_groups(self):
        if self.env.context.get('skip_ai_chatbot_sync'):
            return

        refs = self._ai_chatbot_group_refs()
        employee_group = refs['employee']
        if not employee_group:
            return

        manager_groups = {
            g.id for g in (
                refs['manager'],
                refs['admin'],
                refs['payroll_hr'],
                refs['payroll_admin'],
                refs['base_admin'],
                refs['system_group'],
            ) if g
        }
        all_users = self.sudo().search([('share', '=', False)])
        manager_user_ids = [user.id for user in all_users if manager_groups.intersection(user.groups_id.ids)]
        employee_user_ids = [user.id for user in all_users if user.id not in manager_user_ids]
        cr = self.env.cr
        if manager_user_ids:
            cr.execute(
                "DELETE FROM res_groups_users_rel WHERE gid = %s AND uid = ANY(%s)",
                (employee_group.id, manager_user_ids),
            )
        if employee_user_ids:
            cr.execute(
                """
                INSERT INTO res_groups_users_rel (gid, uid)
                SELECT %s, uid
                FROM unnest(%s::int[]) AS uid
                ON CONFLICT DO NOTHING
                """,
                (employee_group.id, employee_user_ids),
            )

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        users._sync_ai_chatbot_groups()
        return users

    def write(self, vals):
        res = super().write(vals)
        self._sync_ai_chatbot_groups()
        return res

    def _register_hook(self):
        res = super()._register_hook()
        self._sync_ai_chatbot_groups()
        return res
