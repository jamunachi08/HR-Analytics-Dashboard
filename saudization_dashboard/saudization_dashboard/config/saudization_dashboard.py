from frappe import _


def get_data():
    return [
        {
            "label": _("Settings"),
            "items": [
                {"type": "doctype", "name": "Saudization Settings", "label": _("Saudization Settings")},
                {"type": "doctype", "name": "Saudization Policy", "label": _("Saudization Policy")},
            ],
        },
        {
            "label": _("Analytics"),
            "items": [
                {"type": "page", "name": "saudization-hr-analytics", "label": _("Saudization HR Analytics")},
                {"type": "report", "name": "Saudization KPI Summary", "doctype": "Employee"},
                {"type": "report", "name": "Saudization by Nationality Group", "doctype": "Employee"},
                {"type": "report", "name": "Saudization by Department", "doctype": "Employee"},
                {"type": "report", "name": "Saudization by Designation", "doctype": "Employee"},
            ],
        },
    ]
