// Copyright (c) 2026, ORTAS IT Directorate and contributors
// For license information, please see license.txt

frappe.ui.form.on("Archive Work", {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frm.doc.status === "مفتوح" && frappe.model.can_create("Detailed Review Report")) {
			frm.add_custom_button(__("تقرير حلقة جديد"), () => {
				frappe.new_doc("Detailed Review Report", { work: frm.doc.name });
			});
		}

		if (frm.doc.general_report) {
			frm.add_custom_button(__("التقرير العام"), () =>
				frappe.set_route("Form", "General Review Report", frm.doc.general_report)
			);
		} else if (frappe.model.can_create("General Review Report")) {
			frm.add_custom_button(__("بدء التقرير العام"), () => {
				frappe.new_doc("General Review Report", { work: frm.doc.name });
			});
		}

		frm.dashboard.add_indicator(
			__("{0} من {1} حلقة جاهزة للعرض", [frm.doc.ready_count || 0, frm.doc.episodes_count || 0]),
			frm.doc.progress >= 100 ? "green" : "orange"
		);
	},
});
