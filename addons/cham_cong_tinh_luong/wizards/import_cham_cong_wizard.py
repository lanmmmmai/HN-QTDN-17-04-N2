import base64
import csv
import logging
from datetime import datetime
from io import BytesIO, StringIO
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from odoo import fields, models
from odoo.exceptions import ValidationError, AccessError

_logger = logging.getLogger(__name__)


class ImportChamCongWizard(models.TransientModel):
    _name = 'import_cham_cong_wizard'
    _description = 'Import chấm công'

    file_data = fields.Binary(required=True)
    file_name = fields.Char(required=True)
    ket_qua_import = fields.Text(readonly=True)

    def _parse_xlsx_rows(self, content):
        with ZipFile(BytesIO(content), 'r') as zf:
            shared_strings = []
            if 'xl/sharedStrings.xml' in zf.namelist():
                root = ET.fromstring(zf.read('xl/sharedStrings.xml'))
                ns = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for si in root.findall('a:si', ns):
                    text = ''.join(node.text or '' for node in si.iterfind('.//a:t', ns))
                    shared_strings.append(text)
            sheet = ET.fromstring(zf.read('xl/worksheets/sheet1.xml'))
            ns = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            rows = []
            for row in sheet.findall('.//a:sheetData/a:row', ns):
                values = []
                for cell in row.findall('a:c', ns):
                    cell_type = cell.attrib.get('t')
                    value_node = cell.find('a:v', ns)
                    if cell_type == 'inlineStr':
                        text_node = cell.find('a:is/a:t', ns)
                        values.append(text_node.text if text_node is not None else '')
                    elif cell_type == 's' and value_node is not None:
                        values.append(shared_strings[int(value_node.text)])
                    elif value_node is not None:
                        values.append(value_node.text)
                    else:
                        values.append('')
                rows.append(values)
            return rows

    def _parse_csv_rows(self, content):
        text = content.decode('utf-8-sig')
        reader = csv.reader(StringIO(text))
        return [row for row in reader]

    def action_import(self):
        self.ensure_one()
        if not (self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_nhan_su') or 
                self.env.user.has_group('cham_cong_tinh_luong.group_cham_cong_quan_tri')):
            raise AccessError('Bạn không có quyền import dữ liệu chấm công. Chỉ Nhân sự hoặc Quản trị mới được phép.')

        content = base64.b64decode(self.file_data)
        filename = (self.file_name or '').lower()
        rows = self._parse_xlsx_rows(content) if filename.endswith('.xlsx') else self._parse_csv_rows(content)
        if not rows:
            raise ValidationError('File import không có dữ liệu.')

        headers = [col.strip().lower() for col in rows[0]]
        required = ['ma_nhan_vien', 'ngay_cham_cong', 'gio_vao', 'gio_ra', 'trang_thai', 'ghi_chu']
        for item in required:
            if item not in headers:
                raise ValidationError('Thiếu cột bắt buộc: %s' % item)

        idx = {name: headers.index(name) for name in headers}
        total = success = error = 0
        messages = []
        ChamCong = self.env['cham_cong']
        NhanVien = self.env['nhan_vien']

        for row in rows[1:]:
            total += 1
            try:
                ma = row[idx['ma_nhan_vien']].strip() if len(row) > idx['ma_nhan_vien'] else ''
                ngay = row[idx['ngay_cham_cong']].strip() if len(row) > idx['ngay_cham_cong'] else ''
                gio_vao = row[idx['gio_vao']].strip() if len(row) > idx['gio_vao'] else ''
                gio_ra = row[idx['gio_ra']].strip() if len(row) > idx['gio_ra'] else ''
                trang_thai = row[idx['trang_thai']].strip() if len(row) > idx['trang_thai'] else 'di_lam'
                ghi_chu = row[idx['ghi_chu']].strip() if len(row) > idx['ghi_chu'] else ''

                employee = NhanVien.search([('ma_dinh_danh', '=', ma)], limit=1)
                if not employee:
                    name_candidate = row[idx['ma_nhan_vien']].strip() if ma else ''
                    if name_candidate:
                        employee = NhanVien.search(['|', ('ho_va_ten', '=', name_candidate), ('email', '=', name_candidate)], limit=1)
                if not employee:
                    raise ValidationError('Không tìm thấy nhân viên với mã %s' % ma)

                date_value = datetime.strptime(ngay, '%Y-%m-%d').date() if ngay else fields.Date.context_today(self)
                if gio_vao:
                    gio_vao = datetime.fromisoformat(gio_vao)
                else:
                    gio_vao = False
                if gio_ra:
                    gio_ra = datetime.fromisoformat(gio_ra)
                else:
                    gio_ra = False
                if gio_vao and gio_ra and gio_ra < gio_vao:
                    raise ValidationError('Giờ ra nhỏ hơn giờ vào.')

                if ChamCong.search_count([('nhan_vien_id', '=', employee.id), ('ngay_cham_cong', '=', date_value)]):
                    messages.append('Dòng %s: bỏ qua vì đã tồn tại chấm công ngày %s.' % (total + 1, ngay))
                    continue

                ChamCong.create({
                    'nhan_vien_id': employee.id,
                    'ngay_cham_cong': date_value,
                    'gio_vao': gio_vao,
                    'gio_ra': gio_ra,
                    'trang_thai': trang_thai,
                    'ghi_chu': ghi_chu,
                })
                success += 1
            except Exception as exc:
                error += 1
                messages.append('Dòng %s: %s' % (total + 1, exc))

        self.ket_qua_import = 'Tổng số dòng: %s\nThành công: %s\nLỗi: %s\n%s' % (total, success, error, '\n'.join(messages))
        _logger.info('Import chấm công hoàn tất: tổng %s, thành công %s, lỗi %s.', total, success, error)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'import_cham_cong_wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
