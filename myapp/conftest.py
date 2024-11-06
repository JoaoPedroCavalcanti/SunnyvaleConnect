import django
import pytest
from django.conf import settings

# Inicialize o Django antes de qualquer coisa
django.setup()


@pytest.fixture(autouse=True, scope="session")
def django_db_setup():
    settings.DATABASES["default"]["TEST"] = {
        "NAME": "test_" + settings.DATABASES["default"]["NAME"],
        "MIRROR": None,
    }
