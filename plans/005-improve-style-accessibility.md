# Plan 005: Tinh chỉnh Giao diện và Khả năng tiếp cận (Accessibility & Contrast) theo tiêu chuẩn Impeccable

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise.
>
> **Drift check (run first)**: `git diff --stat 1f284728..HEAD -- addons/cham_cong_tinh_luong/static/src/scss/cham_cong_tinh_luong.scss`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P3
- **Effort**: S (1 hour)
- **Risk**: LOW
- **Depends on**: none
- **Category**: tech-debt
- **Planned at**: commit `1f284728`, 2026-06-19

## Why this matters

Theo các nguyên tắc thiết kế khả năng tiếp cận (Accessibility / WCAG AA) trong `Impeccable` và `Taste Skill`, độ tương phản màu sắc của chữ hiển thị so với nền phải đạt tối thiểu **4.5:1** đối với văn bản thông thường để đảm bảo tính dễ đọc cho tất cả người dùng. 

Khi kiểm tra tệp CSS `cham_cong_tinh_luong.scss`, phát sinh một số điểm vi phạm độ tương phản:
1. Nhãn chữ xám nhạt `.o_cctl_salary_total_box .text-muted` (màu `#6b7280`) trên nền xanh nhạt `$cctl-blue-soft` (`#E4F4FD`) chỉ đạt tỷ lệ tương phản **3.0:1** (dưới mức tối thiểu 4.5:1).
2. Tương phản của nhãn `.o_cctl_stat_label` (màu `$cctl-navy` `#0369A1`) trên nền thẻ thông tin `.o_cctl_stat_card--info` (nền `$cctl-blue-soft` `#E4F4FD`) chỉ đạt **3.8:1**.
3. Chữ của thẻ trạng thái cảnh báo màu cam `.o_cctl_badge_warning` (màu `darken($cctl-orange, 12%)` trên nền cam nhạt `$cctl-orange-soft` `#fff7ed`) chỉ đạt **4.2:1**.
4. Các hiệu ứng chuyển động hover trên thẻ thống kê chưa có cấu hình giảm chuyển động `@media (prefers-reduced-motion: reduce)` theo tiêu chuẩn bắt buộc của Impeccable.

## Current state

- File liên quan:
  - `addons/cham_cong_tinh_luong/static/src/scss/cham_cong_tinh_luong.scss` — Định nghĩa CSS/SCSS tùy chỉnh cho module Chấm công & Tính lương.

Đoạn mã hiện tại có độ tương phản thấp (dòng 272–276):
```scss
.o_cctl_salary_total_box .text-muted {
  color: $cctl-gray !important;
  font-weight: 700;
}
```

Đoạn mã hiện tại của nhãn thẻ (dòng 153–158):
```scss
.o_cctl_stat_label {
  font-size: 0.92rem;
  font-weight: 700;
  color: $cctl-navy;
  letter-spacing: 0.01em;
}
```

Đoạn mã hiện tại của badge màu cam (dòng 181–185):
```scss
.o_cctl_badge_warning {
  background: $cctl-orange-soft;
  color: darken($cctl-orange, 12%);
  border: 1px solid rgba(245, 158, 11, 0.20);
}
```

Đoạn mã hiện tại của hiệu ứng hover (dòng 85–92):
```scss
  box-shadow: 0 12px 28px rgba(23, 50, 77, 0.06);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 18px 36px rgba(23, 50, 77, 0.12);
    border-color: rgba(37, 99, 235, 0.16);
  }
```

## Commands you will need

| Purpose   | Command                                                                            | Expected on success |
|-----------|------------------------------------------------------------------------------------|---------------------|
| Upgrade   | `docker exec -u 0 odoo15 odoo -d MaiLan -u cham_cong_tinh_luong --stop-after-init` | exit 0              |
| Restart   | `docker restart odoo15`                                                            | Container restarts  |

## Scope

**In scope**:
- `addons/cham_cong_tinh_luong/static/src/scss/cham_cong_tinh_luong.scss`

**Out of scope**:
- Thay đổi cấu trúc HTML/XML.
- Thay đổi các module CSS của hệ thống Odoo core.

## Steps

### Step 1: Cải thiện độ tương phản màu chữ trong file SCSS

Chỉnh sửa tệp `addons/cham_cong_tinh_luong/static/src/scss/cham_cong_tinh_luong.scss` để tăng độ tối của màu chữ trên nền sáng:

1. Tăng độ tương phản của chữ `.o_cctl_salary_total_box .text-muted` bằng cách đổi từ màu `$cctl-gray` sang một màu xám đậm hơn (ví dụ `#374151`) hoặc `$cctl-navy`.
2. Tăng độ tương phản của nhãn `.o_cctl_stat_label` khi nằm trong thẻ có nền xanh nhạt bằng cách bổ sung quy tắc màu tối hơn (ví dụ `#0c4a6e`).
3. Tối màu chữ của `.o_cctl_badge_warning` bằng cách thay đổi giá trị từ `darken($cctl-orange, 12%)` thành `darken($cctl-orange, 18%)` (tương ứng mã màu tối hơn đạt tỷ lệ tương phản >4.5:1).

Đề xuất thay đổi:

```scss
// Tăng độ tương phản của nhãn trong thẻ thống kê thông tin
.o_cctl_stat_label {
  font-size: 0.92rem;
  font-weight: 700;
  color: darken($cctl-navy, 8%); // Dùng màu navy đậm hơn để tăng tương phản
  letter-spacing: 0.01em;
}

// Tối ưu hóa màu chữ badge cảnh báo
.o_cctl_badge_warning {
  background: $cctl-orange-soft;
  color: darken($cctl-orange, 18%); // Đậm hơn (từ 12% lên 18%) để đạt tỷ lệ tương phản WCAG AA
  border: 1px solid rgba(245, 158, 11, 0.20);
}

// Tăng tương phản nhãn trong khung Tổng lương nhận được
.o_cctl_salary_total_box .text-muted {
  color: darken($cctl-navy, 5%) !important; // Chuyển từ xám nhạt sang Navy đậm
  font-weight: 700;
}
```

### Step 2: Bổ sung hỗ trợ giảm chuyển động (Prefers Reduced Motion)

Thêm quy tắc `@media (prefers-reduced-motion: reduce)` cho thẻ thống kê `.o_cctl_stat_card` nhằm tắt bỏ hiệu ứng dịch chuyển `translateY` và bóng đổ mượt khi người dùng có thiết lập nhạy cảm với chuyển động:

```scss
.o_cctl_stat_card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 100%;
  padding: 16px 16px 15px;
  border: 1px solid $cctl-border;
  border-radius: 18px;
  background: linear-gradient(180deg, #fff, $cctl-gray-soft);
  box-shadow: 0 12px 28px rgba(23, 50, 77, 0.06);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 18px 36px rgba(23, 50, 77, 0.12);
    border-color: rgba(37, 99, 235, 0.16);
  }

  @media (prefers-reduced-motion: reduce) {
    transition: none;
    &:hover {
      transform: none; // Tắt dịch chuyển translateY khi di chuột
    }
  }
  // ...
```

**Verify**: Chạy nâng cấp module và khởi động lại Odoo để áp dụng CSS mới.

---

## Done criteria

- [ ] Tất cả các nhãn chữ trong `.o_cctl_salary_total_box` và `.o_cctl_stat_card` đều đạt tỷ lệ tương phản tối thiểu 4.5:1.
- [ ] Bổ sung khối `@media (prefers-reduced-motion: reduce)` cho `.o_cctl_stat_card`.
- [ ] Biên dịch SCSS của Odoo chạy thành công không bị lỗi cú pháp.
