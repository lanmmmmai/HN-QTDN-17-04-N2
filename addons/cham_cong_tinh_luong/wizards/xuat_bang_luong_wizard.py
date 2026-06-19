# -*- coding: utf-8 -*-

import base64
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from odoo import fields, models


class XuatBangLuongWizard(models.TransientModel):
    _name = 'xuat_bang_luong_wizard'
    _description = 'Xuất bảng lương Excel'

    thang = fields.Selection([(str(i), 'Tháng %s' % i) for i in range(1, 13)], required=True, default=lambda self: str(fields.Date.context_today(self).month))
    nam = fields.Integer(required=True, default=lambda self: fields.Date.context_today(self).year)
    file_data = fields.Binary(readonly=True)
    file_name = fields.Char(readonly=True)

    def _build_xlsx(self, rows, headers):
        def c_ref(col, row):
            letters = ''
            col += 1
            while col:
                col, rem = divmod(col - 1, 26)
                letters = chr(65 + rem) + letters
            return '%s%s' % (letters, row)

        def xml_escape(value):
            return ('' if value is None else str(value)).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        sheet_rows = []
        header_cells = ''.join('<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (c_ref(i, 1), xml_escape(h)) for i, h in enumerate(headers))
        sheet_rows.append('<row r="1">%s</row>' % header_cells)
        for r_index, row in enumerate(rows, start=2):
            cells = []
            for c_index, value in enumerate(row):
                if isinstance(value, (int, float)):
                    cells.append('<c r="%s"><v>%s</v></c>' % (c_ref(c_index, r_index), value))
                else:
                    cells.append('<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (c_ref(c_index, r_index), xml_escape(value)))
            sheet_rows.append('<row r="%s">%s</row>' % (r_index, ''.join(cells)))
        sheet_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' \
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' \
            '<sheetData>%s</sheetData></worksheet>' % ''.join(sheet_rows)

        workbook_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' \
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ' \
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' \
            '<sheets><sheet name="Bang Luong" sheetId="1" r:id="rId1"/></sheets></workbook>'

        workbook_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' \
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' \
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>' \
            '</Relationships>'

        root_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' \
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' \
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>' \
            '</Relationships>'

        content_types = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' \
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' \
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' \
            '<Default Extension="xml" ContentType="application/xml"/>' \
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' \
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' \
            '</Types>'

        bio = BytesIO()
        with ZipFile(bio, 'w', ZIP_DEFLATED) as zf:
            zf.writestr('[Content_Types].xml', content_types)
            zf.writestr('_rels/.rels', root_rels)
            zf.writestr('xl/workbook.xml', workbook_xml)
            zf.writestr('xl/_rels/workbook.xml.rels', workbook_rels)
            zf.writestr('xl/worksheets/sheet1.xml', sheet_xml)
        return bio.getvalue()

    def action_xuat_excel(self):
        self.ensure_one()
        payslips = self.env['bang_luong'].search([
            ('thang', '=', self.thang),
            ('nam', '=', self.nam),
        ], order='nhan_vien_id')
        headers = [
            'STT', 'Mã nhân viên', 'Họ tên nhân viên', 'Tháng', 'Năm', 'Số ngày đi làm', 'Tổng giờ làm',
            'Tổng giờ tăng ca', 'Lương cơ bản', 'Lương theo ngày công', 'Tổng phụ cấp',
            'Khen thưởng', 'Kỷ luật', 'Tổng khấu trừ', 'Tổng lương thực nhận', 'Trạng thái bảng lương',
        ]
        rows = []
        for index, line in enumerate(payslips, start=1):
            rows.append([
                index,
                line.ma_nhan_vien or '',
                line.nhan_vien_id.ho_va_ten or '',
                line.thang,
                line.nam,
                line.so_ngay_di_lam,
                line.tong_gio_lam,
                line.tong_gio_tang_ca,
                line.luong_co_ban,
                line.luong_theo_cong,
                line.tong_phu_cap,
                line.tong_khen_thuong,
                line.tong_ky_luat,
                line.tong_khau_tru,
                line.tong_luong,
                line.state,
            ])
        filename = 'Bang_luong_thang_%s_%s.xlsx' % (self.thang, self.nam)
        self.write({
            'file_name': filename,
            'file_data': base64.b64encode(self._build_xlsx(rows, headers)),
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/?model=xuat_bang_luong_wizard&id=%s&field=file_data&filename_field=file_name&download=true' % self.id,
            'target': 'self',
        }
