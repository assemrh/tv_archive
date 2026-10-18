// Copyright (c) 2026, ORTAS IT Directorate and contributors
// For license information, please see license.txt

frappe.query_reports["Archive Work Progress"] = {
	filters: [
		{
			fieldname: "status",
			label: __("حالة الملف"),
			fieldtype: "Select",
			options: "\nمفتوح\nمغلق",
			default: "مفتوح",
		},
		{
			fieldname: "work_type",
			label: __("النوع"),
			fieldtype: "Select",
			options: "\nمسلسل\nبرنامج\nمادة",
		},
		{
			fieldname: "category",
			label: __("التصنيف"),
			fieldtype: "Link",
			options: "Archive Category",
		},
	],
};
