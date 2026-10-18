# Copyright (c) 2026, ORTAS IT Directorate and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from tv_archive.constants import DETAILED_REPORT
from tv_archive.utils import update_work_progress


class ArchiveWork(Document):
	def validate(self):
		if cint(self.episodes_count) <= 0:
			frappe.throw(_("عدد الحلقات يجب أن يكون أكبر من صفر."))

		if not self.is_new() and self.has_value_changed("episodes_count"):
			registered = frappe.db.count(DETAILED_REPORT, {"work": self.name, "docstatus": ("<", 2)})
			if cint(self.episodes_count) < registered:
				frappe.throw(
					_("لا يمكن أن يكون عدد الحلقات أقل من الحلقات المسجلة ({0}).").format(registered)
				)

	def on_update(self):
		if self.has_value_changed("episodes_count"):
			update_work_progress(self.name)
