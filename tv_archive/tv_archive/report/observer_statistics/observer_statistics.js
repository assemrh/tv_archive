// Copyright (c) 2026, ORTAS IT Directorate and contributors
// For license information, please see license.txt

frappe.query_reports["Observer Statistics"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("من تاريخ"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("إلى تاريخ"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
		},
		{
			fieldname: "work",
			label: __("العمل"),
			fieldtype: "Link",
			options: "Archive Work",
		},
	],
};
