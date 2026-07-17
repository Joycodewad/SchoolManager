from django.core.management.base import BaseCommand
from faker import Faker

from backend.ekdschoolmanager.models import Subject
from backend.ekdschoolmanager.models import School
fake = Faker()

class Command(BaseCommand):
    help = "Créer 100 matières"

    def handle(self, *args, **kwargs):

        for _ in range(10):
            Subject.objects.create(
                school = fake.random_element(elements=School.objects.all()),
                name=fake.word(),
                code=fake.unique.word(),                
                description=fake.text(),
                is_active=fake.boolean(chance_of_getting_true=90),
                created_at=fake.date_time_this_decade(),
            )

        self.stdout.write(self.style.SUCCESS("100 matières créées"))
