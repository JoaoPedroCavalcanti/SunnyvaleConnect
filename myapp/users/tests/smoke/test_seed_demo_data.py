"""Smoke coverage for the reusable demo-data management command."""

from io import StringIO

import pytest
from django.core.management import call_command

from condo_payments.models import CondoPaymentModel
from condominiums.models import Condominium
from reservations.models import Reservation
from service_requests.models import ServiceRequestModel
from units.models import UnitMembershipDecision
from users.models import User
from visitor_access.models import VisitorAccessModel


pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_seed_demo_data_populates_every_module_and_is_idempotent():
    condominium = Condominium.objects.create(
        name="Seed Test",
        slug="seed-test",
        code="SEEDTEST",
    )

    output = StringIO()
    call_command(
        "seed_demo_data",
        condominium_code=condominium.code,
        stdout=output,
    )
    first_counts = {
        "users": User.objects.filter(condominium=condominium).count(),
        "reservations": Reservation.objects.filter(
            condominium=condominium
        ).count(),
        "visitors": VisitorAccessModel.objects.filter(
            host_user__condominium=condominium
        ).count(),
        "requests": ServiceRequestModel.objects.filter(
            requester__condominium=condominium
        ).count(),
        "payments": CondoPaymentModel.objects.filter(
            payer_user__condominium=condominium
        ).count(),
        "history": UnitMembershipDecision.objects.filter(
            unit__condominium=condominium
        ).count(),
    }
    assert all(count > 0 for count in first_counts.values())

    call_command(
        "seed_demo_data",
        condominium_code=condominium.code,
        stdout=StringIO(),
    )
    second_counts = {
        "users": User.objects.filter(condominium=condominium).count(),
        "reservations": Reservation.objects.filter(
            condominium=condominium
        ).count(),
        "visitors": VisitorAccessModel.objects.filter(
            host_user__condominium=condominium
        ).count(),
        "requests": ServiceRequestModel.objects.filter(
            requester__condominium=condominium
        ).count(),
        "payments": CondoPaymentModel.objects.filter(
            payer_user__condominium=condominium
        ).count(),
        "history": UnitMembershipDecision.objects.filter(
            unit__condominium=condominium
        ).count(),
    }
    assert second_counts == first_counts
    assert "Demo data ready" in output.getvalue()
