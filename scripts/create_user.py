import os
import sys
import django

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "osint_platform.settings.development")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin_password')
    print("User 'admin' created.")
else:
    u = User.objects.get(username='admin')
    u.set_password('admin_password')
    u.save()
    print("User 'admin' password reset.")
