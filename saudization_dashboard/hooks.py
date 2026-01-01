app_name = "saudization_dashboard"
app_title = "Saudization Dashboard"
app_publisher = "Your Company"
app_description = "KSA Saudization HR analytics dashboard for ERPNext"
app_email = ""
app_license = "MIT"

# Load fixtures for Custom Fields, Server Scripts, Reports, and the Desk Page
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["name", "in", [
            "Employee-is_saudi",
            "Employee-saudization_nationality_group",
        ]]]
    },
    {
        "dt": "Server Script",
        "filters": [["name", "in", [
            "Derive Saudization Group from Nationality (Employee)",
        ]]]
    },
    {
        "dt": "Report",
        "filters": [["name", "in", [
            "Saudization KPI Summary",
            "Saudization by Nationality Group",
            "Saudization Actual vs Target (Overall)",
            "Saudization by Designation",
            "Saudization by Department",
            "Saudization by Salary Band",
            "Saudization Trend (Monthly Snapshot by DOJ)",
            "Saudization Matrix (Dept x Designation)",
            "Saudization Compliance vs Target by Department",
        ]]]
    },]

# After install, backfill derived fields for existing employees
after_install = "saudization_dashboard.patches.backfill_employee_saudization.execute"
