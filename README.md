# Saudization Dashboard (ERPNext / Frappe App)

This app adds:
- Saudization Policy + Policy Lines doctypes (targets by overall/department/designation combinations)
- Saudization Settings doctype (Saudi nationality + GCC nationalities)
- Employee derived fields: `is_saudi` and `saudization_nationality_group` (Saudi/GCC/Non-GCC/Unknown)
- Server Script to derive these from `Employee.nationality`
- Query Reports and Dashboard (charts + KPI number cards)

## Install

1. Get the app into your bench:

```bash
cd ~/frappe-bench
bench get-app /path/to/saudization_dashboard
```

2. Install on the site:

```bash
bench --site <yoursite> install-app saudization_dashboard
```

3. (Optional) Rebuild assets:

```bash
bench build
bench restart
```

## Usage

- Configure **Saudization Settings** (Saudi nationality and GCC list).
- Create **Saudization Policy** (default target %) and add policy lines for department/designation if required.
- Open Dashboard: **Saudization HR Analytics**.

Notes:
- Reports use `Salary Structure Assignment.base` as current base salary.
- If you use a different payroll model, update the SQL in reports accordingly.
# cloud-redeploy
