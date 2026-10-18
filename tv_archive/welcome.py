# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

"""Data for the welcome page (page: archive-welcome).

Each user sees the work waiting for them according to their role. Every card carries
the list filters it was counted with, so clicking it opens exactly those records.
"""

import frappe
from frappe import _
from frappe.utils import get_first_day, nowdate

from tv_archive.constants import (
	ARCHIVE_ROLES,
	ARCHIVE_WORK,
	DETAILED_REPORT,
	GENERAL_REPORT,
	ROLE_COORDINATOR,
	ROLE_DIRECTOR,
	ROLE_MONITOR,
	ROLE_OBSERVER,
	ROLE_SYSTEM_MANAGER,
	WORK_CLOSED,
	WORK_OPEN,
	DRState,
	GRState,
)
from tv_archive.utils import user_roles


def card(label, doctype, filters, hint=None, tone="default"):
	return {
		"label": label,
		"doctype": doctype,
		"filters": filters,
		"count": frappe.db.count(doctype, filters),
		"hint": hint,
		"tone": tone,
	}


def observer_cards(user, month_start):
	return [
		card(
			_("أُعيدت إليك للتعديل"),
			DETAILED_REPORT,
			{"observer": user, "workflow_state": DRState.DRAFT, "return_reason": ["is", "set"]},
			_("اقرأ سبب الإعادة في أعلى التقرير، عدّل ثم أرسل من جديد."),
			"warning",
		),
		card(
			_("مسوداتك"),
			DETAILED_REPORT,
			{"observer": user, "workflow_state": DRState.DRAFT},
			_("تقارير لم تُرسل بعد إلى المنسق."),
		),
		card(
			_("أرسلتها وهي قيد المتابعة"),
			DETAILED_REPORT,
			{"observer": user, "workflow_state": ["in", [DRState.PENDING, DRState.REVIEW]]},
			_("لدى المنسق أو المونيتور. لا تحتاج إجراءً منك."),
			"info",
		),
		card(
			_("جاهزة للعرض هذا الشهر"),
			DETAILED_REPORT,
			{"observer": user, "docstatus": 1, "completed_on": [">=", month_start]},
			tone="success",
		),
		card(
			_("تقاريرك العامة المفتوحة"),
			GENERAL_REPORT,
			{"observer": user, "workflow_state": GRState.DRAFT},
			_("تُعبّأ تدريجياً وتُرسل بعد اكتمال الحلقات."),
		),
	]


def coordinator_cards(month_start):
	return [
		card(
			_("بانتظار تحديد المونيتور"),
			DETAILED_REPORT,
			{"workflow_state": DRState.PENDING},
			_("افتح التقرير واضغط «تكليف مونيتور»."),
			"warning",
		),
		card(
			_("قيد المراجعة لدى المونيتورز"),
			DETAILED_REPORT,
			{"workflow_state": DRState.REVIEW},
			_("يمكنك إعادة التكليف من داخل التقرير."),
			"info",
		),
		card(
			_("تقارير عامة بانتظار الاعتماد"),
			GENERAL_REPORT,
			{"workflow_state": GRState.PENDING},
			_("الاعتماد يغلق ملف العمل."),
			"warning",
		),
		card(
			_("حلقات جاهزة للعرض هذا الشهر"),
			DETAILED_REPORT,
			{"docstatus": 1, "completed_on": [">=", month_start]},
			tone="success",
		),
		card(_("أعمال مفتوحة"), ARCHIVE_WORK, {"status": WORK_OPEN}),
	]


def monitor_cards(user, month_start):
	return [
		card(
			_("مهامك المفتوحة"),
			DETAILED_REPORT,
			{"monitor": user, "workflow_state": DRState.REVIEW},
			_("نفّذ الملاحظات، ثم اضغط «تمت المراجعة» داخل التقرير."),
			"warning",
		),
		card(
			_("أنجزتها هذا الشهر"),
			DETAILED_REPORT,
			{"monitor": user, "docstatus": 1, "completed_on": [">=", month_start]},
			tone="success",
		),
	]


def director_cards(month_start):
	return [
		card(
			_("حلقات جاهزة للعرض هذا الشهر"),
			DETAILED_REPORT,
			{"docstatus": 1, "completed_on": [">=", month_start]},
			tone="success",
		),
		card(
			_("حلقات قيد المتابعة"),
			DETAILED_REPORT,
			{"workflow_state": ["in", [DRState.PENDING, DRState.REVIEW]]},
			tone="info",
		),
		card(_("أعمال مفتوحة"), ARCHIVE_WORK, {"status": WORK_OPEN}),
		card(_("أعمال مغلقة ومؤرشفة"), ARCHIVE_WORK, {"status": WORK_CLOSED}),
	]


def setup_checklist():
	"""What the administrator still has to do before people can use the system."""
	items = []
	role_labels = {
		ROLE_OBSERVER: _("أضف مراقباً واحداً على الأقل"),
		ROLE_COORDINATOR: _("أضف المنسق / رئيس شعبة المراقبة"),
		ROLE_MONITOR: _("أضف المونيتورز"),
		ROLE_DIRECTOR: _("أضف مدير المديرية (اطلاع)"),
	}
	for role, label in role_labels.items():
		count = len(
			frappe.get_all(
				"Has Role",
				filters={
					"role": role,
					"parenttype": "User",
					"parent": ["not in", ["Administrator", "Guest"]],
				},
				pluck="parent",
				distinct=True,
			)
		)
		items.append(
			{
				"label": label,
				"done": count > 0,
				"detail": _("{0} مستخدم").format(count),
				"route": ["List", "User"],
			}
		)

	items.append(
		{
			"label": _("اضبط بريد الإرسال لتصل الإشعارات بالبريد أيضاً (اختياري)"),
			"done": bool(frappe.db.exists("Email Account", {"enable_outgoing": 1})),
			"detail": "",
			"route": ["List", "Email Account"],
		}
	)
	items.append(
		{
			"label": _("راجع تصنيفات الأعمال وأنواع الحفظ"),
			"done": bool(frappe.db.count("Archive Category")),
			"detail": _("{0} تصنيف").format(frappe.db.count("Archive Category")),
			"route": ["List", "Archive Category"],
		}
	)
	return items


@frappe.whitelist()
def get_welcome_data() -> dict:
	user = frappe.session.user
	roles = user_roles(user)
	is_admin = user == "Administrator" or ROLE_SYSTEM_MANAGER in roles
	# Administrator holds every role; show the coordinator's view rather than all four.
	archive_roles = (
		[ROLE_COORDINATOR] if user == "Administrator" else [r for r in ARCHIVE_ROLES if r in roles]
	)
	month_start = get_first_day(nowdate())

	sections = []
	if ROLE_COORDINATOR in archive_roles:
		sections.append(
			{"role": ROLE_COORDINATOR, "title": _("بانتظارك كمنسق"), "cards": coordinator_cards(month_start)}
		)
	if ROLE_OBSERVER in archive_roles:
		sections.append(
			{"role": ROLE_OBSERVER, "title": _("تقاريرك كمراقب"), "cards": observer_cards(user, month_start)}
		)
	if ROLE_MONITOR in archive_roles:
		sections.append(
			{"role": ROLE_MONITOR, "title": _("مهامك كمونيتور"), "cards": monitor_cards(user, month_start)}
		)
	if ROLE_DIRECTOR in archive_roles and ROLE_COORDINATOR not in archive_roles:
		sections.append(
			{"role": ROLE_DIRECTOR, "title": _("نظرة عامة"), "cards": director_cards(month_start)}
		)

	recent = []
	if frappe.has_permission(DETAILED_REPORT, "read"):
		recent = frappe.get_list(
			DETAILED_REPORT,
			fields=["name", "title", "workflow_state", "modified"],
			order_by="modified desc",
			limit_page_length=6,
		)

	return {
		"full_name": frappe.utils.get_fullname(user),
		"roles": archive_roles,
		"is_admin": is_admin,
		"sections": sections,
		"recent": recent,
		"setup": setup_checklist() if is_admin else [],
	}
