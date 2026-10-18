# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

"""Demo data for training and acceptance testing. Never run on production.

    bench --site archive.localhost execute tv_archive.setup.demo.make_demo

Creates one user per role (password: DEMO_PASSWORD) and an example work whose
episodes sit at every workflow stage.
"""

import frappe
from frappe.model.workflow import apply_workflow

from tv_archive.constants import (
	RESULT_NEEDS_EDIT,
	RESULT_READY,
	ROLE_COORDINATOR,
	ROLE_DIRECTOR,
	ROLE_MONITOR,
	ROLE_OBSERVER,
	Action,
)
from tv_archive.tv_archive.doctype.detailed_review_report.detailed_review_report import (
	assign_monitor,
	complete_review,
)

DEMO_PASSWORD = "Archive@2026"
DEMO_USERS = (
	("observer@archive.local", "سامر", "المراقب", ROLE_OBSERVER),
	("observer2@archive.local", "ريم", "المراقبة", ROLE_OBSERVER),
	("coordinator@archive.local", "أحمد", "المنسق", ROLE_COORDINATOR),
	("monitor@archive.local", "ماهر", "المونيتور", ROLE_MONITOR),
	("monitor2@archive.local", "لينا", "المونيتور", ROLE_MONITOR),
	("director@archive.local", "مدير", "المديرية", ROLE_DIRECTOR),
)
DEMO_WORK = "الخان (مثال تدريبي)"


def make_demo():
	if frappe.conf.get("developer_mode") != 1 and not frappe.conf.get("allow_tests"):
		frappe.throw("Demo data is only allowed on development or test sites.")

	users = {role: [] for *_, role in DEMO_USERS}
	for email, first, last, role in DEMO_USERS:
		users[role].append(make_user(email, first, last, role))

	if frappe.db.exists("Archive Work", {"work_title": DEMO_WORK}):
		print("Demo work already exists, skipping episodes.")
		return

	work = frappe.get_doc(
		{
			"doctype": "Archive Work",
			"work_title": DEMO_WORK,
			"work_type": "مسلسل",
			"season_no": 2,
			"category": "درامي",
			"episodes_count": 30,
			"story_script": "كاتب العمل (مثال)",
			"preparer": "معد العمل (مثال)",
			"director": "مخرج العمل (مثال)",
			"production_company": "شركة الإنتاج (مثال)",
			"storage_type": "Server",
			"storage_number": "SRV-2026-215",
			"default_characters": "سليمان، رحاب، أبو علي، أم سمير",
		}
	).insert(ignore_permissions=True)

	observer, observer2 = users[ROLE_OBSERVER]
	coordinator = users[ROLE_COORDINATOR][0]
	monitor, monitor2 = users[ROLE_MONITOR]

	def episode(no, result, by):
		frappe.set_user(by)
		doc = frappe.get_doc(
			{
				"doctype": "Detailed Review Report",
				"observer": by,
				"work": work.name,
				"episode_no": no,
				"episode_duration": 2700 + no * 37,
				"episode_summary": f"ملخص الحلقة {no} (نص تدريبي).",
				"review_result": result,
				"notes": f"مشهد يحتاج حذف في الحلقة {no} من الدقيقة 22:42 إلى 23:40"
				if result == RESULT_NEEDS_EDIT
				else None,
			}
		).insert()
		return doc

	def send(doc):
		frappe.set_user(doc.observer)
		apply_workflow(doc.as_dict(), Action.SEND_DETAILED)

	try:
		for no in (1, 2):  # ready for broadcast
			doc = episode(
				no, RESULT_NEEDS_EDIT if no == 2 else RESULT_READY, observer if no == 1 else observer2
			)
			send(doc)
			frappe.set_user(coordinator)
			assign_monitor(doc.name, monitor, "يرجى التنفيذ ونقل الملف إلى مجلد جاهزة للعرض")
			frappe.set_user(monitor)
			complete_review(doc.name, "تم التنفيذ ونقل الملف")

		doc = episode(3, RESULT_READY, observer2)  # under review
		send(doc)
		frappe.set_user(coordinator)
		assign_monitor(doc.name, monitor2)

		doc = episode(4, RESULT_NEEDS_EDIT, observer)  # waiting for a monitor
		send(doc)

		episode(5, RESULT_READY, observer)  # draft
	finally:
		frappe.set_user("Administrator")

	frappe.db.commit()
	print(f"Demo data created. Users: {', '.join(e for e, *_ in DEMO_USERS)} / password: {DEMO_PASSWORD}")


def make_user(email, first_name, last_name, role):
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": last_name,
				"language": "ar",
				"send_welcome_email": 0,
				"new_password": DEMO_PASSWORD,
				"roles": [{"role": role}],
			}
		).insert(ignore_permissions=True)
	return email
