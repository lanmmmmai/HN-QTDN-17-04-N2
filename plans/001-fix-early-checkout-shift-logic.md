# Plan 001: Khắc phục lỗi kiểm tra về sớm theo ca làm việc trong Wizard phân tích chấm công

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise.
>
> **Drift check (run first)**: `git diff --stat 1f284728..HEAD -- addons/cham_cong_tinh_luong/wizards/phan_tich_cham_cong_wizard.py`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S (1-2 hours)
- **Risk**: LOW
- **Depends on**: none
- **Category**: bug
- **Planned at**: commit `1f284728`, 2026-06-19

## Why this matters

Trong Wizard phân tích chấm công (`phan_tich_cham_cong_wizard`), logic kiểm tra cảnh báo "Về sớm" (`ve_som`) hiện đang bị viết cứng (hardcoded) giả định rằng nếu ca làm việc không phải là ca sáng (`sang`) thì sẽ là ca chiều hoặc hành chính và kết thúc lúc 17h00. 

Điều này dẫn đến lỗi logic nghiêm trọng khi nhân viên làm ca tối (`toi`) hoặc ca chiều (`chieu`) riêng biệt:
1. Nhân viên ca tối kết thúc lúc 22h00 nhưng check-out lúc 18h00 (về sớm 4 tiếng) vẫn không bị cảnh báo vì 18h00 > 17h00.
2. Thiết lập quy định giờ ra về cho từng ca cần được tường minh để tránh bỏ sót các vi phạm.

## Current state

- File liên quan:
  - `addons/cham_cong_tinh_luong/wizards/phan_tich_cham_cong_wizard.py` — Chứa hàm `action_phan_tich_canh_bao` thực hiện quét và tạo cảnh báo (dòng 63–86).

Đoạn code hiện tại:
```python
                # 2. Về sớm
                if att.gio_ra and att.trang_thai not in ('nghi', 'nghi_co_phep', 'nghi_khong_phep', 'nua_ngay'):
                    local_ra = att.gio_ra + timedelta(hours=7)
                    is_early = False
                    limit_time_str = ""
                    if att.ca_lam_viec == 'sang':
                        if local_ra.hour < 12:
                            is_early = True
                            limit_time_str = "12:00"
                    else:
                        if local_ra.hour < 17:
                            is_early = True
                            limit_time_str = "17:00"
```

## Commands you will need

| Purpose   | Command                                                                            | Expected on success |
|-----------|------------------------------------------------------------------------------------|---------------------|
| Upgrade   | `docker exec -u 0 odoo15 odoo -d MaiLan -u cham_cong_tinh_luong --stop-after-init` | exit 0              |
| Restart   | `docker restart odoo15`                                                            | Container restarts  |

## Scope

**In scope**:
- `addons/cham_cong_tinh_luong/wizards/phan_tich_cham_cong_wizard.py`

**Out of scope**:
- Các file khác trong thư mục `wizards/` hoặc `models/`.

## Steps

### Step 1: Cập nhật logic đánh giá về sớm cho từng ca làm việc

Chỉnh sửa tệp `addons/cham_cong_tinh_luong/wizards/phan_tich_cham_cong_wizard.py` để phân tách rõ ràng thời gian kết thúc của 4 ca làm việc:
*   `hanh_chinh` (Hành chính): kết thúc lúc 17h00 (`local_ra.hour < 17`)
*   `sang` (Ca sáng): kết thúc lúc 12h00 (`local_ra.hour < 12`)
*   `chieu` (Ca chiều): kết thúc lúc 17h00 (`local_ra.hour < 17`)
*   `toi` (Ca tối): kết thúc lúc 22h00 (`local_ra.hour < 22`)

Đoạn code đề xuất thay thế:
```python
                # 2. Về sớm
                if att.gio_ra and att.trang_thai not in ('nghi', 'nghi_co_phep', 'nghi_khong_phep', 'nua_ngay'):
                    local_ra = att.gio_ra + timedelta(hours=7)
                    is_early = False
                    limit_time_str = ""
                    
                    if att.ca_lam_viec == 'sang':
                        if local_ra.hour < 12:
                            is_early = True
                            limit_time_str = "12:00"
                    elif att.ca_lam_viec == 'toi':
                        if local_ra.hour < 22:
                            is_early = True
                            limit_time_str = "22:00"
                    else: # hanh_chinh hoặc chieu
                        if local_ra.hour < 17:
                            is_early = True
                            limit_time_str = "17:00"
```

**Verify**: Chạy nâng cấp module và khởi động lại Odoo để đảm bảo không lỗi cú pháp Python.

---

## Done criteria

- [ ] Logic ca làm việc trong `phan_tich_cham_cong_wizard.py` đã xử lý riêng ca `toi` (giới hạn 22h00).
- [ ] Chạy nâng cấp module và khởi động lại Odoo thành công.
