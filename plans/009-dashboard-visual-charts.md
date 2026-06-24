# Plan 009: Bổ sung biểu đồ phân tích dữ liệu trực quan trên Dashboard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Goal:** Nhúng các biểu đồ tương tác trực quan (quỹ lương 6 tháng qua và phân bổ cảnh báo chấm công) trực tiếp vào màn hình Dashboard form view bằng Chart.js và Odoo 15 OWL Field Component.
>
> **Architecture:**
> - Bổ sung các trường tính toán (computed fields) trong `dashboard_cham_cong_luong.py` trả về chuỗi JSON chứa cấu hình và dữ liệu biểu đồ.
> - Viết một OWL Field Component mới trong JS để khởi tạo và vẽ đồ thị Chart.js trên thẻ `<canvas>`.
> - Đưa các trường đồ thị này vào giao diện Form View của Dashboard trong `dashboard_views.xml`.
>
> **Tech Stack:** Python, Odoo 15.0 model API, XML, JavaScript (OWL), Chart.js (sẵn có trong Odoo Backend).

## Global Constraints

- Biểu đồ phải tự động cập nhật khi người dùng thay đổi Kỳ (tháng/năm) trên Dashboard hoặc bấm "Cập nhật".
- Màu sắc của các đường đồ thị phải tương phản tốt, đạt chuẩn dễ tiếp cận (WCAG AA).
- Thiết lập tùy chọn giảm hiệu ứng chuyển động nếu người dùng bật chế độ thích ứng hệ điều hành (`prefers-reduced-motion`).

---

### Task 1: Bổ sung trường JSON dữ liệu biểu đồ trên Model Python

**Files:**
- Modify: `addons/cham_cong_tinh_luong/models/dashboard_cham_cong_luong.py`

- [ ] **Step 1: Khai báo trường mới và viết hàm compute**
  Thêm khai báo trường:
  
  ```python
      chart_payroll_history = fields.Text(string='Dữ liệu biểu đồ quỹ lương', compute='_compute_charts')
      chart_warning_distribution = fields.Text(string='Dữ liệu biểu đồ cảnh báo', compute='_compute_charts')
  ```

  Viết hàm compute `_compute_charts` tính toán dữ liệu:
  
  ```python
      def _compute_charts(self):
          import json
          salary_model = self.env['bang_luong']
          warning_model = self.env['canh_bao_cham_cong']
          
          for rec in self:
              # --- 1. Dữ liệu Quỹ lương 6 tháng gần nhất ---
              # Lấy mốc thời gian 6 tháng
              labels_payroll = []
              data_payroll = []
              
              current_month = int(rec.thang)
              current_year = rec.nam
              
              for i in range(5, -1, -1):
                  m = current_month - i
                  y = current_year
                  if m <= 0:
                      m += 12
                      y -= 1
                  labels_payroll.append('T%s/%s' % (m, y))
                  
                  # Query tổng thực lĩnh
                  salaries = salary_model.sudo().search([
                      ('thang', '=', str(m)),
                      ('nam', '=', y),
                      ('state', '=', 'da_thanh_toan'),
                  ])
                  data_payroll.append(sum(salaries.mapped('thuc_linh')))
                  
              rec.chart_payroll_history = json.dumps({
                  'type': 'bar',
                  'labels': labels_payroll,
                  'datasets': [{
                      'label': 'Quỹ lương thực lĩnh (VND)',
                      'data': data_payroll,
                      'backgroundColor': 'rgba(102, 16, 242, 0.65)', # HSL Purple
                      'borderColor': 'rgb(102, 16, 242)',
                      'borderWidth': 1
                  }],
                  'options': {
                      'responsive': True,
                      'maintainAspectRatio': False,
                      'plugins': {
                          'legend': {'display': True}
                      }
                  }
              })
              
              # --- 2. Dữ liệu Phân bổ Cảnh báo Chấm công ---
              warn_groups = warning_model.read_group(
                  [('thang', '=', rec.thang), ('nam', '=', rec.nam)],
                  ['loai_canh_bao'],
                  ['loai_canh_bao']
              )
              
              alert_types = {
                  'di_muon_nhieu': 'Đi muộn nhiều',
                  'thieu_cong': 'Thiếu công',
                  'tang_ca_qua_nhieu': 'Tăng ca quá nhiều',
                  'thieu_du_lieu_cham_cong': 'Thiếu giờ vào/ra',
                  'di_muon': 'Đi muộn',
                  've_som': 'Về sớm',
                  'thieu_gio_ra': 'Thiếu giờ ra',
              }
              
              labels_warn = []
              data_warn = []
              for group in warn_groups:
                  lbl = alert_types.get(group.get('loai_canh_bao'), 'Khác')
                  count = group.get('loai_canh_bao_count', 0)
                  if lbl in labels_warn:
                      # Gộp trùng lặp nếu có
                      idx = labels_warn.index(lbl)
                      data_warn[idx] += count
                  else:
                      labels_warn.append(lbl)
                      data_warn.append(count)
                      
              # Nếu trống, chèn dữ liệu rỗng trực quan
              if not labels_warn:
                  labels_warn = ['Không có cảnh báo']
                  data_warn = [0]
                  
              rec.chart_warning_distribution = json.dumps({
                  'type': 'doughnut',
                  'labels': labels_warn,
                  'datasets': [{
                      'label': 'Số lượng cảnh báo',
                      'data': data_warn,
                      'backgroundColor': [
                          '#dc3545', '#ffc107', '#28a745', '#17a2b8', '#6610f2', '#e83e8c', '#6c757d'
                      ]
                  }],
                  'options': {
                      'responsive': True,
                      'maintainAspectRatio': False,
                  }
              })
  ```

- [ ] **Step 2: Commit**
  ```bash
  git add addons/cham_cong_tinh_luong/models/dashboard_cham_cong_luong.py
  git commit -m "feat: add JSON chart fields in dashboard_cham_cong_luong model"
  ```

---

### Task 2: Xây dựng OWL Field Component hiển thị biểu đồ

**Files:**
- Create: `addons/cham_cong_tinh_luong/static/src/js/dashboard_chart_widget.js`
- Modify: `addons/cham_cong_tinh_luong/__manifest__.py`

- [ ] **Step 1: Viết OWL Component đăng ký widget**
  Tạo tệp `addons/cham_cong_tinh_luong/static/src/js/dashboard_chart_widget.js`:
  
  ```javascript
  /** @odoo-module **/
  import { Component, xml, onMounted, useRef } from "@odoo/owl";
  import { registry } from "@web/core/registry";
  
  export class DashboardChartWidget extends Component {
      setup() {
          this.canvasRef = useRef("chartCanvas");
          this.chart = null;
          onMounted(() => {
              this.renderChart();
          });
      }
  
      renderChart() {
          const val = this.props.value || "{}";
          let config = {};
          try {
              config = JSON.parse(val);
          } catch (e) {
              return;
          }
          if (!config || !config.labels) return;
  
          const ctx = this.canvasRef.el;
          if (this.chart) {
              this.chart.destroy();
          }
  
          if (typeof Chart !== "undefined") {
              // Thêm tính năng Reduced Motion thích ứng
              const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
              const isReduced = mediaQuery && mediaQuery.matches;
              if (isReduced && config.options) {
                  config.options.animation = false;
              }
              this.chart = new Chart(ctx, {
                  type: config.type || "bar",
                  data: {
                      labels: config.labels,
                      datasets: config.datasets,
                  },
                  options: config.options || {
                      responsive: true,
                      maintainAspectRatio: false,
                  }
              });
          }
      }
  }
  
  DashboardChartWidget.template = xml`
      <div style="position: relative; height: 300px; width: 100%;">
          <canvas t-ref="chartCanvas"/>
      </div>
  `;
  
  registry.category("fields").add("dashboard_chart_widget", DashboardChartWidget);
  ```

- [ ] **Step 2: Đăng ký tệp Javascript vào backend assets**
  Sửa `addons/cham_cong_tinh_luong/__manifest__.py` để khai báo `assets` ở cuối manifest:
  
  ```python
      'assets': {
          'web.assets_backend': [
              'cham_cong_tinh_luong/static/src/js/dashboard_chart_widget.js',
          ],
      },
  ```

- [ ] **Step 3: Commit**
  ```bash
  git add addons/cham_cong_tinh_luong/static/src/js/dashboard_chart_widget.js addons/cham_cong_tinh_luong/__manifest__.py
  git commit -m "feat: implement OWL dashboard_chart_widget field component"
  ```

---

### Task 3: Nhúng biểu đồ trực quan vào giao diện XML Dashboard

**Files:**
- Modify: `addons/cham_cong_tinh_luong/views/dashboard_views.xml`

- [ ] **Step 1: Đưa các biểu đồ vào form view**
  Mở tệp `addons/cham_cong_tinh_luong/views/dashboard_views.xml`. Tìm `dashboard_tinh_luong_form_view` (ở khoảng dòng 120-240) và nhúng biểu đồ bên dưới bảng thống kê nhanh (trước thẻ `</sheet>`):
  
  ```xml
                              <div class="row mt-4">
                                  <div class="col-12 col-lg-8">
                                      <div class="card p-3 shadow-sm border-0">
                                          <div class="fw-bold mb-2">Thống kê Quỹ lương 6 tháng qua</div>
                                          <field name="chart_payroll_history" widget="dashboard_chart_widget" nolabel="1" readonly="1"/>
                                      </div>
                                  </div>
                                  <div class="col-12 col-lg-4">
                                      <div class="card p-3 shadow-sm border-0">
                                          <div class="fw-bold mb-2">Phân bổ cảnh báo chấm công</div>
                                          <field name="chart_warning_distribution" widget="dashboard_chart_widget" nolabel="1" readonly="1"/>
                                      </div>
                                  </div>
                              </div>
  ```

- [ ] **Step 2: Nâng cấp module và chạy thử nghiệm**
  Khởi động lại Odoo, bấm nâng cấp module `cham_cong_tinh_luong` và truy cập Dashboard tính lương để kiểm nghiệm biểu đồ hiển thị.

- [ ] **Step 3: Commit**
  ```bash
  git add addons/cham_cong_tinh_luong/views/dashboard_views.xml
  git commit -m "feat: embed payroll history and warning distribution charts in dashboard view"
  ```

---

## Done criteria

- [ ] Các trường `chart_payroll_history` và `chart_warning_distribution` sinh chuỗi JSON hợp lệ.
- [ ] OWL Widget `dashboard_chart_widget` hiển thị chính xác đồ thị cột và đồ thị bánh donut.
- [ ] Dữ liệu biểu đồ tự động cập nhật lại khi bấm nút "Cập nhật".

## STOP conditions

- Lỗi biên dịch JavaScript hoặc OWL Component làm vỡ giao diện Odoo Backend.
- Không tải được thư viện Chart.js gây báo lỗi `Chart is not defined`.
