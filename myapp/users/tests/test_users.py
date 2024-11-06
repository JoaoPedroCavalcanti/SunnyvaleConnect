from django.test import TestCase

# from django.urls import reverse
from faker import Faker


class UserAuthenticationTests(TestCase):
    def test_tests(self):
        fake = Faker()
        print(fake.name())
        self.assertEqual(1, 1)
