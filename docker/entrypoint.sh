#!/bin/bash
set -e

# Wait for postgres to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! nc -z db 5432; do
  sleep 0.5
done
echo "PostgreSQL is up!"

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
while ! nc -z redis 6379; do
  sleep 0.5
done
echo "Redis is up!"

cd backend

# Run tests if TEST_MODE is enabled
if [ "${TEST_MODE}" = "true" ]; then
  echo "Running tests..."
  # Run tests for each app individually
  python manage.py test apps.accounts.SimpleTest --verbosity=2
  # If tests fail, exit with error
  if [ $? -ne 0 ]; then
    echo "Tests failed. Exiting..."
    exit 1
  fi
  echo "All tests passed!"
fi

# Run migrations
echo "Applying database migrations..."
python manage.py makemigrations --noinput
# First migrate the built-in apps
echo "Migrating built-in apps first..."
python manage.py migrate auth --noinput
python manage.py migrate contenttypes --noinput
python manage.py migrate admin --noinput
python manage.py migrate sessions --noinput
# Then migrate our custom apps
echo "Migrating custom apps..."
python manage.py migrate accounts --noinput
python manage.py migrate medical --noinput
python manage.py migrate chat --noinput
python manage.py migrate audit --noinput
# Finally migrate any remaining apps
echo "Migrating remaining apps..."
python manage.py migrate --noinput

# Create superuser if it doesn't exist
echo "Creating superuser (if not exists)..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
from apps.accounts.models import Role, Language
User = get_user_model()
email = "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}"
password = "${DJANGO_SUPERUSER_PASSWORD:-adminpass}"

# Create languages first
english, _ = Language.objects.get_or_create(code='en')
spanish, _ = Language.objects.get_or_create(code='es')
french, _ = Language.objects.get_or_create(code='fr')
arabic, _ = Language.objects.get_or_create(code='ar')
hindi, _ = Language.objects.get_or_create(code='hi')

if not User.objects.filter(email=email).exists():
    # Ensure admin role exists
    admin_role, _ = Role.objects.get_or_create(name='administrator')
    # Create superuser with admin role
    user = User.objects.create_superuser(email=email, password=password)
    user.role = admin_role
    user.language = english  # Use the language object, not the string
    user.save()
    print(f"Superuser with email {email} created")
else:
    print(f"Superuser with email {email} already exists")
EOF

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create vector extension if needed
echo "Creating pg_vector extension if needed..."
PGPASSWORD=${POSTGRES_PASSWORD} psql -h db -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "CREATE EXTENSION IF NOT EXISTS vector;" || echo "Skipping PGVector creation"

# Start server based on environment
if [ "${DJANGO_ENV}" = "production" ]; then
  echo "Starting Gunicorn server..."
  gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
else
  echo "Starting Django development server..."
  # Use --verbosity=1 to reduce logging output
  python manage.py runserver 0.0.0.0:8000 --verbosity=1
fi