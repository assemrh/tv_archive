// Copyright (c) 2026, ORTAS IT Directorate and contributors
// For license information, please see license.txt

const DRR_METHOD = "tv_archive.tv_archive.doctype.detailed_review_report.detailed_review_report";
const DRR_STATE = {
	DRAFT: "مسودة",
	PENDING: "بانتظار تحديد المونيتور",
	REVIEW: "قيد المراجعة من قبل المونيتور",
};
const SEASON_ORDINALS = [
	"الأول", "الثاني", "الثالث", "الرابع", "الخامس",
	"السادس", "السابع", "الثامن", "التاسع", "العاشر",
];

const is_archive_manager = () => frappe.user.has_role(["Archive Coordinator", "System Manager"]);
const user_query = (role) => ({ query: "tv_archive.api.users_with_role", filters: { role } });

frappe.ui.form.on("Detailed Review Report", {
	setup(frm) {
		frm.set_query("work", () => ({ filters: { status: "مفتوح" } }));
		frm.set_query("observer", () => user_query("Archive Observer"));
		frm.set_query("monitor", () => user_query("Archive Monitor"));
	},

	refresh(frm) {
		if (frm.is_new() || frm.is_dirty()) return;
		const state = frm.doc.workflow_state;

		if (state === DRR_STATE.PENDING && is_archive_manager()) {
			frm.add_custom_button(__("تكليف مونيتور"), () => assign_monitor_dialog(frm)).addClass("btn-primary");
			frm.add_custom_button(__("إعادة للمراقب"), () => return_dialog(frm));
		}

		if (state === DRR_STATE.REVIEW) {
			if (frm.doc.monitor === frappe.session.user || is_archive_manager()) {
				frm.add_custom_button(__("تمت المراجعة · نقل إلى جاهزة للعرض"), () => complete_dialog(frm)).addClass(
					"btn-primary"
				);
			}
			if (is_archive_manager()) {
				frm.add_custom_button(__("إعادة تكليف"), () => assign_monitor_dialog(frm));
			}
		}

		if (frm.doc.return_reason && state === DRR_STATE.DRAFT) {
			frm.dashboard.set_headline_alert(
				`<b>${__("أُعيد التقرير للتعديل")}:</b> ${frappe.utils.escape_html(frm.doc.return_reason)}`,
				"orange"
			);
		}
	},

	season_no: set_episode_label,
	episode_no: set_episode_label,
});

function set_episode_label(frm) {
	if (!frm.doc.episode_no) return;
	const season = cint(frm.doc.season_no) || 1;
	const season_text = SEASON_ORDINALS[season - 1] || season;
	frm.set_value("episode_label", `الجزء ${season_text} الحلقة ${cint(frm.doc.episode_no)}`);
}

function report_summary_html(frm) {
	const notes = frm.doc.notes
		? `<div class="text-muted">${__("الملاحظات")}: ${frappe.utils.escape_html(frm.doc.notes)}</div>`
		: "";
	return `<div class="mb-2"><b>${frappe.utils.escape_html(frm.doc.title)}</b>
		<div>${__("نتيجة المراقبة")}: ${frappe.utils.escape_html(frm.doc.review_result || "")}</div>${notes}</div>`;
}

function run_action(frm, method, args, dialog, message) {
	frappe
		.call({ method: `${DRR_METHOD}.${method}`, args: { name: frm.doc.name, ...args }, freeze: true })
		.then(() => {
			dialog.hide();
			frm.reload_doc();
			frappe.show_alert({ message, indicator: "green" });
		});
}

function assign_monitor_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("تكليف مونيتور"),
		fields: [
			{ fieldtype: "HTML", fieldname: "summary", options: report_summary_html(frm) },
			{
				fieldtype: "Link",
				fieldname: "monitor",
				label: __("المونيتور المسؤول"),
				options: "User",
				reqd: 1,
				default: frm.doc.monitor,
				get_query: () => user_query("Archive Monitor"),
				description: __("يظهر بجانب كل اسم عدد المهام المفتوحة لديه."),
			},
			{
				fieldtype: "Small Text",
				fieldname: "instructions",
				label: __("تعليمات للمونيتور"),
				default: frm.doc.coordinator_instructions,
			},
		],
		primary_action_label: __("تأكيد التكليف"),
		primary_action: (values) =>
			run_action(frm, "assign_monitor", values, dialog, __("تم تكليف المونيتور وإشعاره")),
	});
	dialog.show();
}

function return_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("إعادة التقرير للمراقب"),
		fields: [
			{ fieldtype: "HTML", fieldname: "summary", options: report_summary_html(frm) },
			{ fieldtype: "Small Text", fieldname: "reason", label: __("سبب الإعادة"), reqd: 1 },
		],
		primary_action_label: __("إعادة"),
		primary_action: (values) =>
			run_action(frm, "return_to_observer", values, dialog, __("أُعيد التقرير للمراقب")),
	});
	dialog.show();
}

function complete_dialog(frm) {
	const dialog = new frappe.ui.Dialog({
		title: __("إنهاء المراجعة"),
		fields: [
			{ fieldtype: "HTML", fieldname: "summary", options: report_summary_html(frm) },
			{
				fieldtype: "Small Text",
				fieldname: "note",
				label: __("ملاحظة الإنجاز"),
				default: frm.doc.completion_note,
				description: __("مثال: تم الحذف ونقل الملف إلى مجلد جاهزة للعرض."),
			},
		],
		primary_action_label: __("تمت المراجعة"),
		primary_action: (values) =>
			run_action(frm, "complete_review", values, dialog, __("الحلقة جاهزة للعرض")),
	});
	dialog.show();
}
