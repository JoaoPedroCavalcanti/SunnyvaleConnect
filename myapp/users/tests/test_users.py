from visitor_access.views import VisitorAccessViewSet
from django.test import TestCase
from model_bakery import baker
from users.models import Profile

# from django.urls import reverse
from faker import Faker
# from users.models import Profile


class UserAuthenticationTests(TestCase):
    def test_tests(self):
        fake = Faker()
        customer = baker.make(Profile)
        print(fake.name())
        print(f"customer: {customer.user.username}")
        self.assertEqual(1, 1)
