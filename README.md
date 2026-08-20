# Galaxy English School — Django Website

A school website built with Django 6, Tailwind CSS, and SQLite/MySQL. It includes
news, events, notices, a photo gallery, exam results lookup, an exam routine
page (one table per class), a working contact form, sitemaps, and custom
admin error pages.

---

## Local development

### 1. Environment
```bash
# From the project root (the folder containing manage.py)
copy .env.example .env        # then edit values (DEBUG=True for local)
```

### 2. Python
```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Database & static
```bash
python manage.py migrate
python manage.py createsuperuser
```

Tailwind is compiled with Node. After installing it the first time, rebuild
whenever you change a template:
```bash
npm install
npm run build:css          # one-off build -> static/css/tailwind.css
npm run watch:css          # (optional) rebuild on change while developing
```

### 4. Run
```bash
python manage.py runserver
```
Open http://127.0.0.1:8000 (admin at /admin/).

### 5. Tests
```bash
python manage.py test
```

---

## Deploying to PythonAnywhere

### 1. Push the compiled CSS (critical)
`static/css/tailwind.css` is **committed** on purpose. After any Tailwind change,
rebuild it locally and commit + push:

```bash
npm run build:css
git add static/css/tailwind.css
git commit -m "Rebuild tailwind css"
git push
```

Do **not** rely on npm on the server — the compiled file is committed so the
server never needs Node.

### 2. On PythonAnywhere — get the code
```bash
cd ~
git clone https://your-repo-url galaxy-school   # once
cd galaxy-school
git pull                                        # on every deploy
```

### 3. Set up the environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` from `.env.example` **with your real values** (critical):
```bash
cp .env.example .env
nano .env
```
At minimum set:
```ini
DEBUG=False
SECRET_KEY=<a long random string>
ALLOWED_HOSTS=<your-pythonanywhere-domain>
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<your-smtp-host>
EMAIL_HOST_USER=<smtp-user>
EMAIL_HOST_PASSWORD=<smtp-password>
```

### 4. Migrate + collect static
```bash
python manage.py migrate
python manage.py collectstatic --noinput   # required — fills staticfiles/
```

### 5. Configure the Web app in the dashboard
- **Source code:** `/home/<your-user>/galaxy-school`
- **Working directory:** `/home/<your-user>/galaxy-school`
- **Virtualenv:** `/home/<your-user>/galaxy-school/.venv`
- **WSGI configuration file:** point to `config/wsgi.py` (see the per-app WSGI
  tab setting, e.g. `/home/<your-user>/galaxy-school/config/wsgi.py`).

Because **Whitenoise** is installed (`config/wsgi.py` + middleware), static files
are served automatically by your WSGI app — you do **not** need a separate
"Static files" URL mapping in the dashboard. (If you add one, map URL `/static/`
to `/home/<your-user>/galaxy-school/staticfiles`.)

### 6. Reload
Click **Reload** on the Web tab. Open your site; CSS should be applied.

---

## Project layout
```
apps/core/       School settings, home/about/admissions/contact views, image utils
apps/academics/  Programs, exams, exam routine, results
apps/content/    News, notices, events, gallery
config/          settings.py, urls.py, wsgi.py/asgi.py
templates/       base.html + per-page/component templates
static/          css (tailwind build + custom), js
```

## Notable config
- `DEBUG` defaults **ON** locally, **OFF** on the server (from `.env`).
- Production refuses to boot without a real `SECRET_KEY`.
- `SchoolSettings` is cached; edit it in admin to update the whole site.
- Image uploads are auto-resized/compressed on save (`apps/core/image_utils.py`).
