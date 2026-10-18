# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

"""Episodes reviewed per observer in a date range, split by result and current state."""

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, Sum

from tv_archive.constants import DETAILED_REPORT, RESULT_NEEDS_EDIT, DRState


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = [
		{
			"fieldname": "observer",
			"label": _("المراقب"),
			"fieldtype": "Link",
			"options": "User",
			"width": 220,
		},
		{"fieldname": "total", "label": _("الحلقات المراقبة"), "fieldtype": "Int", "width": 120},
		{"fieldname": "needs_edit", "label": _("تحتاج تعديلات"), "fieldtype": "Int", "width": 110},
		{"fieldname": "in_progress", "label": _("قيد المتابعة"), "fieldtype": "Int", "width": 110},
		{"fieldname": "ready", "label": _("جاهزة للعرض"), "fieldtype": "Int", "width": 110},
		{"fieldname": "duration", "label": _("إجمالي المدة المراقبة"), "fieldtype": "Duration", "width": 150},
	]

	report = frappe.qb.DocType(DETAILED_REPORT)
	query = (
		frappe.qb.from_(report)
		.select(
			report.observer,
			Count("*").as_("total"),
			Sum(Case().when(report.review_result == RESULT_NEEDS_EDIT, 1).else_(0)).as_("needs_edit"),
			Sum(Case().when(report.workflow_state.isin([DRState.PENDING, DRState.REVIEW]), 1).else_(0)).as_(
				"in_progress"
			),
			Sum(Case().when(report.workflow_state == DRState.READY, 1).else_(0)).as_("ready"),
			Sum(report.episode_duration).as_("duration"),
		)
		.where(report.docstatus < 2)
		.groupby(report.observer)
		.orderby(Count("*"), order=frappe.qb.desc)
	)
	if filters.from_date:
		query = query.where(report.review_date >= filters.from_date)
	if filters.to_date:
		query = query.where(report.review_date <= filters.to_date)
	if filters.work:
		query = query.where(report.work == filters.work)

	data = query.run(as_dict=True)
	chart = {
		"data": {
			"labels": [frappe.db.get_value("User", d.observer, "full_name") or d.observer for d in data],
			"datasets": [
				{"name": _("جاهزة للعرض"), "values": [d.ready for d in data]},
				{"name": _("قيد المتابعة"), "values": [d.in_progress for d in data]},
			],
		},
		"type": "bar",
		"barOptions": {"stacked": 1},
	}
	return columns, data, None, chart
