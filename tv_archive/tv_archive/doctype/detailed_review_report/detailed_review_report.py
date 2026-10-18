# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

"""Detailed review report: one per episode (ARC-REQ-01, ARC-REQ-02).

Lifecycle (driven by the "Detailed Review Report" workflow, see setup/install.py):

    مسودة → بانتظار تحديد المونيتور → قيد المراجعة من قبل المونيتور → الحلقة جاهزة للعرض (submitted)
                    ↘ إعادة للمراقب (back to مسودة)
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.workflow import apply_workflow
from frappe.utils import cint, now_datetime

from tv_archive import notifications
from tv_archive.constants import (
	ARCHIVE_WORK,
	DETAILED_REPORT,
	RESULT_NEEDS_EDIT,
	ROLE_COORDINATOR,
	ROLE_MONITOR,
	ROLE_OBSERVER,
	WORK_CLOSED,
	Action,
	DRState,
)
from tv_archive.utils import (
	changed_fields,
	ensure_user_has_role,
	is_manager,
	state_changed,
	update_work_progress,
	user_roles,
)

# Set by the system during transitions, never by hand.
SYSTEM_FIELDS = frozenset(
	{
		"workflow_state",
		"assigned_by",
		"assigned_on",
		"completed_by",
		"completed_on",
		"return_reason",
		"title",
		"work_title",
		"amended_from",
	}
)
# What the assigned monitor may change while the episode is under review.
MONITOR_EDITABLE = frozenset({"completion_note"})
# What an observer may never change, even in draft.
OBSERVER_FORBIDDEN = frozenset({"monitor", "coordinator_instructions", "completion_note"})

SEASON_ORDINALS = (
	"الأول",
	"الثاني",
	"الثالث",
	"الرابع",
	"الخامس",
	"السادس",
	"السابع",
	"الثامن",
	"التاسع",
	"العاشر",
)


def make_episode_label(season_no, episode_no) -> str:
	"""Format the episode as written on the paper form, e.g. «الجزء الثاني الحلقة 4»."""
	season = cint(season_no) or 1
	season_text = SEASON_ORDINALS[season - 1] if season <= len(SEASON_ORDINALS) else str(season)
	return f"الجزء {season_text} الحلقة {cint(episode_no)}"


class DetailedReviewReport(Document):
	def validate(self):
		if not cint(self.season_no):
			self.season_no = 1
		if not self.episode_label:
			self.episode_label = make_episode_label(self.season_no, self.episode_no)
		self.title = f"{self.work_title or self.work} - {self.episode_label}"

		self.validate_work_is_open()
		self.validate_unique_episode()
		self.validate_notes()
		self.validate_observer()
		self.validate_edit_rights()
		self.apply_state_change()

	def validate_work_is_open(self):
		if not (self.is_new() or self.has_value_changed("work")):
			return
		if frappe.db.get_value(ARCHIVE_WORK, self.work, "status") == WORK_CLOSED:
			frappe.throw(
				_("ملف العمل {0} مغلق، ولا يمكن إضافة حلقات إليه.").format(frappe.bold(self.work_title))
			)

	def validate_unique_episode(self):
		duplicate = frappe.db.get_value(
			DETAILED_REPORT,
			{
				"work": self.work,
				"season_no": cint(self.season_no),
				"episode_no": cint(self.episode_no),
				"docstatus": ("<", 2),
				"name": ("!=", self.name),
			},
		)
		if duplicate:
			frappe.throw(
				_("يوجد تقرير لهذه الحلقة مسبقاً: {0}").format(
					frappe.utils.get_link_to_form(DETAILED_REPORT, duplicate)
				)
			)

	def validate_notes(self):
		if self.review_result == RESULT_NEEDS_EDIT and not (self.notes or "").strip():
			frappe.throw(_("الملاحظات إجبارية عندما تكون نتيجة المراقبة «تحتاج تعديلات»."))

	def validate_observer(self):
		if not (self.is_new() or self.has_value_changed("observer")):
			return
		if not user_roles(self.observer) & {ROLE_OBSERVER, ROLE_COORDINATOR}:
			frappe.throw(
				_("المستخدم {0} ليس من موظفي المراقبة.").format(frappe.bold(self.observer)),
				title=_("اسم المراقب"),
			)

	def validate_edit_rights(self):
		"""FSD: the observer edits only drafts; the monitor only adds the completion note."""
		if self.is_new() or is_manager():
			return
		before = self.get_doc_before_save()
		changed = changed_fields(self) - SYSTEM_FIELDS
		if not before or not changed:
			return

		user = frappe.session.user
		if before.workflow_state == DRState.DRAFT and user in (before.observer, before.owner):
			if not changed & OBSERVER_FORBIDDEN:
				return
		elif (
			before.workflow_state == DRState.REVIEW and before.monitor == user and changed <= MONITOR_EDITABLE
		):
			return

		frappe.throw(
			_("لا يمكنك تعديل هذا التقرير وهو في حالة «{0}».").format(before.workflow_state),
			frappe.PermissionError,
		)

	def apply_state_change(self):
		old, new = state_changed(self)
		if old == new:
			if new == DRState.REVIEW and self.has_value_changed("monitor"):
				# Coordinator re-assigned the episode to another monitor.
				self.set_assignment()
				self.flags.monitor_reassigned = True
			return

		if new == DRState.PENDING:
			self.return_reason = None
		elif new == DRState.REVIEW:
			self.set_assignment()
		elif new == DRState.DRAFT and old == DRState.PENDING:
			if not (self.return_reason or "").strip():
				frappe.throw(_("اكتب سبب إعادة التقرير للمراقب."))
		elif new == DRState.READY:
			self.completed_by = frappe.session.user
			self.completed_on = now_datetime()

	def set_assignment(self):
		ensure_user_has_role(self.monitor, ROLE_MONITOR, _("المونيتور المسؤول"))
		self.assigned_by = frappe.session.user
		self.assigned_on = now_datetime()

	def on_update(self):
		old, new = state_changed(self)
		if old != new:
			if new == DRState.PENDING:
				notifications.notify_detailed_sent(self)
			elif new == DRState.REVIEW:
				notifications.notify_monitor_assigned(self)
			elif new == DRState.READY:
				notifications.notify_episode_ready(self)
			elif new == DRState.DRAFT and old == DRState.PENDING:
				notifications.notify_returned(self, notifications.episode_ref(self))
		elif self.flags.monitor_reassigned:
			notifications.notify_monitor_assigned(self)

		update_work_progress(self.work)
		before = self.get_doc_before_save()
		if before and before.work != self.work:
			update_work_progress(before.work)

	def on_cancel(self):
		update_work_progress(self.work)

	def on_trash(self):
		if not is_manager() and self.workflow_state != DRState.DRAFT:
			frappe.throw(
				_("يمكن للمراقب حذف التقرير وهو مسودة فقط. تواصل مع المنسق / رئيس الشعبة."),
				frappe.PermissionError,
			)

	def after_delete(self):
		update_work_progress(self.work)


def _get_report(name: str, expected_state: str) -> DetailedReviewReport:
	doc = frappe.get_doc(DETAILED_REPORT, name)
	if doc.workflow_state != expected_state:
		frappe.throw(_("التقرير في حالة «{0}»، ولا يمكن تنفيذ هذا الإجراء.").format(doc.workflow_state))
	return doc


def _require_manager():
	if not is_manager():
		frappe.throw(_("هذا الإجراء من صلاحية المنسق / رئيس شعبة المراقبة."), frappe.PermissionError)


@frappe.whitelist()
def assign_monitor(name: str, monitor: str, instructions: str | None = None) -> str:
	"""ARC-REQ-03: coordinator picks the monitor. Also used to re-assign during review."""
	_require_manager()
	doc = frappe.get_doc(DETAILED_REPORT, name)
	if doc.workflow_state not in (DRState.PENDING, DRState.REVIEW):
		frappe.throw(_("لا يمكن تكليف مونيتور والتقرير في حالة «{0}».").format(doc.workflow_state))
	ensure_user_has_role(monitor, ROLE_MONITOR, _("المونيتور المسؤول"))

	doc.monitor = monitor
	doc.coordinator_instructions = instructions
	doc.save()
	if doc.workflow_state == DRState.PENDING:
		apply_workflow(doc.as_dict(), Action.ASSIGN_MONITOR)
	return doc.name


@frappe.whitelist()
def return_to_observer(name: str, reason: str) -> str:
	_require_manager()
	if not (reason or "").strip():
		frappe.throw(_("اكتب سبب إعادة التقرير للمراقب."))
	doc = _get_report(name, DRState.PENDING)
	doc.return_reason = reason
	doc.save()
	apply_workflow(doc.as_dict(), Action.RETURN_TO_OBSERVER)
	return doc.name


@frappe.whitelist()
def complete_review(name: str, note: str | None = None) -> str:
	"""ARC-REQ-06: the monitor finishes the edits and moves the episode to «جاهزة للعرض»."""
	doc = _get_report(name, DRState.REVIEW)
	if doc.monitor != frappe.session.user and not is_manager():
		frappe.throw(_("هذه الحلقة مكلّف بها مونيتور آخر."), frappe.PermissionError)
	if note:
		doc.completion_note = note
		doc.save()
	apply_workflow(doc.as_dict(), Action.COMPLETE_REVIEW)
	return doc.name
