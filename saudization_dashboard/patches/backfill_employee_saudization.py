import frappe


def _ensure_singleton(doctype, values=None):
    """Create singleton doc if missing."""
    try:
        frappe.get_single(doctype)
        return
    except Exception:
        doc = frappe.get_doc({"doctype": doctype})
        for k, v in (values or {}).items():
            setattr(doc, k, v)
        doc.flags.ignore_permissions = True
        doc.insert()


def execute():
    # Ensure singleton configuration doctypes exist (theme / settings / navigation)
    _ensure_singleton("Saudization Dashboard Theme")
    _ensure_singleton("Saudization Settings")
    _ensure_singleton("Saudization Dashboard Navigation", {
        "enable_tabs": 1,
        "tabs": [
            {"tab_label": "Human Resources", "tab_type": "Filter Dashboard", "order": 10},
            {"tab_label": "Research & Development", "tab_type": "Filter Dashboard", "order": 20},
            {"tab_label": "Sales", "tab_type": "Filter Dashboard", "order": 30}
        ]
    })

    # Trigger Employee before_save to compute derived fields for active employees
    if not frappe.db.table_exists("tabEmployee"):
        return

    employee_names = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
    for name in employee_names:
        try:
            doc = frappe.get_doc("Employee", name)
            # save will run before_save server script; ignore perms during install
            doc.flags.ignore_permissions = True
            doc.save()
        except Exception:
            # Do not fail installation due to one bad record
            frappe.log_error(frappe.get_traceback(), f"Saudization backfill failed for Employee {name}")

    frappe.db.commit()
