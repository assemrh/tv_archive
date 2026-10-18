# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

"""Progress of every work: how many episodes are at each stage, and the general report state."""

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Count, Sum

from tv_archive.constants import ARCHIVE_WORK, DETAILED_REPORT, GENERAL_REPORT, DRState


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"fieldname": "work",
			"label": _("العمل"),
			"fieldtype": "Link",
			"options": ARCHIVE_WORK,
			"width": 220,
		},
		{"fieldname": "work_type", "label": _("النوع"), "fieldtype": "Data", "width": 80},
		{
			"fieldname": "category",
			"label": _("التصنيف"),
			"fieldtype": "Link",
			"options": "Archive Category",
			"width": 100,
		},
		{"fieldname": "episodes_count", "label": _("عدد الحلقات"), "fieldtype": "Int", "width": 95},
		{"fieldname": "drafts", "label": _("مسودات"), "fieldtype": "Int", "width": 80},
		{"fieldname": "pending", "label": _("بانتظار التكليف"), "fieldtype": "Int", "width": 110},
		{"fieldname": "in_review", "label": _("قيد المراجعة"), "fieldtype": "Int", "width": 100},
		{"fieldname": "ready", "label": _("جاهزة للعرض"), "fieldtype": "Int", "width": 100},
		{"fieldname": "progress", "label": _("نسبة الإنجاز"), "fieldtype": "Percent", "width": 110},
		{"fieldname": "general_state", "label": _("التقرير العام"), "fieldtype": "Data", "width": 120},
		{"fieldname": "status", "label": _("حالة الملف"), "fieldtype": "Data", "width": 90},
	]


def get_data(filters):
	work_filters = {k: filters[k] for k in ("status", "category", "work_type") if filters.get(k)}
	works = frappe.get_list(
		ARCHIVE_WORK,
		filters=work_filters,
		fields=[
			"name",
			"work_title",
			"work_type",
			"category",
			"episodes_count",
			"progress",
			"status",
			"general_report",
		],
		order_by="creation desc",
	)
	if not works:
		return []

	report = frappe.qb.DocType(DETAILED_REPORT)

	def count_state(state):
		return Sum(Case().when(report.workflow_state == state, 1).else_(0))

	counts = (
		frappe.qb.from_(report)
		.select(
			report.work,
			count_state(DRState.DRAFT).as_("drafts"),
			count_state(DRState.PENDING).as_("pending"),
			count_state(DRState.REVIEW).as_("in_review"),
			count_state(DRState.READY).as_("ready"),
			Count("*").as_("total"),
		)
		.where(report.work.isin([w.name for w in works]))
		.groupby(report.work)
		.run(as_dict=True)
	)
	counts = {row.work: row for row in counts}

	general_states = dict(
		frappe.get_all(
			GENERAL_REPORT,
			filters={"name": ("in", [w.general_report for w in works if w.general_report] or [""])},
			fields=["name", "workflow_state"],
			as_list=True,
		)
	)

	data = []
	for w in works:
		c = counts.get(w.name, {})
		data.append(
			{
				"work": w.name,
				"work_type": w.work_type,
				"category": w.category,
				"episodes_count": w.episodes_count,
				"drafts": c.get("drafts") or 0,
				"pending": c.get("pending") or 0,
				"in_review": c.get("in_review") or 0,
				"ready": c.get("ready") or 0,
				"progress": w.progress,
				"general_state": general_states.get(w.general_report) or _("لم يبدأ"),
				"status": w.status,
			}
		)
	return data
