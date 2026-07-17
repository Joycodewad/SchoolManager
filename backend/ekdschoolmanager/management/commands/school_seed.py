from django.core.management.base import BaseCommand
from faker import Faker

from ekdschoolmanager.models import School
from ekdschoolmanager.models import CustomUser
# fake = Faker()
# Créer des écoles et propriétaires sans le fake

class Command(BaseCommand):
    help = "Create default school"

    def handle(self, *args, **kwargs):
        schools = [
            {
                "name": "Excellence High School",
                "code": "EXHS001",
                "logo": "https://example.com/logo1.png",
                "owner": CustomUser.objects.get(id=3),  # Assuming the owner is the first user created
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "name": "Global Academy",
                "code": "GA002",
                "logo": "https://example.com/logo2.png",
                "owner": CustomUser.objects.get(id=3),  # Assuming the owner is the second user created
                "is_active": True,
                "created_at": "2024-01-02T00:00:00Z",
            },
            {
                "name": "Sunrise International School",
                "code": "SIS003",
                "logo": "https://example.com/logo3.png",
                "owner": CustomUser.objects.get(id=3),  # Assuming the owner is the third user created
                "is_active": True,
                "created_at": "2024-01-03T00:00:00Z",
            },
            {
                "name": "Harmony Academy",
                "code": "HA004",
                "logo": "https://example.com/logo4.png",
                "owner": CustomUser.objects.get(id=3),  # Assuming the owner is the fourth user created
                "is_active": True,
                "created_at": "2024-01-04T00:00:00Z",
            },
            {
                "name": "Bright Future School",
                "code": "BFS005",
                "logo": "https://example.com/logo5.png",
                "owner": CustomUser.objects.get(id=3),  # Assuming the owner is the fifth user created
                "is_active": True,
                "created_at": "2024-01-05T00:00:00Z",
            },
            {
                "name": "Elite Scholars Academy",
                "code": "ESA006",
                "logo": "https://example.com/logo6.png",
                "owner": CustomUser.objects.get(id=3),  # Assuming the owner is the sixth user created
                "is_active": True,
                "created_at": "2024-01-06T00:00:00Z",
            },
            {
                "name": "Rising Stars School",
                "code": "RSS007",
                "logo": "https://example.com/logo7.png",
                "owner": CustomUser.objects.get(id=3),  # Assuming the owner is the seventh user created
                "is_active": True,
                "created_at": "2024-01-07T00:00:00Z",
            },
            {
                "name": "Innovators Academy",
                "code": "IA008",
                "logo": "https://example.com/logo8.png",
                "owner": CustomUser.objects.get(id=3),  # Assuming the owner is the eighth user created
                "is_active": True,
                "created_at": "2024-01-08T00:00:00Z",
            },
            {
                "name": "Visionary High School",
                "code": "VHS009",
                "logo": "https://example.com/logo9.png",
                "owner": CustomUser.objects.get(id=3),  # Assuming the owner is the ninth user created
                "is_active": True,
                "created_at": "2024-01-09T00:00:00Z",
            },
            {
                "name": "Global Leaders Academy",
                "code": "GLA010",
                "logo": "https://example.com/logo10.png",
                "owner": CustomUser.objects.get(id=3),  # Assuming the owner is the tenth user created
                "is_active": True,
                "created_at": "2024-01-10T00:00:00Z",
            }
        ]  

        for school in schools:
            School.objects.get_or_create(
            name=school["name"],
            defaults=school
        )
        # school, created = School.objects.get_or_create(
        #     name="Excellence High School",
        #     defaults={
        #         "email": "contact@excellence.edu",
        #         "phone": "+22890000000",
        #         "address": "Lomé, Togo",
        #         "city": "Lomé",
        #         "country": "Togo",
        #     }
        # )
        
        self.stdout.write(self.style.SUCCESS("10 écoles créées"))






# class Command(BaseCommand):
#     help = "Créer 10 écoles"

#     def handle(self, *args, **kwargs):

#         for _ in range(10):
#             School.objects.create(
#                 name=fake.company(),
#                 code=fake.word(),
#                 logo = fake.image_url(),
#                 owner = fake.random_element(elements=CustomUser.objects.filter(role='proprietaire')),
#                 is_active=fake.boolean(chance_of_getting_true=90),
#                 creatd_at=fake.date_time_this_decade(),
#             )

#         self.stdout.write(self.style.SUCCESS("10 écoles créées"))