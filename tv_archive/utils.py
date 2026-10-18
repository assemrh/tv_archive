# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model import no_value_fields
from frappe.utils import cint, cstr, flt

from tv_archive.constants import ARCHIVE_WORK, DETAILED_REPORT, MANAGER_ROLES

NUMERIC_FIELDTYPES = ("Float", "Duration", "Currency", "Percent")
INT_FIELDTYPES = ("Int", "Check")


def user_roles(user: str | None = None) -> set[str]:
	return set(frappe.get_roles(user or frappe.session.user))


def is_manager(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or bool(user_roles(user) & MANAGER_ROLES)


def ensure_user_has_role(user: str, role: str, label: str):
	"""Throw if `user` is not an enabled user holding `role`."""
	if not user:
		frappe.throw(_("حقل «{0}» إجباري.").format(label))
	if not frappe.db.get_value("User", user, "enabled"):
		frappe.throw(_("المستخدم {0} غير موجود أو معطّل.").format(frappe.bold(user)))
	if role not in user_roles(user):
		frappe.throw(
			_("المستخدم {0} لا يملك دور {1}، ولا يمكن اختياره في حقل «{2}».").format(
				frappe.bold(user), frappe.bold(_(role)), label
			)
		)


def changed_fields(doc) -> set[str]:
	"""Data fields whose value differs from the version stored in the database.

	Values coming from the browser arrive as strings, so both sides are normalised
	by field type before comparing.
	"""
	before = doc.get_doc_before_save()
	if not before:
		return set()

	changed = set()
	for df in doc.meta.fields:
		if df.fieldtype in no_value_fields or df.fieldtype == "Table":
			continue
		if _normalise(df.fieldtype, doc.get(df.fieldname)) != _normalise(
			df.fieldtype, before.get(df.fieldname)
		):
			changed.add(df.fieldname)
	return changed


def _normalise(fieldtype, value):
	if fieldtype in INT_FIELDTYPES:
		return cint(value)
	if fieldtype in NUMERIC_FIELDTYPES:
		return flt(value)
	return cstr(value).strip()


def state_changed(doc) -> tuple[str | None, str | None]:
	"""Return (old_state, new_state) of the workflow_state field."""
	before = doc.get_doc_before_save()
	return (before.workflow_state if before else None, doc.workflow_state)


def update_work_progress(work: str | None):
	"""Recalculate the episode counters shown on the Archive Work form."""
	if not work or not frappe.db.exists(ARCHIVE_WORK, work):
		return

	reports_count = frappe.db.count(DETAILED_REPORT, {"work": work, "docstatus": ("<", 2)})
	ready_count = frappe.db.count(DETAILED_REPORT, {"work": work, "docstatus": 1})
	episodes_count = cint(frappe.db.get_value(ARCHIVE_WORK, work, "episodes_count"))
	progress = min(100.0, ready_count * 100.0 / episodes_count) if episodes_count else 0

	frappe.db.set_value(
		ARCHIVE_WORK,
		work,
		{"reports_count": reports_count, "ready_count": ready_count, "progress": progress},
		update_modified=False,
	)


def user_full_name(user: str | None) -> str:
	if not user:
		return ""
	return frappe.db.get_value("User", user, "full_name") or user
