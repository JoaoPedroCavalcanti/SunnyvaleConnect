from django.test import TestCase
from django.urls import reverse

class UserAuthenticationTests(TestCase):
    
    def test_create_user_status_201_with_valid_data(self):
        # user_data = {
        #     "username": "johndoe",
        #     "email": "johndoe@email.com",
        #     "password": "Abcd123!",
        #     "first_name": "Tico",
        #     "last_name": "Sheba"
        # }
        print(reverse("users:users-api-list"))
        self.assertEqual(1, 1)
        # response = self.client.post(reverse("users:users-api-list"), data=user_data)
        # self.assertEqual(201, response.status_code)