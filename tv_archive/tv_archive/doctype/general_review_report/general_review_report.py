# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

"""General review report: one per work (ARC-REQ-07).

Filled gradually while the episodes are reviewed, sent for approval once every
episode is ready for broadcast, and approving it closes the work file.

    مسودة → بانتظار الاعتماد → معتمد (submitted, work closed)
                    ↘ إعادة للمراقب (back to مسودة)
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.workflow import apply_workflow
from frappe.utils import cint, flt, now_datetime

from tv_archive import notifications
from tv_archive.constants import (
	ARCHIVE_WORK,
	DETAILED_REPORT,
	GENERAL_REPORT,
	WORK_CLOSED,
	WORK_OPEN,
	Action,
	GRState,
)
from tv_archive.utils import changed_fields, is_manager, state_changed

# Mandatory before the report leaves draft (ARC-REQ-07). Draft saves may be partial.
REQUIRED_TO_SEND = (
	"category",
	"story_script",
	"preparer",
	"director",
	"production_company",
	"episodes_count",
	"review_date",
	"characters",
	"subject",
	"notes",
	"objective_eval",
	"technical_eval",
)
SYSTEM_FIELDS = frozenset(
	{
		"workflow_state",
		"ready_episodes",
		"titles_total",
		"approved_by",
		"approved_on",
		"return_reason",
		"title",
		"work_title",
		"amended_from",
	}
)


class GeneralReviewReport(Document):
	def validate(self):
		self.title = _("التقرير العام: {0}").format(self.work_title or self.work)
		self.titles_total = flt(self.intro_duration) + flt(self.outro_duration)
		self.ready_episodes = frappe.db.count(DETAILED_REPORT, {"work": self.work, "docstatus": 1})

		self.validate_unique_per_work()
		self.validate_edit_rights()
		self.apply_state_change()

	def validate_unique_per_work(self):
		existing = frappe.db.get_value(
			GENERAL_REPORT, {"work": self.work, "docstatus": ("<", 2), "name": ("!=", self.name)}
		)
		if existing:
			frappe.throw(
				_("يوجد تقرير عام لهذا العمل مسبقاً: {0}").format(
					frappe.utils.get_link_to_form(GENERAL_REPORT, existing)
				)
			)

	def validate_edit_rights(self):
		if self.is_new() or is_manager():
			return
		before = self.get_doc_before_save()
		if not before or not (changed_fields(self) - SYSTEM_FIELDS):
			return
		if before.workflow_state == GRState.DRAFT and frappe.session.user in (before.observer, before.owner):
			return
		frappe.throw(
			_("لا يمكنك تعديل التقرير العام وهو في حالة «{0}».").format(before.workflow_state),
			frappe.PermissionError,
		)

	def apply_state_change(self):
		old, new = state_changed(self)
		if old == new:
			return
		if new == GRState.PENDING:
			self.validate_ready_to_send()
			self.return_reason = None
		elif new == GRState.DRAFT and old == GRState.PENDING:
			if not (self.return_reason or "").strip():
				frappe.throw(_("اكتب سبب إعادة التقرير للمراقب."))
		elif new == GRState.APPROVED:
			self.validate_ready_to_send()
			self.approved_by = frappe.session.user
			self.approved_on = now_datetime()

	def validate_ready_to_send(self):
		missing = [_(self.meta.get_label(f)) for f in REQUIRED_TO_SEND if not self.get(f)]
		if missing:
			frappe.throw(
				_("أكمل الحقول التالية قبل الإرسال:") + "<br>" + "<br>".join(missing),
				title=_("حقول ناقصة"),
			)

		episodes = cint(frappe.db.get_value(ARCHIVE_WORK, self.work, "episodes_count"))
		if self.ready_episodes < episodes:
			frappe.throw(
				_("لا يمكن إرسال التقرير العام قبل اكتمال الحلقات: {0} من {1} حلقة جاهزة للعرض.").format(
					self.ready_episodes, episodes
				)
			)

	def on_update(self):
		if self.is_new() or not frappe.db.get_value(ARCHIVE_WORK, self.work, "general_report"):
			frappe.db.set_value(ARCHIVE_WORK, self.work, "general_report", self.name, update_modified=False)

		old, new = state_changed(self)
		if old == new:
			return
		if new == GRState.PENDING:
			notifications.notify_general_sent(self)
		elif new == GRState.DRAFT and old == GRState.PENDING:
			notifications.notify_returned(self, f"العام «{self.work_title or self.work}»")

	def on_submit(self):
		frappe.db.set_value(
			ARCHIVE_WORK,
			self.work,
			{"status": WORK_CLOSED, "general_report": self.name},
			update_modified=False,
		)
		notifications.notify_general_approved(self)

	def on_cancel(self):
		frappe.db.set_value(ARCHIVE_WORK, self.work, "status", WORK_OPEN, update_modified=False)

	def on_trash(self):
		if not is_manager() and self.workflow_state != GRState.DRAFT:
			frappe.throw(_("يمكن حذف التقرير العام وهو مسودة فقط."), frappe.PermissionError)
		if frappe.db.get_value(ARCHIVE_WORK, self.work, "general_report") == self.name:
			frappe.db.set_value(ARCHIVE_WORK, self.work, "general_report", None, update_modified=False)


@frappe.whitelist()
def return_to_observer(name: str, reason: str) -> str:
	if not is_manager():
		frappe.throw(_("هذا الإجراء من صلاحية المنسق / رئيس شعبة المراقبة."), frappe.PermissionError)
	if not (reason or "").strip():
		frappe.throw(_("اكتب سبب إعادة التقرير للمراقب."))
	doc = frappe.get_doc(GENERAL_REPORT, name)
	if doc.workflow_state != GRState.PENDING:
		frappe.throw(_("التقرير في حالة «{0}»، ولا يمكن إعادته.").format(doc.workflow_state))
	doc.return_reason = reason
	doc.save()
	apply_workflow(doc.as_dict(), Action.RETURN_TO_OBSERVER)
	return doc.name
