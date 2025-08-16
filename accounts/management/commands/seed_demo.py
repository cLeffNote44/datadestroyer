import random

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from documents.models import Document, DocumentCategory
from forum.models import ForumCategory, Post, Topic
from messaging.models import Message, MessageThread, ThreadParticipant

LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
)


class Command(BaseCommand):
    help = "Seed a demo dataset: users, document categories/docs, forum topics/posts, and messages"

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        # Ensure base users exist
        users = {}
        for uname in ("alice", "bob", "charlie"):
            user, _ = User.objects.get_or_create(
                username=uname,
                defaults={"email": f"{uname}@example.com"},
            )
            if not user.password:
                user.set_password("password123")
                user.save(update_fields=["password"])
            users[uname] = user
        self.stdout.write(
            self.style.SUCCESS("Users ensured: alice, bob, charlie (password: password123)")
        )

        # Document categories and documents
        cat_specs = [
            ("Reports", "reports", False),
            ("Photos", "photos", False),
            ("Sensitive", "sensitive", True),
        ]
        categories = []
        for name, slug, sens in cat_specs:
            cat, _ = DocumentCategory.objects.get_or_create(
                name=name, slug=slug, defaults={"is_sensitive": sens}
            )
            categories.append(cat)
        self.stdout.write(self.style.SUCCESS("Document categories ensured."))

        # Create a few small text docs for users
        for uname, owner in users.items():
            for idx in range(1, 3):
                title = f"{uname.capitalize()} Doc {idx}"
                content = ContentFile(
                    f"{title}\n\n{LOREM}".encode("utf-8"), name=f"{uname}_doc_{idx}.txt"
                )
                cat = random.choice(categories)
                doc, created = Document.objects.get_or_create(
                    owner=owner,
                    title=title,
                    defaults={
                        "category": cat,
                        "description": LOREM,
                        "file": content,
                        "file_size": len(content.read() or b"") if hasattr(content, "read") else 0,
                        "file_hash": "",
                        "mime_type": "text/plain",
                    },
                )
        self.stdout.write(self.style.SUCCESS("Sample documents created."))

        # Forum: category, topics, posts
        fcat, _ = ForumCategory.objects.get_or_create(name="General", slug="general")
        for uname, author in users.items():
            topic, _ = Topic.objects.get_or_create(
                category=fcat,
                author=author,
                title=f"Welcome from {uname.capitalize()}!",
                defaults={"retention_date": None},
            )
            for i in range(2):
                Post.objects.get_or_create(
                    topic=topic,
                    author=author,
                    content=f"Post {i+1} by {uname}. {LOREM}",
                )
        self.stdout.write(self.style.SUCCESS("Forum topics and posts created."))

        # Messaging: create a thread with all participants and messages
        thread, _ = MessageThread.objects.get_or_create(
            subject="Demo Chat",
            created_by=users["alice"],
        )
        for u in users.values():
            ThreadParticipant.objects.get_or_create(thread=thread, user=u)
        messages = [
            (users["alice"], users["bob"], "Hi Bob!"),
            (users["bob"], users["alice"], "Hi Alice, what's up?"),
            (users["charlie"], None, "Hey folks, this is a demo message."),
        ]
        for sender, recipient, text in messages:
            Message.objects.get_or_create(
                thread=thread,
                sender=sender,
                recipient=recipient,
                content=text,
                defaults={"delivered_at": timezone.now()},
            )
        self.stdout.write(self.style.SUCCESS("Messaging thread with sample messages created."))

        self.stdout.write(self.style.SUCCESS("Demo dataset seeded successfully."))
