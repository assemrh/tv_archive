# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

"""In-app notifications (ARC-REQ-04, 05, 06).

Notifications are written to Notification Log, which shows them in the bell menu
in real time and also emails them when the user has email alerts enabled.
"""

import frappe
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification
from frappe.utils.user import get_users_with_role

from tv_archive.constants import ROLE_COORDINATOR, ROLE_DIRECTOR
from tv_archive.utils import user_full_name


def coordinators() -> list[str]:
	return get_users_with_role(ROLE_COORDINATOR)


def directors() -> list[str]:
	return get_users_with_role(ROLE_DIRECTOR)


def notify(users, doc, subject: str, message: str | None = None):
	"""Send a bell notification about `doc` to `users`, skipping the person who acted."""
	recipients = sorted({u for u in (users or []) if u and u not in (frappe.session.user, "Guest")})
	if not recipients:
		return

	enqueue_create_notification(
		recipients,
		{
			"type": "Alert",
			"document_type": doc.doctype,
			"document_name": doc.name,
			"subject": subject,
			"email_content": message or subject,
			"from_user": frappe.session.user,
		},
	)


def episode_ref(doc) -> str:
	return f"«{doc.work_title or doc.work}» - {doc.episode_label}"


def notify_detailed_sent(doc):
	"""ARC-REQ-04: coordinator and section head get the new report."""
	notify(
		coordinators(),
		doc,
		f"تقرير تفصيلي جديد بانتظار تحديد المونيتور: {episode_ref(doc)} | المراقب: {user_full_name(doc.observer)}",
	)


def notify_monitor_assigned(doc):
	"""ARC-REQ-05: the assigned monitor gets the task."""
	notify(
		[doc.monitor],
		doc,
		f"كُلّفت بمتابعة {episode_ref(doc)} | الحالة: {doc.workflow_state}",
		doc.coordinator_instructions,
	)


def notify_episode_ready(doc):
	"""ARC-REQ-06: coordinator, section head and observer learn the episode is ready."""
	notify(
		[*coordinators(), doc.observer],
		doc,
		f"الحلقة جاهزة للعرض: {episode_ref(doc)} | المونيتور: {user_full_name(doc.monitor)}",
		doc.completion_note,
	)


def notify_returned(doc, ref: str):
	notify([doc.observer], doc, f"أُعيد إليك التقرير {ref} للتعديل", doc.return_reason)


def notify_general_sent(doc):
	notify(
		coordinators(),
		doc,
		f"تقرير رقابة عام بانتظار الاعتماد: «{doc.work_title or doc.work}» | المراقب: {user_full_name(doc.observer)}",
	)


def notify_general_approved(doc):
	notify(
		[doc.observer, *directors()],
		doc,
		f"اعتُمد التقرير العام وأُغلق ملف «{doc.work_title or doc.work}»",
	)
