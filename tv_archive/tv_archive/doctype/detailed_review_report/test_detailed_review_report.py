# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

from contextlib import contextmanager

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase

from tv_archive.constants import (
	RESULT_NEEDS_EDIT,
	RESULT_READY,
	ROLE_COORDINATOR,
	ROLE_DIRECTOR,
	ROLE_MONITOR,
	ROLE_OBSERVER,
	WORK_CLOSED,
	Action,
	DRState,
	GRState,
)
from tv_archive.tv_archive.doctype.detailed_review_report.detailed_review_report import (
	assign_monitor,
	complete_review,
	make_episode_label,
	return_to_observer,
)

USERS = {
	"observer": ("archive.observer@test.local", ROLE_OBSERVER),
	"observer2": ("archive.observer2@test.local", ROLE_OBSERVER),
	"coordinator": ("archive.coordinator@test.local", ROLE_COORDINATOR),
	"monitor": ("archive.monitor@test.local", ROLE_MONITOR),
	"monitor2": ("archive.monitor2@test.local", ROLE_MONITOR),
	"director": ("archive.director@test.local", ROLE_DIRECTOR),
}


def make_user(email, role):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
	return email


@contextmanager
def as_user(user):
	previous = frappe.session.user
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user(previous)


class TestDetailedReviewReport(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.u = {key: make_user(email, role) for key, (email, role) in USERS.items()}

	def setUp(self):
		frappe.set_user("Administrator")
		self.work = frappe.get_doc(
			{
				"doctype": "Archive Work",
				"work_title": f"الخان {frappe.generate_hash(length=5)}",
				"work_type": "مسلسل",
				"season_no": 2,
				"category": "درامي",
				"episodes_count": 2,
				"director": "مخرج تجريبي",
				"production_company": "شركة تجريبية",
				"default_characters": "سليمان، رحاب",
			}
		).insert()

	def new_report(self, episode_no=1, result=RESULT_NEEDS_EDIT, observer=None):
		observer = observer or self.u["observer"]
		with as_user(observer):
			return frappe.get_doc(
				{
					"doctype": "Detailed Review Report",
					"observer": observer,
					"work": self.work.name,
					"episode_no": episode_no,
					"episode_duration": 2747,
					"episode_summary": "ملخص الحلقة",
					"review_result": result,
					"notes": "مشهد يحتاج حذف من 22:42 إلى 23:40" if result == RESULT_NEEDS_EDIT else None,
				}
			).insert()

	def send(self, doc, user=None):
		with as_user(user or doc.observer):
			return apply_workflow(doc.as_dict(), Action.SEND_DETAILED)

	def run_to_ready(self, doc):
		self.send(doc)
		with as_user(self.u["coordinator"]):
			assign_monitor(doc.name, self.u["monitor"], "احذف المشهد")
		with as_user(self.u["monitor"]):
			complete_review(doc.name, "تم")
		return frappe.get_doc(doc.doctype, doc.name)

	def test_defaults_from_work(self):
		doc = self.new_report()
		self.assertEqual(doc.workflow_state, DRState.DRAFT)
		self.assertEqual(doc.season_no, 2)
		self.assertEqual(doc.episode_label, "الجزء الثاني الحلقة 1")
		self.assertEqual(doc.characters, "سليمان، رحاب")
		self.assertEqual(doc.episode_director, "مخرج تجريبي")
		self.assertEqual(make_episode_label(12, 3), "الجزء 12 الحلقة 3")

	def test_full_episode_cycle_and_notifications(self):
		doc = self.new_report()

		self.send(doc)
		doc.reload()
		self.assertEqual(doc.workflow_state, DRState.PENDING)
		self.assertTrue(
			frappe.db.exists(
				"Notification Log",
				{"for_user": self.u["coordinator"], "document_name": doc.name},
			),
			"ARC-REQ-04: coordinator should be notified",
		)

		with as_user(self.u["coordinator"]):
			assign_monitor(doc.name, self.u["monitor"], "احذف المشهد")
		doc.reload()
		self.assertEqual(doc.workflow_state, DRState.REVIEW)
		self.assertEqual(doc.assigned_by, self.u["coordinator"])
		self.assertTrue(
			frappe.db.exists("Notification Log", {"for_user": self.u["monitor"], "document_name": doc.name}),
			"ARC-REQ-05: monitor should be notified",
		)

		with as_user(self.u["monitor"]):
			complete_review(doc.name, "تم الحذف")
		doc.reload()
		self.assertEqual(doc.workflow_state, DRState.READY)
		self.assertEqual(doc.docstatus, 1)
		self.assertEqual(doc.completed_by, self.u["monitor"])
		self.assertEqual(
			frappe.db.count("Notification Log", {"for_user": self.u["observer"], "document_name": doc.name}),
			1,
			"ARC-REQ-06: observer should be notified once",
		)

		work = frappe.get_doc("Archive Work", self.work.name)
		self.assertEqual((work.reports_count, work.ready_count, work.progress), (1, 1, 50))

	def test_observer_cannot_edit_after_sending(self):
		doc = self.new_report()
		self.send(doc)
		with as_user(self.u["observer"]):
			doc = frappe.get_doc(doc.doctype, doc.name)
			doc.episode_summary = "تعديل غير مسموح"
			self.assertRaises(frappe.PermissionError, doc.save)

	def test_monitor_may_only_add_completion_note(self):
		doc = self.new_report()
		self.send(doc)
		with as_user(self.u["coordinator"]):
			assign_monitor(doc.name, self.u["monitor"])
		with as_user(self.u["monitor"]):
			doc = frappe.get_doc(doc.doctype, doc.name)
			doc.completion_note = "قيد التنفيذ"
			doc.save()
			doc.episode_summary = "تعديل غير مسموح"
			self.assertRaises(frappe.PermissionError, doc.save)

	def test_other_monitor_cannot_complete(self):
		doc = self.new_report()
		self.send(doc)
		with as_user(self.u["coordinator"]):
			assign_monitor(doc.name, self.u["monitor"])
		with as_user(self.u["monitor2"]):
			self.assertRaises(frappe.PermissionError, complete_review, doc.name)

	def test_only_monitors_can_be_assigned(self):
		doc = self.new_report()
		self.send(doc)
		with as_user(self.u["coordinator"]):
			self.assertRaises(frappe.ValidationError, assign_monitor, doc.name, self.u["observer2"])

	def test_observer_cannot_assign_monitor(self):
		doc = self.new_report()
		self.send(doc)
		with as_user(self.u["observer"]):
			self.assertRaises(frappe.PermissionError, assign_monitor, doc.name, self.u["monitor"])

	def test_return_to_observer(self):
		doc = self.new_report()
		self.send(doc)
		with as_user(self.u["coordinator"]):
			self.assertRaises(frappe.ValidationError, return_to_observer, doc.name, " ")
			return_to_observer(doc.name, "الملخص ناقص")
		doc.reload()
		self.assertEqual(doc.workflow_state, DRState.DRAFT)
		self.assertEqual(doc.return_reason, "الملخص ناقص")

		# The observer can edit again and resend; the reason is cleared.
		with as_user(self.u["observer"]):
			doc.episode_summary = "ملخص كامل"
			doc.save()
		self.send(doc)
		doc.reload()
		self.assertEqual(doc.workflow_state, DRState.PENDING)
		self.assertFalse(doc.return_reason)

	def test_notes_required_when_needs_edit(self):
		with as_user(self.u["observer"]):
			doc = frappe.get_doc(
				{
					"doctype": "Detailed Review Report",
					"observer": self.u["observer"],
					"work": self.work.name,
					"episode_no": 1,
					"episode_duration": 2700,
					"episode_summary": "ملخص",
					"review_result": RESULT_NEEDS_EDIT,
				}
			)
			self.assertRaises(frappe.ValidationError, doc.insert)

	def test_duplicate_episode_rejected(self):
		self.new_report(episode_no=1)
		self.assertRaises(frappe.ValidationError, self.new_report, 1)

	def test_row_level_permissions(self):
		mine = self.new_report(episode_no=1)
		self.new_report(episode_no=2, observer=self.u["observer2"])

		with as_user(self.u["observer"]):
			visible = frappe.get_list(
				"Detailed Review Report", filters={"work": self.work.name}, pluck="name"
			)
			self.assertEqual(visible, [mine.name])

		with as_user(self.u["monitor"]):
			self.assertEqual(frappe.get_list("Detailed Review Report", filters={"work": self.work.name}), [])

		with as_user(self.u["director"]):
			self.assertEqual(
				len(frappe.get_list("Detailed Review Report", filters={"work": self.work.name})), 2
			)

	def test_general_report_closes_work(self):
		first = self.run_to_ready(self.new_report(episode_no=1, result=RESULT_READY))

		with as_user(self.u["observer"]):
			general = frappe.get_doc(
				{"doctype": "General Review Report", "observer": self.u["observer"], "work": self.work.name}
			).insert()
			self.assertEqual(general.director, "مخرج تجريبي")
			general.update(
				{
					"preparer": "معد",
					"story_script": "كاتب",
					"review_date": frappe.utils.today(),
					"subject": "الموضوع",
					"notes": "لا يوجد",
					"objective_eval": "جيد",
					"technical_eval": "جيد",
					"intro_duration": 90,
					"outro_duration": 70,
				}
			)
			general.save()
			self.assertEqual(general.titles_total, 160)
			# Only one of two episodes is ready.
			self.assertRaises(frappe.ValidationError, apply_workflow, general.as_dict(), Action.SEND_GENERAL)

		self.run_to_ready(self.new_report(episode_no=2, result=RESULT_READY))
		with as_user(self.u["observer"]):
			apply_workflow(general.as_dict(), Action.SEND_GENERAL)
		with as_user(self.u["coordinator"]):
			apply_workflow(frappe.get_doc(general.doctype, general.name).as_dict(), Action.APPROVE)

		general.reload()
		self.assertEqual((general.workflow_state, general.docstatus), (GRState.APPROVED, 1))
		self.assertEqual(frappe.db.get_value("Archive Work", self.work.name, "status"), WORK_CLOSED)
		self.assertEqual(first.workflow_state, DRState.READY)

		# A closed work accepts no new episodes.
		self.assertRaises(frappe.ValidationError, self.new_report, 3)
