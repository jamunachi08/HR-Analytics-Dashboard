import frappe
from frappe import _


def _get_theme_doc():
    """Return Saudization Dashboard Theme singleton as dict (with safe defaults)."""
    defaults = {
        "enable_custom_theme": 0,
        "page_background": "#5b0d55",
        "panel_background": "#7a1b73",
        "card_background": "#6a1665",
        "border_color": "rgba(255,255,255,0.25)",
        "text_color": "#ffffff",
        "muted_text_color": "rgba(255,255,255,0.70)",
        "kpi_value_color": "#ffffff",
        "chart_palette": "#1E90FF,#22C55E,#F59E0B,#EF4444,#A855F7,#06B6D4,#F97316,#84CC16",
        "chart_height": 260,
        "tab_bg_color": "#6a1665",
        "tab_text_color": "rgba(255,255,255,0.85)",
        "tab_active_bg_color": "#1E90FF",
        "tab_active_text_color": "#ffffff",
    }

    try:
        doc = frappe.get_single("Saudization Dashboard Theme")
        out = defaults.copy()
        for k in out.keys():
            if hasattr(doc, k):
                out[k] = getattr(doc, k)
        return out
    except Exception:
        return defaults


@frappe.whitelist()
def get_theme():
    """Theme configuration for the dashboard page (v14+ compatible)."""
    return _get_theme_doc()


def _get_navigation_doc():
    """Return Saudization Dashboard Navigation singleton as dict (with safe defaults)."""
    defaults = {
        "enable_tabs": 1,
        "default_tab": "",
        "tabs": [
            {"tab_label": "Human Resources", "tab_type": "Filter Dashboard", "department": "", "company": "", "designation": "", "nationality_group": "", "route": "", "report_name": "", "open_in_new_window": 0, "order": 10},
            {"tab_label": "Research & Development", "tab_type": "Filter Dashboard", "department": "", "company": "", "designation": "", "nationality_group": "", "route": "", "report_name": "", "open_in_new_window": 0, "order": 20},
            {"tab_label": "Sales", "tab_type": "Filter Dashboard", "department": "", "company": "", "designation": "", "nationality_group": "", "route": "", "report_name": "", "open_in_new_window": 0, "order": 30},
        ],
    }

    try:
        doc = frappe.get_single("Saudization Dashboard Navigation")
        out = {"enable_tabs": int(getattr(doc, "enable_tabs", 1) or 0), "default_tab": getattr(doc, "default_tab", "") or "", "tabs": []}
        for row in (getattr(doc, "tabs", []) or []):
            out["tabs"].append({
                "tab_label": getattr(row, "tab_label", ""),
                "tab_type": getattr(row, "tab_type", "Filter Dashboard"),
                "route": getattr(row, "route", ""),
                "report_name": getattr(row, "report_name", ""),
                "company": getattr(row, "company", ""),
                "department": getattr(row, "department", ""),
                "designation": getattr(row, "designation", ""),
                "nationality_group": getattr(row, "nationality_group", ""),
                "open_in_new_window": int(getattr(row, "open_in_new_window", 0) or 0),
                "order": int(getattr(row, "order", 0) or 0),
            })
        out["tabs"].sort(key=lambda x: x.get("order", 0))
        return out
    except Exception:
        return defaults


@frappe.whitelist()
def get_navigation():
    """Navigation tabs configuration for the dashboard page (v14+ compatible)."""
    return _get_navigation_doc()


def _filters_to_where(filters):
    clauses = ["e.status='Active'"]
    params = {}

    company = filters.get('company')
    if not company:
        raise frappe.ValidationError(_("Company is required"))
    clauses.append("e.company=%(company)s")
    params['company'] = company

    for key, field in [
        ('department', 'department'),
        ('designation', 'designation'),
        ('nationality_group', 'saudization_nationality_group'),
    ]:
        val = filters.get(key)
        if val:
            clauses.append(f"e.{field}=%({key})s")
            params[key] = val

    return " AND ".join(clauses), params


def _latest_salary_cte():
    return """
    WITH latest_salary AS (
      SELECT ssa.employee, ssa.base
      FROM `tabSalary Structure Assignment` ssa
      INNER JOIN (
        SELECT employee, MAX(from_date) AS max_from_date
        FROM `tabSalary Structure Assignment`
        WHERE docstatus = 1
        GROUP BY employee
      ) x ON x.employee = ssa.employee AND x.max_from_date = ssa.from_date
      WHERE ssa.docstatus = 1
    )
    """


def _get_active_policy(company):
    # Returns dict with name and default_target_percent or None
    row = frappe.db.sql(
        """
        SELECT name, default_target_percent
        FROM `tabSaudization Policy`
        WHERE company=%s
          AND effective_from <= CURDATE()
          AND (effective_to IS NULL OR effective_to >= CURDATE())
        ORDER BY effective_from DESC
        LIMIT 1
        """,
        (company,),
        as_dict=True,
    )
    return row[0] if row else None


def _get_policy_lines(policy_name, dimension_type=None):
    if not policy_name:
        return []
    q = """
        SELECT dimension_type, department, designation, nationality_group, target_percent, IFNULL(min_headcount, 0) AS min_headcount
        FROM `tabSaudization Policy Line`
        WHERE parent=%s
    """
    params = [policy_name]
    if dimension_type:
        q += " AND dimension_type=%s"
        params.append(dimension_type)
    return frappe.db.sql(q, tuple(params), as_dict=True)


@frappe.whitelist()
def get_kpis(company, department=None, designation=None, nationality_group=None):
    where, params = _filters_to_where({
        'company': company,
        'department': department,
        'designation': designation,
        'nationality_group': nationality_group,
    })

    sql = _latest_salary_cte() + f"""
    SELECT
      COUNT(*) AS total_employees,
      SUM(CASE WHEN e.is_saudi = 1 THEN 1 ELSE 0 END) AS saudi_employees,
      SUM(CASE WHEN e.is_saudi = 0 THEN 1 ELSE 0 END) AS non_saudi_employees,
      ROUND(100 * SUM(CASE WHEN e.is_saudi = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0), 1) AS saudization_percent,

      ROUND(AVG(CASE WHEN e.is_saudi = 1 THEN ls.base END), 0) AS avg_salary_saudi,
      ROUND(AVG(CASE WHEN e.is_saudi = 0 THEN ls.base END), 0) AS avg_salary_non_saudi,

      ROUND(AVG(CASE WHEN e.is_saudi = 1 THEN TIMESTAMPDIFF(MONTH, e.date_of_joining, CURDATE()) END)/12, 1) AS avg_tenure_years_saudi,
      ROUND(AVG(CASE WHEN e.is_saudi = 0 THEN TIMESTAMPDIFF(MONTH, e.date_of_joining, CURDATE()) END)/12, 1) AS avg_tenure_years_non_saudi
    FROM `tabEmployee` e
    LEFT JOIN latest_salary ls ON ls.employee = e.name
    WHERE {where}
    """

    row = frappe.db.sql(sql, params, as_dict=True)[0]

    policy = _get_active_policy(company)
    row['target_percent'] = policy.get('default_target_percent') if policy else None
    row['variance_percent'] = (row['saudization_percent'] - row['target_percent']) if row.get('target_percent') is not None else None
    return row


@frappe.whitelist()
def get_nationality_group_breakdown(company, department=None, designation=None):
    where, params = _filters_to_where({
        'company': company,
        'department': department,
        'designation': designation,
        'nationality_group': None,
    })
    sql = f"""
    SELECT
      e.saudization_nationality_group AS label,
      COUNT(*) AS value
    FROM `tabEmployee` e
    WHERE {where}
    GROUP BY e.saudization_nationality_group
    ORDER BY value DESC
    """
    rows = frappe.db.sql(sql, params, as_dict=True)
    return rows


@frappe.whitelist()
def get_designation_saudization(company, department=None, min_headcount=3):
    where, params = _filters_to_where({
        'company': company,
        'department': department,
        'designation': None,
        'nationality_group': None,
    })
    params['min_headcount'] = int(min_headcount or 0)
    sql = f"""
    SELECT
      e.designation AS label,
      ROUND(100 * SUM(CASE WHEN e.is_saudi=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS value,
      COUNT(*) AS headcount
    FROM `tabEmployee` e
    WHERE {where}
    GROUP BY e.designation
    HAVING COUNT(*) >= %(min_headcount)s
    ORDER BY value ASC, headcount DESC
    LIMIT 15
    """
    return frappe.db.sql(sql, params, as_dict=True)


@frappe.whitelist()
def get_department_saudization(company, designation=None):
    where, params = _filters_to_where({
        'company': company,
        'department': None,
        'designation': designation,
        'nationality_group': None,
    })
    sql = f"""
    SELECT
      e.department AS label,
      SUM(CASE WHEN e.is_saudi=1 THEN 1 ELSE 0 END) AS saudi_count,
      SUM(CASE WHEN e.is_saudi=0 THEN 1 ELSE 0 END) AS non_saudi_count,
      ROUND(100 * SUM(CASE WHEN e.is_saudi=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS saudization_percent,
      COUNT(*) AS headcount
    FROM `tabEmployee` e
    WHERE {where}
    GROUP BY e.department
    ORDER BY saudization_percent ASC, headcount DESC
    LIMIT 20
    """
    return frappe.db.sql(sql, params, as_dict=True)


@frappe.whitelist()
def get_salary_band_saudization(company, department=None, designation=None):
    where, params = _filters_to_where({
        'company': company,
        'department': department,
        'designation': designation,
        'nationality_group': None,
    })
    sql = _latest_salary_cte() + f"""
    WITH emp AS (
      SELECT e.name, e.is_saudi, IFNULL(ls.base,0) AS base
      FROM `tabEmployee` e
      LEFT JOIN latest_salary ls ON ls.employee = e.name
      WHERE {where}
    )
    SELECT
      CASE
        WHEN base <= 5000 THEN 'Up to 5k'
        WHEN base <= 10000 THEN '5k-10k'
        WHEN base <= 15000 THEN '10k-15k'
        ELSE '15k+'
      END AS label,
      ROUND(100 * SUM(CASE WHEN is_saudi=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS value,
      COUNT(*) AS headcount
    FROM emp
    GROUP BY label
    ORDER BY FIELD(label,'Up to 5k','5k-10k','10k-15k','15k+')
    """
    return frappe.db.sql(sql, params, as_dict=True)


@frappe.whitelist()
def get_trend(company, department=None, designation=None, months_back=24):
    where, params = _filters_to_where({
        'company': company,
        'department': department,
        'designation': designation,
        'nationality_group': None,
    })
    params['months_back'] = int(months_back or 24)
    sql = f"""
    SELECT
      DATE_FORMAT(e.date_of_joining, '%Y-%m-01') AS label,
      ROUND(100 * SUM(CASE WHEN e.is_saudi=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS value,
      COUNT(*) AS hires_count
    FROM `tabEmployee` e
    WHERE {where}
      AND e.date_of_joining IS NOT NULL
      AND e.date_of_joining >= DATE_SUB(CURDATE(), INTERVAL %(months_back)s MONTH)
    GROUP BY label
    ORDER BY label
    """
    return frappe.db.sql(sql, params, as_dict=True)


@frappe.whitelist()
def get_department_compliance(company, min_headcount=3):
    # Actual vs targets by department (policy line overrides default target)
    min_headcount = int(min_headcount or 0)

    policy = _get_active_policy(company)
    default_target = policy.get('default_target_percent') if policy else None
    policy_name = policy.get('name') if policy else None
    line_targets = _get_policy_lines(policy_name, dimension_type='Department')
    target_by_dept = {l.get('department'): l.get('target_percent') for l in line_targets if l.get('department')}
    min_by_dept = {l.get('department'): int(l.get('min_headcount') or 0) for l in line_targets if l.get('department')}

    rows = frappe.db.sql(
        """
        SELECT
          e.department AS department,
          COUNT(*) AS headcount,
          ROUND(100 * SUM(CASE WHEN e.is_saudi=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS actual_percent
        FROM `tabEmployee` e
        WHERE e.status='Active' AND e.company=%s
        GROUP BY e.department
        ORDER BY actual_percent ASC, headcount DESC
        """,
        (company,),
        as_dict=True,
    )

    out = []
    for r in rows:
        dept = r.get('department')
        hc = int(r.get('headcount') or 0)
        effective_min = max(min_headcount, min_by_dept.get(dept, 0))
        if hc < effective_min:
            continue
        target = target_by_dept.get(dept, default_target)
        variance = (r['actual_percent'] - target) if target is not None else None
        status = None
        if target is not None:
            if r['actual_percent'] >= target:
                status = 'Compliant'
            elif r['actual_percent'] >= target - 10:
                status = 'Near'
            else:
                status = 'Below'
        out.append({
            'department': dept,
            'headcount': hc,
            'actual_percent': r['actual_percent'],
            'target_percent': target,
            'variance_percent': variance,
            'status': status,
        })

    return out


@frappe.whitelist()
def get_matrix(company, min_headcount=3):
    min_headcount = int(min_headcount or 0)
    rows = frappe.db.sql(
        """
        SELECT
          e.department AS department,
          e.designation AS designation,
          COUNT(*) AS headcount,
          ROUND(100 * SUM(CASE WHEN e.is_saudi=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS saudization_percent
        FROM `tabEmployee` e
        WHERE e.status='Active' AND e.company=%s
        GROUP BY e.department, e.designation
        HAVING COUNT(*) >= %s
        ORDER BY e.department, saudization_percent ASC
        """,
        (company, min_headcount),
        as_dict=True,
    )
    return rows


# --------------------------
# Dashboard-friendly wrappers
# (Keeps JS stable across versions)
# --------------------------


def _rows_to_chart(rows, series_name="Value", value_key="value", label_key="label"):
    labels = [r.get(label_key) for r in rows]
    values = [r.get(value_key) for r in rows]
    return {
        "labels": labels,
        "datasets": [{"name": series_name, "values": values}],
    }


@frappe.whitelist()
def get_actual_vs_target_overall(company, department=None, designation=None, nationality_group=None):
    # Reuse KPI function to compute actual; compare with active policy
    k = get_kpis(company, department=department, designation=designation, nationality_group=nationality_group)
    labels = ["Saudization %"]
    datasets = [
        {"name": "Actual", "values": [k.get("saudization_percent") or 0]},
        {"name": "Target", "values": [k.get("target_percent") or 0]},
    ]
    return {"labels": labels, "datasets": datasets, "variance_percent": k.get("variance_percent")}


@frappe.whitelist()
def get_saudization_by_designation(company, department=None, min_headcount=3):
    rows = get_designation_saudization(company, department=department, min_headcount=min_headcount)
    return _rows_to_chart(rows, series_name="Saudization %")


@frappe.whitelist()
def get_saudization_by_department(company, designation=None):
    rows = get_department_saudization(company, designation=designation)
    # stacked bar: saudi and non-saudi counts
    labels = [r.get("label") for r in rows]
    saudi = [r.get("saudi_count") for r in rows]
    non_saudi = [r.get("non_saudi_count") for r in rows]
    return {
        "labels": labels,
        "datasets": [
            {"name": "Saudi", "values": saudi},
            {"name": "Non-Saudi", "values": non_saudi},
        ],
    }


@frappe.whitelist()
def get_saudization_by_salary_band(company, department=None, designation=None):
    rows = get_salary_band_saudization(company, department=department, designation=designation)
    return _rows_to_chart(rows, series_name="Saudization %")


@frappe.whitelist()
def get_saudization_trend(company, department=None, designation=None, months_back=24):
    rows = get_trend(company, department=department, designation=designation, months_back=months_back)
    return _rows_to_chart(rows, series_name="Saudization %")


@frappe.whitelist()
def get_matrix_with_targets(company, min_headcount=3):
    # Returns rows with target and variance (Department+Designation overrides)
    base_rows = get_matrix(company, min_headcount=min_headcount)
    policy = _get_active_policy(company)
    default_target = policy.get("default_target_percent") if policy else None

    lines = _get_policy_lines(policy.get("name") if policy else None)
    # Build lookup precedence: Dept+Designation > Designation > Department > Overall(default)
    dept_desig = {}
    desig = {}
    dept = {}
    for l in lines:
        dt = l.get("dimension_type")
        if dt == "Department+Designation" and l.get("department") and l.get("designation"):
            dept_desig[(l["department"], l["designation"])] = l.get("target_percent")
        elif dt == "Designation" and l.get("designation"):
            desig[l["designation"]] = l.get("target_percent")
        elif dt == "Department" and l.get("department"):
            dept[l["department"]] = l.get("target_percent")

    out = []
    for r in base_rows:
        d = r.get("department")
        g = r.get("designation")
        t = None
        if d and g and (d, g) in dept_desig:
            t = dept_desig[(d, g)]
        elif g and g in desig:
            t = desig[g]
        elif d and d in dept:
            t = dept[d]
        else:
            t = default_target
        v = (r.get("saudization_percent") - t) if (t is not None and r.get("saudization_percent") is not None) else None
        out.append({
            **r,
            "target_percent": t,
            "variance_percent": v,
        })
    return out
