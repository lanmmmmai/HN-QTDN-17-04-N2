# Hệ Thống Chấm Công Và Tính Lương

## Mô tả ngắn
Dự án xây dựng trên **Odoo 15** nhằm quản lý nhân sự, chấm công, cấu hình lương, tính lương, cảnh báo thông minh và xuất báo cáo cho doanh nghiệp. Hệ thống kế thừa module `nhan_su` có sẵn và phát triển thêm module `cham_cong_tinh_luong` để kết nối dữ liệu nhân sự với dữ liệu chấm công thực tế.

## Chức năng chính
| Chức năng | Mô tả |
|---|---|
| Quản lý nhân viên | Sử dụng model nhân viên của module `nhan_su` |
| Chấm công | Tạo, xác nhận, hủy bản ghi chấm công |
| Cấu hình lương | Thiết lập lương cơ bản, phụ cấp, bảo hiểm và thời gian áp dụng |
| Bảng lương | Tính lương theo tháng/năm và theo dữ liệu chấm công |
| Báo cáo PDF | In phiếu lương nhân viên dạng PDF |
| Excel | Xuất bảng lương theo tháng/năm ra file Excel |
| Import dữ liệu | Import chấm công từ CSV/XLSX |

## Chức năng nâng cao
| Chức năng nâng cao | Mô tả |
|---|---|
| Workflow chấm công | Trạng thái nháp, đã xác nhận, hủy |
| Workflow bảng lương | Nháp, đã tính, đã xác nhận, đã thanh toán, hủy |
| Dashboard thống kê | Tree, graph, pivot cho chấm công và bảng lương |
| Cảnh báo thông minh | Rule-based alert cho đi muộn, thiếu công, tăng ca quá nhiều, lương bất thường |
| Wizard phân tích | Tạo cảnh báo theo tháng/năm bằng một wizard |
| Phân quyền | Tách nhóm Nhân viên, Nhân sự, Kế toán, Quản trị |
| Liên kết hồ sơ nhân viên | Hiển thị chấm công, cấu hình lương, bảng lương, cảnh báo ngay trên form nhân viên |

## Công nghệ sử dụng
- **Odoo 15**
- Python
- XML / QWeb
- PostgreSQL
- Docker Compose
- CSV / XLSX

## Cấu trúc thư mục
```text
Business-Internship/
├── addons/
│   ├── nhan_su/
│   │   ├── models/
│   │   ├── views/
│   │   └── security/
│   └── cham_cong_tinh_luong/
│       ├── models/
│       ├── views/
│       ├── wizards/
│       ├── reports/
│       ├── security/
│       └── __manifest__.py
├── docker-compose.yml
├── Dockerfile.odoo
└── README.md
```

## Hướng dẫn cài đặt
### 1. Clone dự án
```bash
git clone <repository-url>
cd Business-Internship
```

### 2. Chuẩn bị môi trường
- Cài Docker và Docker Compose
- Đảm bảo máy có quyền chạy Docker

### 3. Kiểm tra module
- `addons/nhan_su` là module nhân sự gốc
- `addons/cham_cong_tinh_luong` là module phát triển thêm

## Hướng dẫn chạy bằng Docker Compose
### Khởi động database và Odoo
```bash
docker compose up -d
```

### Cập nhật module sau khi thay đổi code
```bash
docker compose run --rm odoo odoo -d MaiLan --addons-path=/usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons -u nhan_su,cham_cong_tinh_luong --stop-after-init
docker compose up --build
```

### Ghi chú
- Service Odoo trong `docker-compose.yml` là `odoo`
- Project sử dụng Odoo 15

## Hướng dẫn cài module trong Odoo
1. Mở Odoo tại `http://localhost:8069`
2. Đăng nhập bằng tài khoản quản trị
3. Vào `Apps`
4. Bấm `Update Apps List` nếu cần
5. Tìm và cài các module:
   - `nhan_su`
   - `cham_cong_tinh_luong`

## Tài khoản demo
Hiện tại dự án **chưa đi kèm tài khoản demo cố định** trong README.

Nếu bạn có dữ liệu demo hoặc người dùng mẫu, hãy bổ sung tại đây:
| Tài khoản | Mật khẩu | Vai trò |
|---|---|---|
| `admin` | `admin` | Quản trị |

## Quy trình demo
1. Vào `QLNS` tạo nhân viên mới.
2. Vào `Chấm công` tạo bản ghi chấm công và xác nhận.
3. Vào `Tính lương > Cấu hình lương` tạo cấu hình lương cho từng nhân viên.
4. Vào `Tính lương > Bảng lương` bấm `Tính lương`.
5. Xem bảng lương, mở form chi tiết và in `Phiếu lương PDF`.
6. Vào `Tính lương > Báo cáo & Thống kê` để xem graph/pivot.
7. Vào `Tính lương > Cảnh báo thông minh` và `Phân tích cảnh báo` để tạo rule-based warning.
8. Vào `Tính lương > Xuất bảng lương Excel` để tải file Excel.
9. Vào `Chấm công > Import chấm công` để nhập dữ liệu từ CSV/XLSX.

```

## Nguồn tham khảo
- [Odoo 15 Documentation](https://www.odoo.com/documentation/15.0/)
- [Odoo QWeb Reports](https://www.odoo.com/documentation/15.0/developer/reference/backend/reports.html)
- [Odoo ORM](https://www.odoo.com/documentation/15.0/developer/reference/backend/orm.html)
- Tài liệu học phần Thực tập doanh nghiệp / Hội nhập và Quản trị phần mềm doanh nghiệp


## Thông tin kỹ thuật
- Hệ thống chạy trên **Odoo 15**
- Không dùng `hr.employee`
- Module chấm công và tính lương liên kết trực tiếp với module `nhan_su`
- Có hỗ trợ báo cáo PDF, dashboard, wizard và import/export dữ liệu

