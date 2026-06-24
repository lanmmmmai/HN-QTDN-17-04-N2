# Kế hoạch cải tiến và tối ưu hóa hệ thống (Implementation Plans)

Được tạo bởi kỹ năng `improve` vào ngày 19/06/2026. Hãy thực thi các kế hoạch dưới đây theo thứ tự khuyến nghị để đảm bảo hiệu năng và độ ổn định cao nhất cho hệ thống Chấm công và Tính lương.

## Thứ tự thực thi & Trạng thái

| Kế hoạch | Tiêu đề kế hoạch | Độ ưu tiên | Độ phức tạp | Phụ thuộc vào | Trạng thái |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **001** | [Khắc phục lỗi kiểm tra về sớm theo ca làm việc trong Wizard phân tích chấm công](file:///d:/My_Lan/HN-QTDN-17-04-N2/plans/001-fix-early-checkout-shift-logic.md) | P1 | S | — | DONE |
| **002** | [Tối ưu hiệu năng bằng cách gộp tạo cảnh báo (Bulk Create) trong Wizard phân tích chấm công](file:///d:/My_Lan/HN-QTDN-17-04-N2/plans/002-bulk-create-attendance-alerts.md) | P2 | M | 001 | DONE |
| **003** | [Thêm kiểm tra quyền hạn chặt chẽ khi sinh bảng lương hàng loạt](file:///d:/My_Lan/HN-QTDN-17-04-N2/plans/003-secure-sinh-bang-luong-action.md) | P3 | S | — | DONE |
| **004** | [Tối ưu hóa hiệu năng tính lương (Giảm thiểu truy vấn N+1) trong Bảng lương](file:///d:/My_Lan/HN-QTDN-17-04-N2/plans/004-optimize-payroll-nplusone.md) | P2 | M | — | DONE |
| **005** | [Tinh chỉnh Giao diện và Khả năng tiếp cận (Accessibility & Contrast) theo tiêu chuẩn Impeccable](file:///d:/My_Lan/HN-QTDN-17-04-N2/plans/005-improve-style-accessibility.md) | P3 | S | — | DONE |
| **006** | [Tự động hóa gửi Phiếu lương qua Email & Chatter](file:///d:/My_Lan/HN-QTDN-17-04-N2/plans/006-auto-send-payroll-email.md) | P2 | S | — | DONE |
| **007** | [Thiết lập Cron Job tự động tính công và sinh bảng lương định kỳ cuối tháng](file:///d:/My_Lan/HN-QTDN-17-04-N2/plans/007-auto-payroll-cron.md) | P2 | S | — | TODO |
| **008** | [Nâng cấp AI Chatbot Nhân sự lên chuẩn OpenAI Chat Completions API](file:///d:/My_Lan/HN-QTDN-17-04-N2/plans/008-upgrade-ai-chatbot.md) | P2 | S | — | TODO |
| **009** | [Bổ sung biểu đồ phân tích dữ liệu trực quan trên Dashboard](file:///d:/My_Lan/HN-QTDN-17-04-N2/plans/009-dashboard-visual-charts.md) | P2 | S | — | TODO |

*Trạng thái có thể cập nhật: `TODO` \| `IN PROGRESS` \| `DONE` \| `BLOCKED` \| `REJECTED`*

## Chi tiết sự phụ thuộc

*   **002 phụ thuộc vào 001**: Vì cả hai kế hoạch đều chỉnh sửa cùng một vị trí trong hàm `action_phan_tich_canh_bao` của tệp `phan_tich_cham_cong_wizard.py`. Cần sửa logic phân tách ca làm việc trước (Plan 001), sau đó mới thực hiện gom cấu trúc danh sách để bulk create (Plan 002) nhằm tránh xung đột code (conflict).

## Các phát hiện được cân nhắc và bỏ qua (Rejected Findings)

*   **Tối ưu hóa các truy vấn trong Dashboard (`dashboard_cham_cong_luong.py`)**: Đã được cân nhắc. Tuy nhiên, do bản ghi Dashboard là một cấu trúc đơn (thường chỉ tải 1 bản ghi duy nhất trên giao diện), số lượng truy vấn thực tế phát sinh khi chạy là cố định và không tăng tiến theo số lượng nhân viên. Do đó, việc tái cấu trúc gộp truy vấn tại đây mang lại lợi ích hiệu năng rất nhỏ nhưng làm tăng độ phức tạp của mã nguồn nên tạm thời bỏ qua.
