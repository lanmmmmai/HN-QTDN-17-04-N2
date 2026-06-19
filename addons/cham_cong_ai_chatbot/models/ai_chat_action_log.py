# -*- coding: utf-8 -*-
import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AiChatActionLog(models.Model):
    _name = 'ai.chat.action.log'
    _description = 'Log hành động AI Chatbot'
    _order = 'create_date desc'

    name = fields.Char(string='Tên', compute='_compute_name', store=True)
    session_id = fields.Many2one('ai.chat.session', string='Phiên chat', ondelete='cascade')
    message_id = fields.Many2one('ai.chat.message', string='Tin nhắn')
    user_id = fields.Many2one('res.users', string='Người dùng', default=lambda self: self.env.user)
    employee_id = fields.Many2one('nhan_vien', string='Nhân viên')
    action_type = fields.Selection(
        [
            ('create_attendance', 'Tạo chấm công'),
            ('update_attendance', 'Sửa chấm công'),
            ('create_leave', 'Tạo nghỉ phép'),
            ('get_salary_info', 'Tra cứu lương'),
            ('get_attendance_summary', 'Tra cứu chấm công'),
            ('print_payroll', 'In bảng lương'),
            ('other', 'Khác'),
        ],
        string='Loại hành động', default='other',
    )
    original_text = fields.Text(string='Câu hỏi gốc')
    extracted_data = fields.Text(string='Dữ liệu trích xuất (JSON)')
    summary = fields.Text(string='Tóm tắt xác nhận')
    state = fields.Selection(
        [
            ('draft', 'Nháp'),
            ('pending_confirm', 'Chờ xác nhận'),
            ('confirmed', 'Đã xác nhận'),
            ('done', 'Đã thực hiện'),
            ('cancelled', 'Đã hủy'),
            ('error', 'Lỗi'),
        ],
        string='Trạng thái', default='draft',
    )
    target_model = fields.Char(string='Model đích')
    target_record_id = fields.Integer(string='ID bản ghi đích')
    error_message = fields.Text(string='Lỗi')
    confirmed_at = fields.Datetime(string='Thời điểm xác nhận')
    done_at = fields.Datetime(string='Thời điểm thực hiện')
    intent = fields.Char(string='Ý định')
    function_name = fields.Char(string='Hàm AI gọi')
    function_output = fields.Text(string='Dữ liệu phản hồi (Output)')

    @api.depends('action_type', 'create_date')
    def _compute_name(self):
        type_labels = dict(self._fields['action_type'].selection)
        for rec in self:
            label = type_labels.get(rec.action_type, 'Hành động')
            date_str = ''
            if rec.create_date:
                date_str = fields.Datetime.to_string(rec.create_date)
            rec.name = ('%s - %s' % (label, date_str)).strip(' -')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_data(self):
        self.ensure_one()
        if not self.extracted_data:
            return {}
        try:
            return json.loads(self.extracted_data)
        except (ValueError, TypeError):
            return {}

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------
    def action_confirm(self):
        for rec in self:
            if rec.state not in ('pending_confirm', 'draft'):
                continue
            rec.write({
                'state': 'confirmed',
                'confirmed_at': fields.Datetime.now(),
            })
            _logger.info('AI_CHATBOT_ACTION: confirmed action_id=%s type=%s', rec.id, rec.action_type)
            try:
                rec._execute_action()
            except Exception as exc:  # noqa: BLE001
                _logger.exception('AI_CHATBOT_ACTION: error action_id=%s', rec.id)
                rec.write({'state': 'error', 'error_message': str(exc)})
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    def _execute_action(self):
        self.ensure_one()
        data = self._get_data()
        result = None
        if self.action_type == 'create_attendance':
            result = self._do_create_attendance(data)
        elif self.action_type == 'update_attendance':
            result = self._do_update_attendance(data)
        elif self.action_type == 'create_leave':
            result = self._do_create_leave(data)
        elif self.action_type == 'print_payroll':
            result = self._do_print_payroll(data)
        else:
            self.write({'state': 'done', 'done_at': fields.Datetime.now()})
        _logger.info('AI_CHATBOT_ACTION: done action_id=%s type=%s target=%s/%s',
                     self.id, self.action_type, self.target_model, self.target_record_id)
        return result

    # ------------------------------------------------------------------
    # Concrete actions
    # ------------------------------------------------------------------
    def _build_datetime(self, date_val, time_str):
        """Combine a date and an "HH:MM" string into a naive datetime."""
        if not date_val or not time_str:
            return False
        return self.env['cham_cong'].sudo()._local_datetime_to_utc_naive(date_val, time_str)

    def _do_create_attendance(self, data):
        self.ensure_one()
        employee = self.employee_id or self.env['nhan_vien'].browse(data.get('employee_id'))
        if not employee:
            raise UserError('Không xác định được nhân viên để tạo chấm công.')
        date_val = data.get('date')
        vals = {
            'nhan_vien_id': employee.id,
            'ngay_cham_cong': date_val,
            'loai_cong': 'cong_thuong',
            'trang_thai': 'di_lam',
            'state': 'nhap',
        }
        gio_vao = self._build_datetime(date_val, data.get('check_in'))
        gio_ra = self._build_datetime(date_val, data.get('check_out'))
        if gio_vao:
            vals['gio_vao'] = gio_vao
        if gio_ra:
            vals['gio_ra'] = gio_ra
        if data.get('reason'):
            vals['ghi_chu'] = data.get('reason')
        record = self.env['cham_cong'].sudo().create(vals)
        self.write({
            'target_model': 'cham_cong',
            'target_record_id': record.id,
            'function_output': 'Đã tạo bản ghi chấm công ID: %s cho %s ngày %s' % (record.id, employee.ho_va_ten, date_val),
            'state': 'done',
            'done_at': fields.Datetime.now(),
        })
        return record

    def _do_update_attendance(self, data):
        self.ensure_one()
        record_id = data.get('target_record_id') or self.target_record_id
        if not record_id:
            raise UserError('Không tìm thấy bản ghi chấm công để cập nhật.')
        record = self.env['cham_cong'].sudo().browse(record_id)
        if not record.exists():
            raise UserError('Bản ghi chấm công không tồn tại.')
        vals = {}
        date_val = record.ngay_cham_cong
        if data.get('check_in'):
            gio_vao = self._build_datetime(date_val, data.get('check_in'))
            if gio_vao:
                vals['gio_vao'] = gio_vao
        if data.get('check_out'):
            gio_ra = self._build_datetime(date_val, data.get('check_out'))
            if gio_ra:
                vals['gio_ra'] = gio_ra
        if data.get('reason'):
            vals['ghi_chu'] = data.get('reason')
        if vals:
            record.write(vals)
        self.write({
            'target_model': 'cham_cong',
            'target_record_id': record.id,
            'function_output': 'Đã cập nhật bản ghi chấm công ID: %s cho %s' % (record.id, record.nhan_vien_id.ho_va_ten),
            'state': 'done',
            'done_at': fields.Datetime.now(),
        })
        return record

    def _do_create_leave(self, data):
        self.ensure_one()
        # The leave/nghi phep model may not exist in this deployment.
        leave_model = None
        for candidate in ('nghi_phep', 'don_xin_nghi', 'hr.leave'):
            if candidate in self.env:
                leave_model = candidate
                break
        if not leave_model:
            self.write({
                'state': 'done',
                'done_at': fields.Datetime.now(),
                'function_output': 'Đã ghi nhận yêu cầu nghỉ phép (chưa cài module nghỉ phép).',
                'error_message': 'Module nghỉ phép chưa được cài đặt - đã ghi nhận yêu cầu.',
            })
            return False
        employee = self.employee_id
        data = self._get_data()
        vals = {}
        Model = self.env[leave_model].sudo()
        if 'nhan_vien_id' in Model._fields and employee:
            vals['nhan_vien_id'] = employee.id
        if 'date_from' in Model._fields and data.get('date_from'):
            vals['date_from'] = data['date_from']
        if 'date_to' in Model._fields and data.get('date_to'):
            vals['date_to'] = data['date_to']
        if 'ngay_bat_dau' in Model._fields and data.get('date_from'):
            vals['ngay_bat_dau'] = data['date_from']
        if 'ngay_ket_thuc' in Model._fields and data.get('date_to'):
            vals['ngay_ket_thuc'] = data['date_to']
        if 'name' in Model._fields and data.get('reason'):
            vals['name'] = data['reason']
        if 'ghi_chu' in Model._fields and data.get('reason'):
            vals['ghi_chu'] = data['reason']
        record = False
        try:
            record = Model.create(vals)
            self.write({
                'target_model': leave_model,
                'target_record_id': record.id,
                'function_output': 'Đã tạo yêu cầu nghỉ phép ID: %s cho %s' % (record.id, employee.ho_va_ten),
                'state': 'done',
                'done_at': fields.Datetime.now(),
            })
        except Exception as exc:  # noqa: BLE001
            self.write({
                'state': 'done',
                'done_at': fields.Datetime.now(),
                'function_output': 'Lỗi khi tạo bản ghi nghỉ phép: %s' % exc,
                'error_message': 'Không thể tạo bản ghi nghỉ phép tự động: %s' % exc,
            })
        return record

    def _do_print_payroll(self, data):
        self.ensure_one()
        record_id = data.get('target_record_id') or self.target_record_id
        self.write({
            'target_model': 'bang_luong',
            'target_record_id': record_id or 0,
            'function_output': 'Đã xuất phiếu lương PDF cho bảng lương ID: %s' % record_id,
            'state': 'done',
            'done_at': fields.Datetime.now(),
        })
        if record_id:
            return self.env.ref('cham_cong_tinh_luong.action_report_bang_luong').report_action(record_id)
        return False
