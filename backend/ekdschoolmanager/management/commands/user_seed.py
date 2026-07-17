from django.core.management.base import BaseCommand
from faker import Faker

from ekdschoolmanager.models import CustomUser
from ekdschoolmanager.models import Subject

fake = Faker()

class Command(BaseCommand):
    help = "Créer 10 utilisateurs"

    def handle(self, *args, **kwargs):

        for _ in range(10):
            CustomUser.objects.create(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                is_superuser=fake.boolean(chance_of_getting_true=10),
                password=fake.password(length=10, special_chars=True, digits=True, upper_case=True, lower_case=True),
                username=fake.user_name(),
                email=fake.email(),
                phone = "+228" + fake.numerify("########"),
                gender=fake.random_element(elements=("M", "F")),
                role=fake.random_element(elements=("admin","proprietaire","enseignant","eleve","parent","comptable","secretaire","censeur","proviseur","surveillant","personnel")),
                is_archived=fake.boolean(chance_of_getting_true=10),
                date_of_birth=fake.date_of_birth(),
                address=fake.address(),
                
            )

        self.stdout.write(self.style.SUCCESS("10 utilisateurs créés"))