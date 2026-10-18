# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

"""Row-level access (ARC-ROL-01 .. 04).

Role permissions in the DocType JSON decide *what* a role may do; these hooks decide
*which* records it may see:

- Observer: only reports where they are the observer (or that they created).
- Monitor: only detailed reports assigned to them.
- Coordinator, Director, System Manager: everything.
"""

import frappe

from tv_archive.constants import ROLE_MONITOR, ROLE_OBSERVER, VIEW_ALL_ROLES
from tv_archive.utils import user_roles


def _sees_everything(user: str, roles: set[str]) -> bool:
	return user == "Administrator" or bool(roles & VIEW_ALL_ROLES)


def detailed_report_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	roles = user_roles(user)
	if _sees_everything(user, roles):
		return ""

	table = "`tabDetailed Review Report`"
	esc = frappe.db.escape(user)
	conditions = []
	if ROLE_OBSERVER in roles:
		conditions += [f"{table}.observer = {esc}", f"{table}.owner = {esc}"]
	if ROLE_MONITOR in roles:
		conditions.append(f"{table}.monitor = {esc}")

	return "({})".format(" or ".join(conditions)) if conditions else "1=0"


def detailed_report_has_permission(doc, ptype=None, user=None) -> bool:
	user = user or frappe.session.user
	roles = user_roles(user)
	if _sees_everything(user, roles) or doc.is_new():
		return True
	if ROLE_OBSERVER in roles and user in (doc.observer, doc.owner):
		return True
	if ROLE_MONITOR in roles and doc.monitor == user:
		return True
	return False


def general_report_query(user: str | None = None) -> str:
	user = user or frappe.session.user
	roles = user_roles(user)
	if _sees_everything(user, roles):
		return ""

	if ROLE_OBSERVER in roles:
		table = "`tabGeneral Review Report`"
		esc = frappe.db.escape(user)
		return f"({table}.observer = {esc} or {table}.owner = {esc})"
	return "1=0"


def general_report_has_permission(doc, ptype=None, user=None) -> bool:
	user = user or frappe.session.user
	roles = user_roles(user)
	if _sees_everything(user, roles) or doc.is_new():
		return True
	return ROLE_OBSERVER in roles and user in (doc.observer, doc.owner)
