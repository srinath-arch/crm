# Fieldnote CRM

A Django CRM for sales teams to manage customer relationships, contacts, deal stages, and customer activity. The application uses MySQL in production and SQLite by default for local development and tests.

## Start locally

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000`. Sign in with the superuser or create a sales user from `/admin/`. Staff users can see and assign records across the team; non-staff users can access only customers they own and the deals linked to those customers.

## MySQL configuration

Create a MySQL database using `utf8mb4`, then set these environment variables before running Django commands:

```sh
export DB_ENGINE=mysql
export DB_NAME=crm
export DB_USER=crm
export DB_PASSWORD='your-local-password'
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DJANGO_SECRET_KEY='replace-with-a-long-random-value'
export DJANGO_DEBUG=false
export DJANGO_ALLOWED_HOSTS='crm.example.com'
python manage.py migrate
```

`mysqlclient` needs the MySQL development headers at install time on systems that do not provide a prebuilt wheel.

## Features

- Customer and contact create, detail, edit, and delete workflows.
- Deals with Lead, Contacted, Proposal, Won, and Lost stages, expected close date, value, and owner.
- Customer notes, calls, emails, and meetings in a chronological activity log.
- Customer and deal search; stage and owner filters. Owner filters are available to staff.
- Customer CSV import and export. Imports accept `name,company,email,phone`, update an existing record with the same email for that owner, and use batched bulk writes. Files are limited to 5 MB and 10,000 rows.
- Staff-only Django admin, user ownership rules, dashboard metrics, and recent activity.
- Indexes on customer email, customer owner, and deal stage.

## Seed and benchmark

Create a sales user in the admin, then add a representative-sized sample dataset:

```sh
python manage.py seed_customers --owner maya --count 1000
```

The benchmark compares the original row-by-row upsert pattern with the optimized bulk import for the same row count. It rolls back all generated records when finished:

```sh
python manage.py benchmark_customer_import --owner maya --count 1000
```

Run it against the same database and machine before and after changing the importer to compare results fairly. It prints elapsed time and speedup; timings vary with database, indexes, and hardware.

## Backups

The MySQL backup script writes a timestamped compressed SQL dump under `BACKUP_DIR` (default `./backups`). Set `DB_NAME`, `DB_USER`, and optionally `DB_HOST`, `DB_PORT`, and `BACKUP_DIR`. Provide credentials through the MySQL client option file or the environment used by your scheduler; do not put passwords in crontab arguments.

Example daily cron entry (adjust the project path and environment file):

```cron
15 2 * * * cd /srv/fieldnote && set -a && . ./.env && set +a && bash scripts/backup_mysql.sh >> /var/log/fieldnote-backup.log 2>&1
```

Backups contain customer data. Restrict directory access, define a retention policy, and periodically test restoring a dump.

## Tests and deployment

```sh
python manage.py test crm.tests
python manage.py check --deploy
python manage.py collectstatic --noinput
```

For production, set a strong `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, and the exact trusted host names; terminate HTTPS at the application proxy and configure secure cookies and proxy settings for your hosting environment. Run migrations as part of deployment. `check --deploy` intentionally reports security settings that must be finalized for the chosen hosting platform.