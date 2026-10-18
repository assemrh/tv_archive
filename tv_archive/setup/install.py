# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

"""Create roles, workflows and default lists.

Runs after install and after every migrate, so changes to the workflows below reach
existing sites with `bench migrate`. Lists (categories, storage types) are only seeded
when missing, so edits made by administrators are kept.
"""

import frappe

from tv_archive.constants import (
	ARCHIVE_ROLES,
	DETAILED_REPORT,
	GENERAL_REPORT,
	ROLE_COORDINATOR,
	ROLE_MONITOR,
	ROLE_OBSERVER,
	Action,
	DRState,
	GRState,
)

STATE_STYLES = {
	DRState.DRAFT: "",
	DRState.PENDING: "Warning",
	DRState.REVIEW: "Primary",
	DRState.READY: "Success",
	DRState.CANCELLED: "Danger",
	GRState.PENDING: "Warning",
	GRState.APPROVED: "Success",
}

DEFAULT_CATEGORIES = ("درامي", "تاريخي", "كوميدي", "اجتماعي", "بيئة شامية", "وثائقي", "منوعات", "أطفال")
DEFAULT_STORAGE_TYPES = ("Hard", "Server")
WORKSPACE = "TV Archive"


def after_install():
	setup()


def after_migrate():
	setup()


def setup():
	create_roles()
	create_workflow_states()
	create_workflow_actions()
	create_detailed_report_workflow()
	create_general_report_workflow()
	seed_list("Archive Category", "category_name", DEFAULT_CATEGORIES)
	seed_list("Archive Storage Type", "storage_type_name", DEFAULT_STORAGE_TYPES)
	ensure_desk_entry()


def create_roles():
	for role in ARCHIVE_ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def create_workflow_states():
	for state, style in STATE_STYLES.items():
		if frappe.db.exists("Workflow State", state):
			frappe.db.set_value("Workflow State", state, "style", style)
		else:
			frappe.get_doc(
				{"doctype": "Workflow State", "workflow_state_name": state, "style": style}
			).insert(ignore_permissions=True)


def create_workflow_actions():
	for action in (
		Action.SEND_DETAILED,
		Action.ASSIGN_MONITOR,
		Action.RETURN_TO_OBSERVER,
		Action.COMPLETE_REVIEW,
		Action.SEND_GENERAL,
		Action.APPROVE,
		Action.CANCEL,
	):
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(
				ignore_permissions=True
			)


def state(name, docstatus, role):
	return {"state": name, "doc_status": str(docstatus), "allow_edit": role}


def transition(from_state, action, to_state, role, condition=None):
	return {
		"state": from_state,
		"action": action,
		"next_state": to_state,
		"allowed": role,
		"allow_self_approval": 1,
		"condition": condition,
	}


def create_detailed_report_workflow():
	"""FSD V1.1 workflow matrix, plus the return path proposed in the analysis."""
	upsert_workflow(
		"Detailed Review Report Workflow",
		DETAILED_REPORT,
		states=[
			state(DRState.DRAFT, 0, ROLE_OBSERVER),
			state(DRState.DRAFT, 0, ROLE_COORDINATOR),
			state(DRState.PENDING, 0, ROLE_COORDINATOR),
			state(DRState.REVIEW, 0, ROLE_COORDINATOR),
			state(DRState.REVIEW, 0, ROLE_MONITOR),
			state(DRState.READY, 1, ROLE_COORDINATOR),
			state(DRState.CANCELLED, 2, ROLE_COORDINATOR),
		],
		transitions=[
			transition(DRState.DRAFT, Action.SEND_DETAILED, DRState.PENDING, ROLE_OBSERVER),
			transition(DRState.DRAFT, Action.SEND_DETAILED, DRState.PENDING, ROLE_COORDINATOR),
			transition(
				DRState.PENDING, Action.ASSIGN_MONITOR, DRState.REVIEW, ROLE_COORDINATOR, "doc.monitor"
			),
			transition(
				DRState.PENDING,
				Action.RETURN_TO_OBSERVER,
				DRState.DRAFT,
				ROLE_COORDINATOR,
				"doc.return_reason",
			),
			transition(
				DRState.REVIEW,
				Action.COMPLETE_REVIEW,
				DRState.READY,
				ROLE_MONITOR,
				"doc.monitor == frappe.session.user",
			),
			transition(DRState.REVIEW, Action.COMPLETE_REVIEW, DRState.READY, ROLE_COORDINATOR),
			transition(DRState.READY, Action.CANCEL, DRState.CANCELLED, ROLE_COORDINATOR),
		],
	)


def create_general_report_workflow():
	upsert_workflow(
		"General Review Report Workflow",
		GENERAL_REPORT,
		states=[
			state(GRState.DRAFT, 0, ROLE_OBSERVER),
			state(GRState.DRAFT, 0, ROLE_COORDINATOR),
			state(GRState.PENDING, 0, ROLE_COORDINATOR),
			state(GRState.APPROVED, 1, ROLE_COORDINATOR),
			state(GRState.CANCELLED, 2, ROLE_COORDINATOR),
		],
		transitions=[
			transition(GRState.DRAFT, Action.SEND_GENERAL, GRState.PENDING, ROLE_OBSERVER),
			transition(GRState.DRAFT, Action.SEND_GENERAL, GRState.PENDING, ROLE_COORDINATOR),
			transition(GRState.PENDING, Action.APPROVE, GRState.APPROVED, ROLE_COORDINATOR),
			transition(
				GRState.PENDING,
				Action.RETURN_TO_OBSERVER,
				GRState.DRAFT,
				ROLE_COORDINATOR,
				"doc.return_reason",
			),
			transition(GRState.APPROVED, Action.CANCEL, GRState.CANCELLED, ROLE_COORDINATOR),
		],
	)


def upsert_workflow(name, document_type, states, transitions):
	if frappe.db.exists("Workflow", name):
		workflow = frappe.get_doc("Workflow", name)
		workflow.set("states", [])
		workflow.set("transitions", [])
	else:
		workflow = frappe.new_doc("Workflow")
		workflow.workflow_name = name

	workflow.update(
		{
			"document_type": document_type,
			"workflow_state_field": "workflow_state",
			"is_active": 1,
			"override_status": 1,
			"send_email_alert": 0,
		}
	)
	for row in states:
		workflow.append("states", row)
	for row in transitions:
		workflow.append("transitions", row)
	workflow.save(ignore_permissions=True)


def ensure_desk_entry():
	"""v16 builds the sidebar and desktop icon from the workspace only at app install.

	Sites that got the workspace through a later migrate need them created here.
	"""
	if frappe.db.exists("Workspace Sidebar", WORKSPACE) and frappe.db.exists(
		"Desktop Icon", {"label": WORKSPACE}
	):
		return
	# Call whatever Frappe itself runs after an app install; the function name changed
	# within v16 (auto_generate_icons_and_sidebar → create_desktop_icons_for_app).
	for method in frappe.get_hooks("after_app_install", app_name="frappe"):
		frappe.get_attr(method)("tv_archive")


def seed_list(doctype, fieldname, values):
	if frappe.db.count(doctype):
		return
	for value in values:
		frappe.get_doc({"doctype": doctype, fieldname: value, "enabled": 1}).insert(ignore_permissions=True)
