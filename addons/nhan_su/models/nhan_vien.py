import unicodedata

from odoo import models, fields, api
from datetime import date

from odoo.exceptions import ValidationError, UserError


def _normalize_vi(text):
    """Chuyển chuỗi có dấu tiếng Việt sang không dấu, viết thường, không khoảng trắng."""
    if not text:
        return ''
    nfkd = unicodedata.normalize('NFKD', text)
    ascii_str = nfkd.encode('ascii', 'ignore').decode('ascii')
    return ascii_str.lower().replace(' ', '')

class NhanVien(models.Model):
    _name = 'nhan_vien'
    _description = 'Bảng chứa thông tin nhân viên'
    _rec_name = 'ho_va_ten'
    _order = 'ten asc, tuoi desc'

    ma_dinh_danh = fields.Char("Mã định danh", required=True)

    ho_ten_dem = fields.Char("Họ tên đệm", required=True)
    ten = fields.Char("Tên", required=True)
    ho_va_ten = fields.Char("Họ và tên", compute="_compute_ho_va_ten", store=True)
    
    ngay_sinh = fields.Date("Ngày sinh")
    que_quan = fields.Char("Quê quán")
    email = fields.Char("Email")
    user_id = fields.Many2one(
        "res.users",
        string="Tài khoản người dùng",
        ondelete="set null",
    )
    so_dien_thoai = fields.Char("Số điện thoại")
    lich_su_cong_tac_ids = fields.One2many(
        "lich_su_cong_tac", 
        inverse_name="nhan_vien_id", 
        string = "Danh sách lịch sử công tác")
    tuoi = fields.Integer("Tuổi", compute="_compute_tuoi", store=True)
    anh = fields.Binary("Ảnh")
    danh_sach_chung_chi_bang_cap_ids = fields.One2many(
        "danh_sach_chung_chi_bang_cap", 
        inverse_name="nhan_vien_id", 
        string = "Danh sách chứng chỉ bằng cấp")
    so_nguoi_bang_tuoi = fields.Integer("Số người bằng tuổi",
                                        compute="_compute_so_nguoi_bang_tuoi",
                                        store=True
                                        )

    # Phòng ban và chức vụ hiện tại — lấy từ lịch sử công tác mới nhất
    phong_ban_id = fields.Many2one(
        'don_vi',
        string='Phòng ban / Đơn vị',
        compute='_compute_phong_ban_chuc_vu',
        store=True,
    )
    chuc_vu_id = fields.Many2one(
        'chuc_vu',
        string='Chức vụ',
        compute='_compute_phong_ban_chuc_vu',
        store=True,
    )

    @api.depends('lich_su_cong_tac_ids', 'lich_su_cong_tac_ids.don_vi_id', 'lich_su_cong_tac_ids.chuc_vu_id')
    def _compute_phong_ban_chuc_vu(self):
        for record in self:
            if record.lich_su_cong_tac_ids:
                latest = record.lich_su_cong_tac_ids.sorted('id', reverse=True)[0]
                record.phong_ban_id = latest.don_vi_id
                record.chuc_vu_id = latest.chuc_vu_id
            else:
                record.phong_ban_id = False
                record.chuc_vu_id = False

    @api.depends("tuoi")
    def _compute_so_nguoi_bang_tuoi(self):
        for record in self:
            if record.tuoi:
                records = self.env['nhan_vien'].search(
                    [
                        ('tuoi', '=', record.tuoi),
                        ('ma_dinh_danh', '!=', record.ma_dinh_danh)
                    ]
                )
                record.so_nguoi_bang_tuoi = len(records)
            else:
                record.so_nguoi_bang_tuoi = 0
    _sql_constraints = [
        ('ma_dinh_danh_unique', 'unique(ma_dinh_danh)', 'Mã định danh phải là duy nhất'),
        ('user_id_unique', 'unique(user_id)', 'Mỗi tài khoản người dùng chỉ được liên kết với một nhân viên'),
    ]

    @api.depends("ho_ten_dem", "ten")
    def _compute_ho_va_ten(self):
        for record in self:
            if record.ho_ten_dem and record.ten:
                record.ho_va_ten = record.ho_ten_dem + ' ' + record.ten
    
    
    
                
    @api.onchange("ten", "ho_ten_dem")
    def _default_ma_dinh_danh(self):
        for record in self:
            if record.ho_ten_dem and record.ten:
                chu_cai_dau = ''.join([tu[0][0] for tu in record.ho_ten_dem.lower().split()])
                record.ma_dinh_danh = record.ten.lower() + chu_cai_dau
    
    @api.depends("ngay_sinh")
    def _compute_tuoi(self):
        for record in self:
            if record.ngay_sinh:
                year_now = date.today().year
                record.tuoi = year_now - record.ngay_sinh.year

    @api.constrains('tuoi')
    def _check_tuoi(self):
        for record in self:
            if record.tuoi < 18:
                raise ValidationError("Tuổi không được bé hơn 18")

    def action_mo_wizard_tao_tai_khoan(self):
        self.ensure_one()
        if not self.email:
            raise UserError(
                "Nhân viên '%s' chưa có email. Vui lòng nhập email trước khi tạo tài khoản."
                % (self.ho_va_ten or self.ma_dinh_danh)
            )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tạo tài khoản người dùng',
            'res_model': 'tao_tai_khoan_nhan_vien_wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_nhan_vien_id': self.id,
                'default_name': self.ho_va_ten or '',
                'default_login': self.email or '',
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.user_id:
                continue
            ten_norm = _normalize_vi(record.ten)
            hodem_norm = _normalize_vi(record.ho_ten_dem)
            if not ten_norm or not hodem_norm:
                continue
            login = f"{ten_norm}.{hodem_norm}@cty.com"
            existing = self.env['res.users'].sudo().search([('login', '=', login)], limit=1)
            if existing:
                already_linked = self.sudo().search(
                    [('user_id', '=', existing.id), ('id', '!=', record.id)], limit=1
                )
                if not already_linked:
                    record.sudo().write({'user_id': existing.id})
        return records
