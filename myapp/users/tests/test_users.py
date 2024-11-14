from django.contrib.auth import get_user_model
from tests_base.base_tests_user import BaseTestsUsers
from django.urls import reverse
from faker import Faker

User = get_user_model()
fake = Faker()


class UserAuthenticationTests(BaseTestsUsers):
    def setUp(self):
        return super().setUp()

    def test_create_user_status_201_with_valid_data(self):
        user_to_be_created = self.create_random_user_from_faker()

        response = self.client.post(
            reverse("users:users-api-list"), data=user_to_be_created
        )

        self.assertEqual(response.status_code, 201)

    def test_create_user_status_400_with_invalid_data(self):
        user_with_wrong_data = self.create_random_user_from_faker()

        user_with_wrong_data.update(
            {"username": "", "email": "wrongemail", "password": "a"}
        )

        response = self.client.post(
            reverse("users:users-api-list"), data=user_with_wrong_data
        )

        self.assertEqual(400, response.status_code)


class UserValidationTests(BaseTestsUsers):
    def setUp(self):
        return super().setUp()

    # USERNAME
    def test_create_user_status_400_and_message_when_username_is_missing(self):
        user = self.create_random_user_from_faker()
        del user["username"]

        response = self.client.post(reverse("users:users-api-list"), data=user)

        error_message = response.data["username"][0].__str__()

        self.assertEqual(400, response.status_code)
        self.assertEqual("This field is required.", error_message)

    def test_create_user_status_400_and_message_when_username_already_exists(self):
        # self.user_a already exists
        user = self.create_random_user_from_faker()
        user.update({"username": self.user_a.username})

        response = self.client.post(reverse("users:users-api-list"), data=user)

        error_message = response.data["username"][0].__str__()

        self.assertEqual(400, response.status_code)
        self.assertEqual("A user with that username already exists.", error_message)

    # EMAIL
    def test_create_user_status_400_and_message_when_email_is_missing(self):
        user = self.create_random_user_from_faker()
        del user["email"]

        response = self.client.post(reverse("users:users-api-list"), data=user)

        error_message = response.data["email"][0].__str__()

        self.assertEqual(400, response.status_code)
        self.assertEqual("This field is required.", error_message)

    def test_create_user_status_400_and_message_when_email_is_invalid_format(self):
        user = self.create_random_user_from_faker()
        user.update({"email": "invalid_email_format"})

        response = self.client.post(reverse("users:users-api-list"), data=user)

        error_message = response.data["email"][0].__str__()

        self.assertEqual(400, response.status_code)
        self.assertEqual("Enter a valid email address.", error_message)

    def test_create_user_status_400_and_message_when_email_already_exists(self):
        # self.user_a already exists
        user = self.create_random_user_from_faker()
        user.update({"email": self.user_a.email})

        response = self.client.post(reverse("users:users-api-list"), data=user)

        error_message = response.data["email"][0].__str__()

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "An account with this email address already exists.", error_message
        )

    # PASSWORD
    def test_create_user_status_400_and_message_when_password_is_missing(self):
        user = self.create_random_user_from_faker()
        del user["password"]

        response = self.client.post(reverse("users:users-api-list"), data=user)

        error_message = response.data["password"][0].__str__()

        self.assertEqual(400, response.status_code)
        self.assertEqual("This field is required.", error_message)

    def test_create_user_status_400_and_message_when_password_does_not_meet_complexity_requirements(
        self,
    ):
        user = self.create_random_user_from_faker()
        user.update({"password": "a"})

        response = self.client.post(reverse("users:users-api-list"), data=user)

        # Extrai as mensagens de erro
        error_messages = [str(error) for error in response.data["password"]]

        expected_errors = [
            "Password must contain at least one uppercase letter.",
            "Password must be at least 8 characters long.",
            "Password must be have at least 1 special character(ex: !$%*<).",
        ]

        # Testa se o status foi 400
        self.assertEqual(400, response.status_code)

        # Verifica se a lista de erros está exatamente como esperado
        self.assertListEqual(error_messages, expected_errors)

    # FIRST NAME
    def test_create_user_status_400_and_message_when_first_name_is_missing(self):
        user = self.create_random_user_from_faker()
        del user["first_name"]

        response = self.client.post(reverse("users:users-api-list"), data=user)

        error_message = response.data["first_name"][0].__str__()

        self.assertEqual(400, response.status_code)
        self.assertEqual("This field is required.", error_message)

    # LAST NAME
    def test_create_user_status_400_and_message_when_last_name_is_missing(self):
        user = self.create_random_user_from_faker()
        del user["last_name"]

        response = self.client.post(reverse("users:users-api-list"), data=user)

        error_message = response.data["last_name"][0].__str__()

        self.assertEqual(400, response.status_code)
        self.assertEqual("This field is required.", error_message)
