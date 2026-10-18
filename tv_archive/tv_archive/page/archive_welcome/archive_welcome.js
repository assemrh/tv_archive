// Copyright (c) 2026, ORTAS IT Directorate and contributors
// For license information, please see license.txt

// Welcome page: the landing page after login. Shows each user what is waiting for
// them according to their role, how the review cycle works, and quick actions.

frappe.pages["archive-welcome"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("الصفحة الرئيسية"),
		single_column: true,
	});
	wrapper.archive_welcome = new TvArchiveWelcome(page);
};

frappe.pages["archive-welcome"].on_page_show = function (wrapper) {
	// Counts change as people work; refresh whenever the user comes back to this page.
	wrapper.archive_welcome && wrapper.archive_welcome.refresh();
};

const TV_ARCHIVE_ROLE_LABELS = {
	"Archive Observer": __("مراقب"),
	"Archive Coordinator": __("منسق / رئيس شعبة"),
	"Archive Monitor": __("مونيتور"),
	"Archive Director": __("مدير المديرية"),
};

// The review cycle (FSD workflow matrix). `role` marks whose step it is.
const TV_ARCHIVE_STEPS = [
	{ role: "Archive Observer", title: __("المراقب"), text: __("يشاهد الحلقة ويكتب التقرير التفصيلي ثم يرسله") },
	{ role: "Archive Coordinator", title: __("المنسق"), text: __("يراجع التقرير ويكلّف مونيتوراً، أو يعيده للمراقب") },
	{ role: "Archive Monitor", title: __("المونيتور"), text: __("ينفّذ الملاحظات وينقل الحلقة إلى مجلد جاهزة للعرض") },
	{ role: null, title: __("جاهزة للعرض"), text: __("تُحفظ الحلقة في الأرشيف ويُشعَر المنسق والمراقب") },
	{ role: "Archive Coordinator", title: __("إغلاق العمل"), text: __("بعد اكتمال الحلقات يُعتمد التقرير العام ويُغلق الملف") },
];

const TV_ARCHIVE_TIPS = {
	"Archive Observer": [
		__("ابدأ من «تقرير حلقة جديد»، واختر العمل من القائمة؛ المخرج والشخصيات تُملأ تلقائياً."),
		__("إذا كانت النتيجة «تحتاج تعديلات» فاكتب الملاحظات بدقة، مع التوقيت إن أمكن."),
		__("يمكنك الحفظ كمسودة والعودة لاحقاً. بعد الإرسال لا يمكنك التعديل إلا إذا أعاده المنسق."),
		__("ارفع صورة وجه وظهر التقرير الورقي من قسم «صورة التقرير الورقي»."),
	],
	"Archive Coordinator": [
		__("ابدأ يومك من بطاقة «بانتظار تحديد المونيتور»."),
		__("بجانب كل مونيتور في نافذة التكليف عدد مهامه المفتوحة، فوزّع العمل بينهم."),
		__("إذا كان التقرير ناقصاً فاستخدم «إعادة للمراقب» واكتب السبب؛ سيظهر له في أعلى التقرير."),
		__("تقرير «تقدم الأعمال» يبيّن أين وصل كل مسلسل."),
	],
	"Archive Monitor": [
		__("ستصلك إشعارات في الجرس أعلى الشاشة عند تكليفك بحلقة."),
		__("اقرأ الملاحظات وتعليمات المنسق داخل التقرير قبل البدء."),
		__("بعد التنفيذ ونقل الملف اضغط «تمت المراجعة» وأضف ملاحظة قصيرة."),
	],
	"Archive Director": [
		__("كل التقارير متاحة لك للاطلاع والطباعة."),
		__("تقرير «إحصاءات المراقبين» يعرض الإنجاز حسب المراقب والفترة."),
	],
};

class TvArchiveWelcome {
	constructor(page) {
		this.page = page;
		this.$body = $('<div class="tva-welcome"></div>').appendTo(page.main);
		this.page.set_secondary_action(__("تحديث"), () => this.refresh());
	}

	async refresh() {
		const r = await frappe.call({ method: "tv_archive.welcome.get_welcome_data" });
		this.data = r.message;
		this.render();
	}

	render() {
		const d = this.data;
		const esc = frappe.utils.escape_html;
		const first_name = esc((d.full_name || "").split(" ")[0]);
		const role_chips = d.roles
			.map((r) => `<span class="tva-chip">${esc(TV_ARCHIVE_ROLE_LABELS[r] || r)}</span>`)
			.join("");
		const today = frappe.datetime.str_to_user(frappe.datetime.get_today());

		this.$body.html(`
			<section class="tva-hero">
				<div>
					<div class="tva-eyebrow">${__("أرشيف المسلسلات والبرامج · الفضائية السورية")}</div>
					<h2>${__("مرحباً، {0}", [first_name])}</h2>
					<p>${this.greeting_line()}</p>
					<div class="tva-chips">${role_chips}<span class="tva-date">${today}</span></div>
				</div>
				<div class="tva-actions">${this.quick_actions()}</div>
			</section>
			${d.setup.length ? this.setup_html() : ""}
			${d.sections.map((s) => this.section_html(s)).join("")}
			<div class="tva-grid-2">
				<section class="tva-panel">
					<h3>${__("كيف يمر التقرير")}</h3>
					<ol class="tva-steps">${this.steps_html()}</ol>
				</section>
				<section class="tva-panel">
					<h3>${__("إرشادات سريعة")}</h3>
					<ul class="tva-tips">${this.tips_html()}</ul>
				</section>
			</div>
			${d.recent.length ? this.recent_html() : ""}
		`);
		this.bind();
	}

	greeting_line() {
		const waiting = this.data.sections
			.flatMap((s) => s.cards)
			.filter((c) => c.tone === "warning" && c.count > 0)
			.reduce((sum, c) => sum + c.count, 0);
		return waiting
			? __("لديك {0} عنصر بانتظار إجراء منك. ابدأ من البطاقات المميّزة باللون البرتقالي.", [waiting])
			: __("لا يوجد ما ينتظرك الآن. يمكنك البدء من الأزرار المجاورة.");
	}

	quick_actions() {
		const roles = this.data.roles;
		const actions = [];
		if (roles.includes("Archive Observer") || roles.includes("Archive Coordinator")) {
			actions.push(["new-detailed", __("تقرير حلقة جديد"), true]);
		}
		if (roles.includes("Archive Coordinator")) {
			actions.push(["new-work", __("تسجيل عمل جديد"), false]);
		}
		if (roles.includes("Archive Observer")) {
			actions.push(["new-general", __("تقرير عام جديد"), false]);
		}
		if (roles.includes("Archive Monitor")) {
			actions.push(["my-tasks", __("فتح مهامي"), true]);
		}
		if (roles.includes("Archive Director") || roles.includes("Archive Coordinator")) {
			actions.push(["progress", __("تقدم الأعمال"), false]);
		}
		if (this.data.is_admin) {
			actions.push(["users", __("إدارة المستخدمين"), false]);
		}
		return actions
			.map(
				([key, label, primary]) =>
					`<button class="btn ${primary ? "btn-primary" : "btn-default"} btn-sm" data-action="${key}">${label}</button>`
			)
			.join("");
	}

	setup_html() {
		const items = this.data.setup;
		const done = items.filter((i) => i.done).length;
		const rows = items
			.map(
				(item, idx) => `
				<li class="${item.done ? "is-done" : ""}">
					<span class="tva-check">${item.done ? "✓" : ""}</span>
					<a href="#" data-setup="${idx}">${frappe.utils.escape_html(item.label)}</a>
					<span class="text-muted">${frappe.utils.escape_html(item.detail || "")}</span>
				</li>`
			)
			.join("");
		return `
			<section class="tva-panel tva-setup">
				<h3>${__("إعداد النظام")} <span class="text-muted">${done} / ${items.length}</span></h3>
				<p class="text-muted">${__("خطوات يقوم بها مدير النظام مرة واحدة: أنشئ المستخدمين وامنح كل واحد دوره (مراقب، منسق، مونيتور، مدير المديرية).")}</p>
				<ul>${rows}</ul>
			</section>`;
	}

	section_html(section) {
		const cards = section.cards
			.map((c, idx) => {
				const hint = c.hint ? `<div class="tva-hint">${frappe.utils.escape_html(c.hint)}</div>` : "";
				return `
					<button class="tva-card tone-${c.tone} ${c.count ? "" : "is-empty"}"
						data-role="${section.role}" data-card="${idx}">
						<span class="tva-count">${c.count}</span>
						<span class="tva-label">${frappe.utils.escape_html(c.label)}</span>
						${hint}
					</button>`;
			})
			.join("");
		return `
			<section class="tva-section">
				<h3>${frappe.utils.escape_html(section.title)}</h3>
				<div class="tva-cards">${cards}</div>
			</section>`;
	}

	steps_html() {
		const roles = this.data.roles;
		return TV_ARCHIVE_STEPS.map(
			(s, idx) => `
				<li class="${s.role && roles.includes(s.role) ? "is-mine" : ""}">
					<span class="tva-step-no">${idx + 1}</span>
					<div><b>${s.title}</b>${s.role && roles.includes(s.role) ? `<span class="tva-you">${__("دورك")}</span>` : ""}
					<div class="text-muted">${s.text}</div></div>
				</li>`
		).join("");
	}

	tips_html() {
		const tips = this.data.roles.flatMap((r) => TV_ARCHIVE_TIPS[r] || []);
		const all = tips.length ? tips : [__("اطلب من مدير النظام منحك دوراً في النظام لتظهر لك مهامك هنا.")];
		return all.map((t) => `<li>${t}</li>`).join("");
	}

	recent_html() {
		const rows = this.data.recent
			.map(
				(r) => `
				<tr data-name="${frappe.utils.escape_html(r.name)}">
					<td>${frappe.utils.escape_html(r.title || r.name)}</td>
					<td><span class="indicator-pill ${this.state_color(r.workflow_state)}">${frappe.utils.escape_html(r.workflow_state || "")}</span></td>
					<td class="text-muted">${frappe.datetime.prettyDate(r.modified)}</td>
				</tr>`
			)
			.join("");
		return `
			<section class="tva-panel">
				<h3>${__("آخر التقارير التفصيلية")}</h3>
				<table class="tva-recent"><tbody>${rows}</tbody></table>
			</section>`;
	}

	state_color(state) {
		return (
			{
				"بانتظار تحديد المونيتور": "orange",
				"قيد المراجعة من قبل المونيتور": "blue",
				"الحلقة جاهزة للعرض": "green",
				"ملغى": "red",
			}[state] || "gray"
		);
	}

	bind() {
		const d = this.data;
		this.$body.find("[data-card]").on("click", (e) => {
			const $el = $(e.currentTarget);
			const section = d.sections.find((s) => s.role === $el.data("role"));
			const c = section.cards[$el.data("card")];
			frappe.set_route("List", c.doctype, c.filters);
		});
		this.$body.find("[data-setup]").on("click", (e) => {
			e.preventDefault();
			frappe.set_route(d.setup[$(e.currentTarget).data("setup")].route);
		});
		this.$body.find(".tva-recent tr").on("click", (e) => {
			frappe.set_route("Form", "Detailed Review Report", $(e.currentTarget).data("name"));
		});
		this.$body.find("[data-action]").on("click", (e) => {
			const action = $(e.currentTarget).data("action");
			({
				"new-detailed": () => frappe.new_doc("Detailed Review Report"),
				"new-general": () => frappe.new_doc("General Review Report"),
				"new-work": () => frappe.new_doc("Archive Work"),
				"my-tasks": () =>
					frappe.set_route("List", "Detailed Review Report", {
						monitor: frappe.session.user,
						workflow_state: "قيد المراجعة من قبل المونيتور",
					}),
				progress: () => frappe.set_route("query-report", "Archive Work Progress"),
				users: () => frappe.set_route("List", "User"),
			})[action]();
		});
	}
}
