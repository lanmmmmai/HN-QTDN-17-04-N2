# -*- coding: utf-8 -*-

from datetime import date, datetime
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestPayroll(TransactionCase):

    def setUp(self):
        super(TestPayroll, self).setUp()
        
        # Create department
        self.department = self.env['don_vi'].create({
            'ten_don_vi': 'Phòng Công nghệ',
            'ma_don_vi': 'IT_DEPT',
        })
        
        # Create job position
        self.job = self.env['chuc_vu'].create({
            'ten_chuc_vu': 'Lập trình viên',
            'ma_chuc_vu': 'DEV',
        })
        
        # Create employee
        self.employee = self.env['nhan_vien'].create({
            'ho_ten_dem': 'Nguyễn Văn',
            'ten': 'A',
            'ma_dinh_danh': 'TEST_NV_001',
            'email': 'nva@company.com',
        })
        
        # Create Lich su cong tac
        self.env['lich_su_cong_tac'].create({
            'nhan_vien_id': self.employee.id,
            'don_vi_id': self.department.id,
            'chuc_vu_id': self.job.id,
            'ngay_bat_dau': date(2026, 6, 1),
        })

        # Create active salary configuration
        self.salary_config = self.env['cau_hinh_luong'].create({
            'nhan_vien_id': self.employee.id,
            'luong_co_ban': 10000000.0,
            'so_ngay_cong_chuan': 26.0,
            'so_gio_cong_chuan': 8.0,
            'phu_cap_an_trua': 500000.0,
            'phu_cap_xang_xe': 300000.0,
            'ty_le_bao_hiem': 10.5,
            'thue_tncn': 100000.0,
            'khau_tru_khac': 50000.0,
            'ngay_bat_dau': date(2026, 6, 1),
            'trang_thai': 'dang_ap_dung',
        })
        
        # Grant payroll manager group to the test user to allow calling manager action methods
        group_admin = self.env.ref('cham_cong_tinh_luong.group_cham_cong_quan_tri')
        self.env.user.write({'groups_id': [(4, group_admin.id)]})

    def test_01_attendance_shift_overtime(self):
        """Test that overtime is calculated correctly according to work shifts (Task 4)"""
        # Ca hành chính (Office shift): Standard hours = 8.0
        att_hc = self.env['cham_cong'].create({
            'nhan_vien_id': self.employee.id,
            'ngay_cham_cong': date(2026, 6, 1),
            'ca_lam_viec': 'hanh_chinh',
            'gio_vao': datetime(2026, 6, 1, 1, 0, 0),  # UTC (~8h sáng local)
            'gio_ra': datetime(2026, 6, 1, 11, 0, 0),  # UTC (~18h chiều local) -> 10 hours worked
            'trang_thai': 'di_lam',
        })
        # 10 hours - 8 hours standard = 2 hours overtime
        self.assertEqual(att_hc.so_gio_lam, 10.0)
        self.assertEqual(att_hc.so_gio_tang_ca, 2.0)
        self.assertEqual(att_hc.so_ngay_cong, 1.0)

        # Ca tối (Night/Evening shift): Standard hours = 4.0
        att_toi = self.env['cham_cong'].create({
            'nhan_vien_id': self.employee.id,
            'ngay_cham_cong': date(2026, 6, 2),
            'ca_lam_viec': 'toi',
            'gio_vao': datetime(2026, 6, 2, 11, 0, 0),  # UTC (~18h tối local)
            'gio_ra': datetime(2026, 6, 2, 16, 0, 0),  # UTC (~23h tối local) -> 5 hours worked
            'trang_thai': 'di_lam',
        })
        # 5 hours - 4 hours standard = 1 hour overtime
        self.assertEqual(att_toi.so_gio_lam, 5.0)
        self.assertEqual(att_toi.so_gio_tang_ca, 1.0)
        self.assertEqual(att_toi.so_ngay_cong, 1.0)

    def test_02_payroll_calculations(self):
        """Test gross salary and take-home pay calculations, including overtime (Task 3)"""
        # Create standard confirmed attendances
        # 1 day of ca hành chính (8 hours standard, 2 hours overtime)
        att1 = self.env['cham_cong'].create({
            'nhan_vien_id': self.employee.id,
            'ngay_cham_cong': date(2026, 6, 1),
            'ca_lam_viec': 'hanh_chinh',
            'gio_vao': datetime(2026, 6, 1, 1, 0, 0),
            'gio_ra': datetime(2026, 6, 1, 11, 0, 0),
            'trang_thai': 'di_lam',
            'state': 'xac_nhan',
        })
        
        # 1 day of ca tối (4 hours standard, 1 hour overtime)
        att2 = self.env['cham_cong'].create({
            'nhan_vien_id': self.employee.id,
            'ngay_cham_cong': date(2026, 6, 2),
            'ca_lam_viec': 'toi',
            'gio_vao': datetime(2026, 6, 2, 11, 0, 0),
            'gio_ra': datetime(2026, 6, 2, 16, 0, 0),
            'trang_thai': 'di_lam',
            'state': 'xac_nhan',
        })

        # Total days: 2.0. Total overtime hours: 3.0.
        
        # Create reward and discipline records
        self.env['khen_thuong_ky_luat'].create({
            'nhan_vien_id': self.employee.id,
            'ngay_ap_dung': date(2026, 6, 15),
            'so_tien': 200000.0,
            'loai_quyet_dinh': 'khen_thuong',
        })
        self.env['khen_thuong_ky_luat'].create({
            'nhan_vien_id': self.employee.id,
            'ngay_ap_dung': date(2026, 6, 20),
            'so_tien': 50000.0,
            'loai_quyet_dinh': 'ky_luat',
        })

        # Generate salary sheet
        salary_sheet = self.env['bang_luong'].create({
            'nhan_vien_id': self.employee.id,
            'thang': '6',
            'nam': 2026,
            'he_so_tang_ca': 1.5,
        })
        
        # Trigger compute
        salary_sheet._compute_bang_luong()

        # luong_co_ban = 10,000,000
        # standard_days = 26
        # so_ngay_di_lam = 2.0
        # luong_theo_cong = 10,000,000 / 26 * 2 = 769,230.77
        self.assertAlmostEqual(salary_sheet.luong_theo_cong, 769230.77, places=2)
        
        # don_gia_gio = 10,000,000 / 26 / 8 = 48076.92
        # he_so_tang_ca = 1.5
        # tong_gio_tang_ca = 3.0
        # tien_tang_ca = 48076.92 * 1.5 * 3 = 216346.14
        self.assertAlmostEqual(salary_sheet.don_gia_gio, 48076.92, places=2)
        self.assertAlmostEqual(salary_sheet.tien_tang_ca, 216346.14, places=2)

        # tong_phu_cap = 500,000 + 300,000 = 800,000
        self.assertEqual(salary_sheet.tong_phu_cap, 800000.0)

        # tong_khen_thuong = 200,000
        self.assertEqual(salary_sheet.tong_khen_thuong, 200000.0)
        
        # tong_ky_luat = 50,000
        self.assertEqual(salary_sheet.tong_ky_luat, 50000.0)

        # tong_luong (Gross Salary) = luong_theo_cong + tong_phu_cap + tien_tang_ca + tong_khen_thuong
        # = 769230.77 + 800000 + 216346.14 + 200000 = 1985576.91
        self.assertAlmostEqual(salary_sheet.tong_luong, 1985576.91, places=2)

        # tien_bao_hiem = 10,000,000 * 10.5% = 1,050,000
        # thue_tncn = 100,000
        # khau_tru_khac = 50,000
        # tong_khau_tru = 1,200,000
        self.assertEqual(salary_sheet.tien_bao_hiem, 1050000.0)
        self.assertEqual(salary_sheet.tong_khau_tru, 1200000.0)

        # thuc_linh (Net Salary) = tong_luong - tong_khau_tru - tong_ky_luat
        # = 1985576.91 - 1200000 - 50000 = 735576.91
        self.assertAlmostEqual(salary_sheet.thuc_linh, 735576.91, places=2)

    def test_03_payroll_email_notification(self):
        """Test sending payroll slips via email automatically on payment confirmation"""
        self.assertTrue(self.employee.email)
        
        salary_sheet = self.env['bang_luong'].create({
            'nhan_vien_id': self.employee.id,
            'thang': '6',
            'nam': 2026,
            'state': 'da_tinh',
        })
        
        salary_sheet.action_xac_nhan()
        self.assertEqual(salary_sheet.state, 'xac_nhan')
        
        template = self.env.ref('cham_cong_tinh_luong.mail_template_phieu_luong')
        template.write({'auto_delete': False})

        mail_count_before = self.env['mail.mail'].search_count([])
        salary_sheet.action_da_thanh_toan()
        self.assertEqual(salary_sheet.state, 'da_thanh_toan')
        
        mail_count_after = self.env['mail.mail'].search_count([])
        self.assertEqual(mail_count_after, mail_count_before + 1)
        
        mail = self.env['mail.mail'].search([], order='id desc', limit=1)
        self.assertEqual(mail.email_to, self.employee.email)
        self.assertIn('Phiếu lương', mail.subject)

    def test_04_cron_jobs(self):
        """Test scheduled cron jobs for automatic attendance warnings and draft payroll generation"""
        # Create standard confirmed attendance
        self.env['cham_cong'].create({
            'nhan_vien_id': self.employee.id,
            'ngay_cham_cong': date(2026, 6, 1),
            'ca_lam_viec': 'hanh_chinh',
            'gio_vao': datetime(2026, 6, 1, 1, 0, 0),
            'gio_ra': datetime(2026, 6, 1, 11, 0, 0),
            'trang_thai': 'di_muon', # Vi phạm đi muộn để phát sinh cảnh báo
            'ly_do_di_muon': 'Đường đông kẹt xe',
            'state': 'xac_nhan',
        })
        
        # 1. Test cron_auto_analyze_attendance
        warn_count_before = self.env['canh_bao_cham_cong'].search_count([])
        self.env['canh_bao_cham_cong'].cron_auto_analyze_attendance()
        warn_count_after = self.env['canh_bao_cham_cong'].search_count([])
        self.assertTrue(warn_count_after > warn_count_before, "Cron analysis should generate warnings")
        
        # 2. Test cron_auto_calculate_payroll
        payroll_count_before = self.env['bang_luong'].search_count([])
        self.env['bang_luong'].cron_auto_calculate_payroll()
        payroll_count_after = self.env['bang_luong'].search_count([])
        self.assertEqual(payroll_count_after, payroll_count_before + 1, "Cron payroll generation should create a new payroll sheet")
        
        # Verify the newly created payroll sheet is in state 'da_tinh'
        new_payroll = self.env['bang_luong'].search([], order='id desc', limit=1)
        self.assertEqual(new_payroll.state, 'da_tinh')
        self.assertEqual(new_payroll.nhan_vien_id.id, self.employee.id)

    def test_05_dashboard_charts(self):
        """Test dashboard chart data generation"""
        dashboard = self.env['dashboard_cham_cong_luong'].create({
            'name': 'Test Dashboard Charts',
            'thang': '6',
            'nam': 2026,
        })
        # Kích hoạt compute các biểu đồ
        dashboard._compute_charts()
        
        # Kiểm nghiệm dữ liệu JSON trả về
        self.assertTrue(dashboard.chart_payroll_history)
        self.assertTrue(dashboard.chart_warning_distribution)
        
        import json
        payroll_data = json.loads(dashboard.chart_payroll_history)
        self.assertEqual(payroll_data['type'], 'bar')
        self.assertIn('labels', payroll_data)
        self.assertIn('datasets', payroll_data)
        
        warn_data = json.loads(dashboard.chart_warning_distribution)
        self.assertEqual(warn_data['type'], 'doughnut')
        self.assertIn('labels', warn_data)
        self.assertIn('datasets', warn_data)

