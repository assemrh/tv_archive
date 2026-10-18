# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

"""Shared names for roles, workflow states and actions.

Workflow states and actions are stored in Arabic because they are shown to users
as-is (state indicator, action buttons) and match the wording of FSD V1.1.
"""

# Roles (ARC-ROL-01 .. ARC-ROL-04). System Manager acts as the system administrator.
ROLE_OBSERVER = "Archive Observer"
ROLE_COORDINATOR = "Archive Coordinator"
ROLE_MONITOR = "Archive Monitor"
ROLE_DIRECTOR = "Archive Director"
ROLE_SYSTEM_MANAGER = "System Manager"

ARCHIVE_ROLES = (ROLE_OBSERVER, ROLE_COORDINATOR, ROLE_MONITOR, ROLE_DIRECTOR)

# Roles that may edit any report in any state and drive the workflow.
MANAGER_ROLES = frozenset({ROLE_COORDINATOR, ROLE_SYSTEM_MANAGER})
# Roles that can see every report.
VIEW_ALL_ROLES = frozenset({ROLE_COORDINATOR, ROLE_DIRECTOR, ROLE_SYSTEM_MANAGER})

DETAILED_REPORT = "Detailed Review Report"
GENERAL_REPORT = "General Review Report"
ARCHIVE_WORK = "Archive Work"


class DRState:
	"""Detailed review report states (FSD: Workflow Matrix)."""

	DRAFT = "مسودة"
	PENDING = "بانتظار تحديد المونيتور"
	REVIEW = "قيد المراجعة من قبل المونيتور"
	READY = "الحلقة جاهزة للعرض"
	CANCELLED = "ملغى"


class GRState:
	"""General review report states."""

	DRAFT = "مسودة"
	PENDING = "بانتظار الاعتماد"
	APPROVED = "معتمد"
	CANCELLED = "ملغى"


class Action:
	SEND_DETAILED = "إرسال التقرير التفصيلي"
	ASSIGN_MONITOR = "تحديد المونيتور"
	RETURN_TO_OBSERVER = "إعادة للمراقب"
	COMPLETE_REVIEW = "تمت المراجعة"
	SEND_GENERAL = "إرسال للاعتماد"
	APPROVE = "اعتماد"
	CANCEL = "إلغاء"


RESULT_READY = "جاهزة للبث"
RESULT_NEEDS_EDIT = "تحتاج تعديلات"

WORK_OPEN = "مفتوح"
WORK_CLOSED = "مغلق"
