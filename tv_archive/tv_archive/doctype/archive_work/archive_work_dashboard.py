from frappe import _


def get_data():
	return {
		"fieldname": "work",
		"transactions": [
			{"label": _("تقارير الرقابة"), "items": ["Detailed Review Report", "General Review Report"]},
		],
	}
