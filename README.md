# TV Archive · نظام أرشفة المسلسلات والبرامج

تطبيق Frappe مستقل (Frappe v16، بدون ERPNext) لدائرة الرقابة في الفضائية السورية. ينفّذ وثيقة المتطلبات FDS-2026-002 (V1.1): تقرير الرقابة التفصيلي لكل حلقة، وتقرير الرقابة العام لكل عمل، ومسار التكليف والمراجعة، والإشعارات، وصلاحيات الأدوار.

## المحتوى

| المكوّن | الوصف | المتطلب |
|---|---|---|
| `Archive Work` | العمل (مسلسل / برنامج / مادة) مع عدّاد تقدّم الحلقات | ARC-REQ-01 |
| `Detailed Review Report` | تقرير الرقابة التفصيلي، تقرير واحد لكل حلقة | ARC-REQ-02 |
| `General Review Report` | تقرير الرقابة العام، يُعبّأ تدريجياً ويُغلق ملف العمل عند اعتماده | ARC-REQ-07 |
| مسارا عمل (Workflow) | مسودة ← بانتظار تحديد المونيتور ← قيد المراجعة ← جاهزة للعرض | مصفوفة سير العمل |
| نوافذ المنسق والمونيتور | تكليف مونيتور، إعادة للمراقب، تمت المراجعة | ARC-REQ-03 |
| الإشعارات | جرس الإشعارات، وبريد إلكتروني إن كان مفعّلاً للمستخدم | ARC-REQ-04/05/06 |
| صلاحيات على مستوى السجل | المراقب يرى تقاريره، والمونيتور يرى المكلّف به فقط | ARC-ROL-01..04 |
| تقارير | تقدم الأعمال، إحصاءات المراقبين | - |
| نماذج طباعة | مطابقة لنموذجي الرقابة الورقيين، مع خانات التواقيع | - |

### الأدوار

| الدور في النظام | الاسم بالعربية |
|---|---|
| `Archive Observer` | المراقب |
| `Archive Coordinator` | المنسق / رئيس شعبة المراقبة |
| `Archive Monitor` | المونيتور |
| `Archive Director` | مدير المديرية (اطلاع فقط) |
| `System Manager` | مدير النظام |

تُنشأ الأدوار ومسارا العمل وقوائم التصنيفات وأنواع الحفظ تلقائياً عند التثبيت، ويُعاد تطبيق مسارَي العمل مع كل `bench migrate` (انظر `tv_archive/setup/install.py`).

## التطوير (frappe_docker devcontainer)

```bash
cd ~/frappe_docker/development/frappe-bench
bench get-app /path/to/tv_archive          # أو انسخ المجلد إلى apps/ ثم: bench setup requirements
bench new-site archive.localhost --db-root-password 123 \
  --mariadb-user-host-login-scope='%' --admin-password admin --install-app tv_archive
bench --site archive.localhost set-config developer_mode 1
bench start
```

بيانات تدريبية (مستخدم لكل دور، وعمل فيه حلقات في كل المراحل):

```bash
bench --site archive.localhost execute tv_archive.setup.demo.make_demo
```

كلمة مرور المستخدمين التدريبيين `Archive@2026`، والأسماء: `observer@archive.local`، `coordinator@archive.local`، `monitor@archive.local`، `director@archive.local`. لا تُشغَّل هذه الدالة على الإنتاج، وهي ترفض العمل إن لم يكن `developer_mode` أو `allow_tests` مفعّلاً.

الاختبارات:

```bash
bench --site archive.localhost set-config allow_tests true
bench --site archive.localhost run-tests --app tv_archive
```

## الإنتاج (Docker)

الصورة تُبنى من هذا المستودع مباشرة، ولا تحتاج مستودع Git بعيداً:

```bash
docker build -f docker/Containerfile -t tv-archive:1.0.0 .
cp docker/.env.example docker/.env          # غيّر كلمات المرور واسم الموقع
docker compose -f docker/compose.yaml --env-file docker/.env up -d
docker compose -f docker/compose.yaml --env-file docker/.env logs -f create-site
```

يفتح النظام على `http://SERVER:8080`. الخدمة `create-site` تنشئ الموقع وتثبّت التطبيق في أول تشغيل، وتشغّل `migrate` في كل تشغيل لاحق.

### أول دخول

- لا يظهر معالج الإعداد العام لـ Frappe: يكمله التطبيق تلقائياً (العربية، سوريا، `Asia/Damascus`، الليرة السورية) ما دام الموقع لا يضم تطبيقات أخرى.
- بعد تسجيل الدخول تفتح **الصفحة الرئيسية** (`archive-welcome`): ترحيب بالاسم، وبطاقات بما ينتظر المستخدم حسب دوره (تفتح القائمة المطابقة بالضغط عليها)، وأزرار البدء السريع، وخطوات مرور التقرير مع تمييز دور المستخدم، وإرشادات قصيرة.
- يرى مدير النظام فيها قائمة **إعداد النظام**: إنشاء المستخدمين ومنح كل واحد دوره، وبريد الإرسال، والتصنيفات.
- إذا علق موقع قديم في إعادة توجيه دائمة بين الصفحة الرئيسية ومعالج الإعداد، يصلحه `bench --site <site> migrate`.

### التحديث إلى إصدار جديد

```bash
git pull
docker build -f docker/Containerfile -t tv-archive:1.1.0 .
# عدّل ARCHIVE_TAG=1.1.0 في docker/.env
docker compose -f docker/compose.yaml --env-file docker/.env up -d
```

### النسخ الاحتياطي

```bash
docker compose -f docker/compose.yaml --env-file docker/.env exec backend \
  bench --site archive.ortas.local backup --with-files
# الملفات في volume باسم tv-archive_sites تحت sites/<site>/private/backups
```

## الترخيص

MIT
