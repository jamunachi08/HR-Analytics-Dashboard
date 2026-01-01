frappe.pages['saudization-hr-analytics'] = {
  on_page_load: function(wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: 'Saudization HR Analytics',
      single_column: true
    });

    const state = {
      filters: {
        company: null,
        department: null,
        designation: null,
        nationality_group: null
      },
      theme: null,
      navigation: null,
      active_tab: null
    };

    const filters = page.add_field({
      fieldtype: 'Link',
      fieldname: 'company',
      label: 'Company',
      options: 'Company',
      reqd: 1,
      change: () => refresh_all()
    });

    page.add_field({
      fieldtype: 'Link',
      fieldname: 'department',
      label: 'Department',
      options: 'Department',
      change: () => refresh_all()
    });

    page.add_field({
      fieldtype: 'Link',
      fieldname: 'designation',
      label: 'Designation',
      options: 'Designation',
      change: () => refresh_all()
    });

    page.add_field({
      fieldtype: 'Select',
      fieldname: 'nationality_group',
      label: 'Nationality Group',
      options: [''].concat(['Saudi','GCC','Non-GCC','Unknown']),
      change: () => refresh_all()
    });

    // Layout
    const $container = $(page.main).addClass('sd-dashboard').append(`
      <div class="sd-tabs" id="sd-tabs"></div>
        <div class="sd-grid" style="display:grid; grid-template-columns: repeat(12, 1fr); gap: 12px;">
        <div class="sd-card" style="grid-column: span 12; display:grid; grid-template-columns: repeat(8, 1fr); gap: 12px;" id="sd-kpis"></div>

        <div class="sd-card" style="grid-column: span 4;" id="sd-chart-nationality"></div>
        <div class="sd-card" style="grid-column: span 8;" id="sd-chart-actual-target"></div>

        <div class="sd-card" style="grid-column: span 6;" id="sd-chart-designation"></div>
        <div class="sd-card" style="grid-column: span 6;" id="sd-chart-department"></div>

        <div class="sd-card" style="grid-column: span 6;" id="sd-chart-salary"></div>
        <div class="sd-card" style="grid-column: span 6;" id="sd-chart-trend"></div>

        <div class="sd-card" style="grid-column: span 12;" id="sd-table-matrix"></div>
      </div>
    `);

    const charts = {};

    function parse_palette(p) {
      const raw = (p || '').split(',').map(x => (x || '').trim()).filter(Boolean);
      return raw.length ? raw : ['#1E90FF','#22C55E','#F59E0B','#EF4444','#A855F7','#06B6D4','#F97316','#84CC16'];
    }

    function apply_theme(t) {
      state.theme = t || {};
      const el = page.main;
      if (!el) return;
      const theme = state.theme;
      // Apply CSS variables
      el.style.setProperty('--sd-page-bg', theme.page_background || '#5b0d55');
      el.style.setProperty('--sd-panel-bg', theme.panel_background || '#7a1b73');
      el.style.setProperty('--sd-card-bg', theme.card_background || '#6a1665');
      el.style.setProperty('--sd-border', theme.border_color || 'rgba(255,255,255,0.25)');
      el.style.setProperty('--sd-text', theme.text_color || '#ffffff');
      el.style.setProperty('--sd-muted', theme.muted_text_color || 'rgba(255,255,255,0.70)');
      el.style.setProperty('--sd-kpi', theme.kpi_value_color || '#ffffff');
      el.style.setProperty('--sd-tab-bg', theme.tab_bg_color || theme.card_background || '#6a1665');
      el.style.setProperty('--sd-tab-text', theme.tab_text_color || theme.text_color || '#ffffff');
      el.style.setProperty('--sd-tab-active-bg', theme.tab_active_bg_color || '#1E90FF');
      el.style.setProperty('--sd-tab-active-text', theme.tab_active_text_color || '#ffffff');
    }

    function get_filters() {
      const f = {
        company: page.fields_dict.company.get_value(),
        department: page.fields_dict.department.get_value(),
        designation: page.fields_dict.designation.get_value(),
        nationality_group: page.fields_dict.nationality_group.get_value()
      };
      return f;
    }

    function call(method, args={}) {
      // API methods accept company/department/designation/nationality_group as direct kwargs
      return frappe.call({
        method: `saudization_dashboard.api.${method}`,
        args: Object.assign(get_filters(), args)
      }).then(r => r.message);
    }

    function render_kpis(k) {
      const cards = [
        {label: 'Total Employees', value: k.total_employees},
        {label: 'Saudi Employees', value: k.saudi_employees},
        {label: 'Non-Saudi Employees', value: k.non_saudi_employees},
        {label: 'Saudization %', value: (k.saudization_percent ?? 0) + '%'},
        {label: 'Avg Salary (Saudi)', value: k.avg_salary_saudi},
        {label: 'Avg Salary (Non-Saudi)', value: k.avg_salary_non_saudi},
        {label: 'Avg Tenure (Saudi)', value: (k.avg_tenure_years_saudi ?? 0) + ' yrs'},
        {label: 'Avg Tenure (Non-Saudi)', value: (k.avg_tenure_years_non_saudi ?? 0) + ' yrs'},
      ];

      const $kpis = $('#sd-kpis').empty();
      cards.forEach(c => {
        $kpis.append(`
          <div class="sd-kpi" style="grid-column: span 1;">
            <div class="sd-kpi-label">${frappe.utils.escape_html(c.label)}</div>
            <div class="sd-kpi-value">${frappe.utils.escape_html(String(c.value ?? 0))}</div>
          </div>
        `);
      });
    }

    function upsert_chart(id, title, chart_type, labels, datasets) {
      const el = document.getElementById(id);
      if (!el) return;
      $(el).empty().append(`<h4 style="margin:0 0 8px 0;">${frappe.utils.escape_html(title)}</h4><div class="sd-chart"></div>`);
      const target = $(el).find('.sd-chart')[0];

      const palette = parse_palette((state.theme || {}).chart_palette);
      const height = (state.theme && state.theme.chart_height) ? parseInt(state.theme.chart_height) : 260;

      const data = {
        labels,
        datasets
      };

      charts[id] = new frappe.Chart(target, {
        title: '',
        data,
        type: chart_type,
        height: height,
        truncateLegends: 1,
        colors: palette,
        axisOptions: { xAxisMode: 'tick', yAxisMode: 'span' },
        barOptions: { stacked: chart_type === 'bar' }
      });
    }

    function render_table_matrix(rows) {
      const $el = $('#sd-table-matrix').empty();
      $el.append('<h4 style="margin:0 0 8px 0;">Saudization Matrix (Department × Designation)</h4>');
      if (!rows || !rows.length) {
        $el.append('<div class="text-muted">No data.</div>');
        return;
      }

      const header = ['Department','Designation','Saudi','Total','Saudization %','Target %','Variance'];
      let html = '<div style="overflow:auto;"><table class="table table-bordered"><thead><tr>';
      header.forEach(h => html += `<th>${frappe.utils.escape_html(h)}</th>`);
      html += '</tr></thead><tbody>';

      rows.forEach(r => {
        html += '<tr>';
        html += `<td>${frappe.utils.escape_html(r.department || '')}</td>`;
        html += `<td>${frappe.utils.escape_html(r.designation || '')}</td>`;
        html += `<td>${frappe.utils.escape_html(String(r.saudi_count ?? 0))}</td>`;
        html += `<td>${frappe.utils.escape_html(String(r.total_count ?? 0))}</td>`;
        html += `<td>${frappe.utils.escape_html(String(r.saudization_percent ?? 0))}</td>`;
        html += `<td>${frappe.utils.escape_html(String(r.target_percent ?? ''))}</td>`;
        html += `<td>${frappe.utils.escape_html(String(r.variance_percent ?? ''))}</td>`;
        html += '</tr>';
      });

      html += '</tbody></table></div>';
      $el.append(html);
    }



    function build_url(route, params) {
      const qp = params || {};
      const query = Object.keys(qp).filter(k => qp[k]).map(k => `${encodeURIComponent(k)}=${encodeURIComponent(qp[k])}`).join('&');
      return query ? `/app/${route}?${query}` : `/app/${route}`;
    }

    function render_tabs(nav) {
      const $tabs = $('#sd-tabs');
      $tabs.empty();

      if (!nav || !nav.enable_tabs) {
        $tabs.hide();
        return;
      }
      $tabs.show();

      (nav.tabs || []).forEach(tab => {
        const isActive = (state.active_tab && state.active_tab === tab.tab_label);
        const cls = isActive ? 'sd-tab sd-tab-active' : 'sd-tab';
        const $btn = $(`<button type="button" class="${cls}">${frappe.utils.escape_html(tab.tab_label || '')}</button>`);
        $btn.on('click', () => handle_tab_click(tab));
        $tabs.append($btn);
      });
    }

    function handle_tab_click(tab) {
      state.active_tab = tab.tab_label || null;
      render_tabs(state.navigation);

      const filters = {
        company: tab.company || page.fields_dict.company.get_value(),
        department: tab.department || page.fields_dict.department.get_value(),
        designation: tab.designation || page.fields_dict.designation.get_value(),
        nationality_group: tab.nationality_group || page.fields_dict.nationality_group.get_value(),
      };

      if ((tab.tab_type || '') === 'Filter Dashboard') {
        if (tab.company) page.fields_dict.company.set_value(tab.company);
        if (tab.department) page.fields_dict.department.set_value(tab.department);
        if (tab.designation) page.fields_dict.designation.set_value(tab.designation);
        if (tab.nationality_group) page.fields_dict.nationality_group.set_value(tab.nationality_group);
        refresh_all();
        return;
      }

      if ((tab.tab_type || '') === 'Route Link') {
        const route = tab.route || 'saudization-hr-analytics';
        if (tab.open_in_new_window) {
          window.open(build_url(route, filters), '_blank');
        } else {
          frappe.route_options = filters;
          frappe.set_route(route);
        }
        return;
      }

      if ((tab.tab_type || '') === 'Report Link') {
        const report = tab.report_name;
        if (!report) {
          frappe.msgprint('This tab is configured as a Report Link but no report is set.');
          return;
        }
        if (tab.open_in_new_window) {
          const url = build_url(`query-report/${encodeURIComponent(report)}`, filters);
          window.open(url, '_blank');
        } else {
          frappe.route_options = filters;
          frappe.set_route('query-report', report);
        }
        return;
      }
    }

    async function ensure_navigation() {
      if (state.navigation) return;
      try {
        const nav = await call('get_navigation');
        state.navigation = nav;
        render_tabs(nav);
      } catch (e) {
        // Fail silently; dashboard should still work.
      }
    }

    async function refresh_all() {
      const f = get_filters();
      if (!f.company) {
        frappe.msgprint('Please select Company.');
        return;
      }

      if (!state.theme) {
        const t = await call('get_theme');
        apply_theme(t);
      }

      await ensure_navigation();

      const [kpis, natRows, actualTarget, desig, dept, salary, trend, matrix] = await Promise.all([
        call('get_kpis'),
        call('get_nationality_group_breakdown'),
        call('get_actual_vs_target_overall'),
        call('get_saudization_by_designation', {min_headcount: 3}),
        call('get_saudization_by_department'),
        call('get_saudization_by_salary_band'),
        call('get_saudization_trend', {months_back: 24}),
        call('get_matrix_with_targets', {min_headcount: 3})
      ]);

      render_kpis(kpis);

      // Nationality (donut)
      const nat = {
        labels: (natRows || []).map(r => r.label),
        datasets: [{ name: 'Headcount', values: (natRows || []).map(r => r.value)}]
      };
      upsert_chart(
        'sd-chart-nationality',
        'Saudization by Nationality Group',
        'donut',
        nat.labels,
        nat.datasets
      );

      // Actual vs Target
      upsert_chart(
        'sd-chart-actual-target',
        'Saudization Actual vs KSA Target',
        'bar',
        actualTarget.labels,
        actualTarget.datasets
      );

      // Designation
      upsert_chart(
        'sd-chart-designation',
        'Saudization by Designation (Saudi %)',
        'bar',
        desig.labels,
        desig.datasets
      );

      // Department (stacked counts)
      upsert_chart(
        'sd-chart-department',
        'Department-wise Saudization (Headcount)',
        'bar',
        dept.labels,
        dept.datasets
      );

      // Salary band
      upsert_chart(
        'sd-chart-salary',
        'Saudization by Salary Band (Saudi %)',
        'bar',
        salary.labels,
        salary.datasets
      );

      // Trend
      upsert_chart(
        'sd-chart-trend',
        'Saudization Trend (Monthly)',
        'line',
        trend.labels,
        trend.datasets
      );

      render_table_matrix(matrix.rows);
    }

    // initial
    // Pre-fill company if single company exists
    frappe.db.get_list('Company', {fields:['name'], limit: 2}).then(list => {
      if (list.length === 1) {
        page.fields_dict.company.set_value(list[0].name);
      }
    });
  }
};
