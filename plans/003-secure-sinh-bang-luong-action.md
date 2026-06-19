# Plan 003: Thêm kiểm tra quyền hạn chặt chẽ khi sinh bảng lương hàng loạt

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise.
>
> **Drift check (run first)**: `git diff --stat 1f284728..HEAD -- addons/cham_cong_tinh_luong/models/bang_luong.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S (30 minutes)
- **Risk**: LOW
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `1f284728`, 2026-06-19

## Why this matters

Trong lớp `bang_luong`, các phương thức thao tác chỉnh sửa bảng lương như `action_tinh_luong`, `action_xac_nhan`,... đều được kiểm tra quyền hạn chặt chẽ qua hàm `_check_payroll_manager_rights()`. 

Tuy nhiên, phương thức sinh bảng lương hàng loạt `action_sinh_bang_luong_thang` (được khai báo ở dạng `@api.model`) hiện tại chưa gọi hàm kiểm tra này ở mức Python. Dù Odoo ORM vẫn chặn quyền tạo/ghi (`create`/`write`) ở tầng dữ liệu khi chạy, việc bổ sung kiểm tra quyền ở mức hàm Python là quy tắc thiết kế phòng vệ chiều sâu (defense-in-depth) tốt để trả về lỗi phân quyền tường minh ngay lập tức khi có cuộc gọi bất hợp pháp (ví dụ: thông qua RPC gọi trực tiếp hàm).

## Current state

- File liên quan:
  - `addons/cham_cong_tinh_luong/models/bang_luong.py` — Chứa lớp `BangLuong`.

Đoạn code phương thức hiện tại (dòng 343–348):
```python
    @api.model
    def action_sinh_bang_luong_thang(self, thang, nam, nhan_vien_ids=None):
        employees = self.env['nhan_vien'].search([])
        if nhan_vien_ids:
            employees = employees.filtered(lambda emp: emp.id in nhan_vien_ids)
```

## Commands you will need

| Purpose   | Command                                                                            | Expected on success |
|-----------|------------------------------------------------------------------------------------|---------------------|
| Upgrade   | `docker exec -u 0 odoo15 odoo -d MaiLan -u cham_cong_tinh_luong --stop-after-init` | exit 0              |
| Restart   | `docker restart odoo15`                                                            | Container restarts  |

## Scope

**In scope**:
- `addons/cham_cong_tinh_luong/models/bang_luong.py`

**Out of scope**:
- Các file view hoặc file wizard khác.

## Steps

### Step 1: Gọi hàm kiểm tra quyền quản lý lương ở đầu phương thức sinh bảng lương

Chỉnh sửa tệp `addons/cham_cong_tinh_luong/models/bang_luong.py` để bổ sung cuộc gọi `self._check_payroll_manager_rights()` ngay đầu hàm:

```python
    @api.model
    def action_sinh_bang_luong_thang(self, thang, nam, nhan_vien_ids=None):
        self._check_payroll_manager_rights()
        employees = self.env['nhan_vien'].search([])
        if nhan_vien_ids:
            employees = employees.filtered(lambda emp: emp.id in nhan_vien_ids)
```

**Verify**: Chạy nâng cấp module và khởi động lại Odoo.

---

## Done criteria

- [ ] Hàm `action_sinh_bang_luong_thang` gọi `self._check_payroll_manager_rights()` ngay dòng đầu tiên của thân hàm.
- [ ] Odoo nâng cấp module và chạy thành công mà không báo lỗi.
