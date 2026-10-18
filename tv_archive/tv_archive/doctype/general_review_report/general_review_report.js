// Copyright (c) 2026, ORTAS IT Directorate and contributors
// For license information, please see license.txt

frappe.ui.form.on("General Review Report", {
	setup(frm) {
		frm.set_query("work", () => ({ filters: { status: "مفتوح" } }));
		frm.set_query("observer", () => ({
			query: "tv_archive.api.users_with_role",
			filters: { role: "Archive Observer" },
		}));
	},

	refresh(frm) {
		if (frm.is_new()) return;

		const ready = frm.doc.ready_episodes || 0;
		const total = frm.doc.episodes_count || 0;
		frm.dashboard.add_indicator(
			__("الحلقات الجاهزة للعرض: {0} من {1}", [ready, total]),
			total && ready >= total ? "green" : "orange"
		);

		if (frm.doc.return_reason && frm.doc.workflow_state === "مسودة") {
			frm.dashboard.set_headline_alert(
				`<b>${__("أُعيد التقرير للتعديل")}:</b> ${frappe.utils.escape_html(frm.doc.return_reason)}`,
				"orange"
			);
		}

		const can_return = frappe.user.has_role(["Archive Coordinator", "System Manager"]);
		if (frm.doc.workflow_state === "بانتظار الاعتماد" && can_return && !frm.is_dirty()) {
			frm.add_custom_button(__("إعادة للمراقب"), () => {
				frappe.prompt(
					{ fieldtype: "Small Text", fieldname: "reason", label: __("سبب الإعادة"), reqd: 1 },
					({ reason }) =>
						frappe
							.call({
								method: "tv_archive.tv_archive.doctype.general_review_report.general_review_report.return_to_observer",
								args: { name: frm.doc.name, reason },
								freeze: true,
							})
							.then(() => frm.reload_doc()),
					__("إعادة التقرير العام للمراقب"),
					__("إعادة")
				);
			});
		}
	},

	intro_duration: update_titles_total,
	outro_duration: update_titles_total,
});

function update_titles_total(frm) {
	frm.set_value("titles_total", (frm.doc.intro_duration || 0) + (frm.doc.outro_duration || 0));
}
