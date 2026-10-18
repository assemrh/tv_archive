# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.search import validate_and_sanitize_search_inputs
from frappe.query_builder.functions import Count

from tv_archive.constants import ARCHIVE_ROLES, DETAILED_REPORT, ROLE_MONITOR, DRState


@frappe.whitelist()
@validate_and_sanitize_search_inputs
def users_with_role(doctype, txt, searchfield, start, page_len, filters):
	"""Link query for observer and monitor fields: enabled users holding one archive role.

	For monitors the description shows how many episodes are currently assigned to them,
	so the coordinator can spread the work (W-06 wireframe).
	"""
	role = (filters or {}).get("role")
	if role not in ARCHIVE_ROLES:
		frappe.throw(_("دور غير معروف: {0}").format(role))

	user = frappe.qb.DocType("User")
	has_role = frappe.qb.DocType("Has Role")
	pattern = f"%{txt}%"
	rows = (
		frappe.qb.from_(user)
		.join(has_role)
		.on((has_role.parent == user.name) & (has_role.parenttype == "User"))
		.select(user.name, user.full_name)
		.where(
			(has_role.role == role)
			& (user.enabled == 1)
			& (user.name.notin(["Administrator", "Guest"]))
			& ((user.name.like(pattern)) | (user.full_name.like(pattern)))
		)
		.distinct()
		.orderby(user.full_name)
		.limit(page_len)
		.offset(start)
		.run()
	)

	if role != ROLE_MONITOR:
		return rows

	report = frappe.qb.DocType(DETAILED_REPORT)
	open_tasks = dict(
		frappe.qb.from_(report)
		.select(report.monitor, Count("*"))
		.where(
			(report.workflow_state == DRState.REVIEW) & (report.monitor.isin([r[0] for r in rows] or [""]))
		)
		.groupby(report.monitor)
		.run()
	)
	return [
		(name, full_name, _("مهام مفتوحة: {0}").format(open_tasks.get(name, 0))) for name, full_name in rows
	]
