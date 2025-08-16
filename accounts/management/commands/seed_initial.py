from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Seed initial data: superuser and a couple of sample users/categories"

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin", help="Superuser username")
        parser.add_argument("--email", default="admin@example.com", help="Superuser email")
        parser.add_argument(
            "--password",
            default=None,
            help="Superuser password (omit to prompt or use DJANGO_SUPERUSER_PASSWORD env)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        email = options["email"]
        password = options["password"]

        su, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        if created:
            if password:
                su.set_password(password)
            else:
                # If no password provided, set unusable; admin can reset later via changepassword
                su.set_unusable_password()
            su.save()
            self.stdout.write(self.style.SUCCESS(f"Created superuser '{username}'"))
        else:
            self.stdout.write(f"Superuser '{username}' already exists")

        # Create a couple of sample non-staff users if they don't exist
        for uname in ("alice", "bob"):
            if not User.objects.filter(username=uname).exists():
                User.objects.create_user(
                    username=uname, email=f"{uname}@example.com", password="password123"
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Created user '{uname}' (password: password123)")
                )

        self.stdout.write(self.style.SUCCESS("Seeding complete."))
