"""Populate a condominium with deterministic, idempotent demo data."""

from datetime import date, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from condo_payments.models import CondoPaymentModel
from condominiums.models import Condominium
from delivery_notification.models import DeliveryNotificationModel
from reservations.models import Reservation, ReservableLocation
from service_requests.models import ServiceRequestModel
from shared.tenant import build_tenant_username
from sunny_vale_news.models import SunnyValeNewsModel
from units.models import Unit, UnitMembership, UnitMembershipDecision
from users.models import EmployeeType, User, UserRole
from visitor_access.models import (
    VisitorAccessModel,
    VisitorGroupMemberModel,
    VisitorGroupModel,
)


DEMO = "[DEMO]"
DEFAULT_PASSWORD = "Sunnyvale123!"
TARGET_EMAILS = (
    "adminchacon@email.com",
    "sheba@email.com",
    "nina@email.com",
)


class Command(BaseCommand):
    help = (
        "Seed every business module with repeatable demo data. Existing "
        "non-demo rows and passwords are preserved."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--condominium-code",
            help=(
                "Target condominium code. Defaults to the condominium of "
                "adminchacon@email.com."
            ),
        )
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help="Password assigned only to newly created demo users.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        condominium = self._resolve_condominium(options["condominium_code"])
        users = self._seed_users(condominium, options["password"])
        units = self._seed_units_and_memberships(condominium, users)
        locations = self._seed_locations(condominium)

        self._seed_membership_history(units, users)
        self._seed_reservations(condominium, locations, units, users)
        self._seed_visitors(users)
        self._seed_service_requests(users)
        self._seed_payments(users)
        self._seed_deliveries(units, users)
        self._seed_news(condominium, users["admin"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo data ready for {condominium.name} "
                f"({condominium.code})."
            )
        )
        self._print_summary(condominium)
        self.stdout.write(
            "Existing users kept their passwords. Newly created demo users "
            f"use: {options['password']}"
        )

    def _resolve_condominium(self, code):
        if code:
            condominium = Condominium.objects.filter(code__iexact=code).first()
        else:
            admin = (
                User.objects.select_related("condominium")
                .filter(email__iexact=TARGET_EMAILS[0])
                .first()
            )
            condominium = admin.condominium if admin else None
        if not condominium:
            raise CommandError(
                "Target condominium not found. Pass --condominium-code."
            )
        return condominium

    def _seed_users(self, condominium, password):
        specs = [
            {
                "key": "admin",
                "email": TARGET_EMAILS[0],
                "username": "admin-chacon",
                "full_name": "Admin Chacon",
                "cpf": "10000000001",
                "role": UserRole.ADMIN,
                "is_staff": True,
                "employee_types": [],
            },
            {
                "key": "sheba",
                "email": TARGET_EMAILS[1],
                "username": "Sheba",
                "full_name": "Sheba Guerreiro",
                "cpf": "10000000002",
                "role": UserRole.RESIDENT,
                "is_staff": False,
                "employee_types": [],
            },
            {
                "key": "nina",
                "email": TARGET_EMAILS[2],
                "username": "Nina",
                "full_name": "Nina Guerreira",
                "cpf": "10000000003",
                "role": UserRole.RESIDENT,
                "is_staff": False,
                "employee_types": [],
            },
            {
                "key": "doorman",
                "email": "demo.doorman@sunnyvale.test",
                "username": "demo-doorman",
                "full_name": "Porteiro Demo",
                "cpf": "10000000004",
                "role": UserRole.EMPLOYEE,
                "is_staff": False,
                "employee_types": [EmployeeType.DOORMAN],
            },
            {
                "key": "cleaner",
                "email": "demo.cleaner@sunnyvale.test",
                "username": "demo-cleaner",
                "full_name": "Limpeza Demo",
                "cpf": "10000000005",
                "role": UserRole.EMPLOYEE,
                "is_staff": False,
                "employee_types": [EmployeeType.CLEANING],
            },
            {
                "key": "resident_1",
                "email": "demo.resident01@sunnyvale.test",
                "username": "demo-resident-01",
                "full_name": "Morador Demo 01",
                "cpf": "10000000006",
                "role": UserRole.RESIDENT,
                "is_staff": False,
                "employee_types": [],
            },
            {
                "key": "resident_2",
                "email": "demo.resident02@sunnyvale.test",
                "username": "demo-resident-02",
                "full_name": "Morador Demo 02",
                "cpf": "10000000007",
                "role": UserRole.RESIDENT,
                "is_staff": False,
                "employee_types": [],
            },
            {
                "key": "pending_admin",
                "email": "demo.pending.admin@sunnyvale.test",
                "username": "demo-pending-admin",
                "full_name": "Pendente Admin Demo",
                "cpf": "10000000008",
                "role": UserRole.RESIDENT,
                "is_staff": False,
                "employee_types": [],
                "is_active": False,
            },
            {
                "key": "pending_owner",
                "email": "demo.pending.owner@sunnyvale.test",
                "username": "demo-pending-owner",
                "full_name": "Pendente Titular Demo",
                "cpf": "10000000009",
                "role": UserRole.RESIDENT,
                "is_staff": False,
                "employee_types": [],
                "is_active": False,
            },
            {
                "key": "inactive",
                "email": "demo.inactive@sunnyvale.test",
                "username": "demo-inactive",
                "full_name": "Usuário Inativo Demo",
                "cpf": "10000000010",
                "role": UserRole.RESIDENT,
                "is_staff": False,
                "employee_types": [],
                "is_active": False,
            },
        ]

        result = {}
        for spec in specs:
            defaults = {
                "username": build_tenant_username(
                    condominium.code, spec["username"]
                ),
                "full_name": spec["full_name"],
                "birth_date": date(1990, 1, 1),
                "cpf": spec["cpf"],
                "phone": "11999999999",
                "role": spec["role"],
                "employee_types": spec["employee_types"],
                "condominium": condominium,
                "is_staff": spec["is_staff"],
                "is_active": spec.get("is_active", True),
            }
            user, created = User.objects.get_or_create(
                email=spec["email"], defaults=defaults
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
            elif spec["email"].endswith("@sunnyvale.test"):
                for field, value in defaults.items():
                    setattr(user, field, value)
                user.save(
                    update_fields=[
                        "username",
                        "full_name",
                        "birth_date",
                        "cpf",
                        "phone",
                        "role",
                        "employee_types",
                        "condominium",
                        "is_staff",
                        "is_active",
                    ]
                )
            elif user.condominium_id != condominium.id:
                raise CommandError(
                    f"{user.email} belongs to another condominium."
                )
            result[spec["key"]] = user
        return result

    def _seed_units_and_memberships(self, condominium, users):
        units = list(
            Unit.objects.filter(
                condominium=condominium,
                status=Unit.Status.ACTIVE,
            ).order_by("block", "apartment", "id")
        )
        if len(units) < 5:
            for floor in range(1, 4):
                for door in ("01", "02"):
                    unit, _ = Unit.objects.get_or_create(
                        condominium=condominium,
                        kind=Unit.Kind.APARTMENT_BLOCK,
                        apartment=f"{floor}{door}",
                        block="DEMO",
                        defaults={"status": Unit.Status.ACTIVE},
                    )
                    units.append(unit)
        units = list(dict.fromkeys(units))

        primary = (
            Unit.objects.filter(
                condominium=condominium,
                apartment="1101",
                block__iexact="A",
            ).first()
            or units[0]
        )
        secondary = next((u for u in units if u.id != primary.id), units[0])
        pending_unit = next(
            (u for u in units if u.id not in {primary.id, secondary.id}),
            units[-1],
        )

        memberships = [
            (primary, users["nina"], UnitMembership.Role.OWNER, "ACTIVE"),
            (primary, users["sheba"], UnitMembership.Role.RESIDENT, "ACTIVE"),
            (
                secondary,
                users["resident_1"],
                UnitMembership.Role.OWNER,
                "ACTIVE",
            ),
            (
                secondary,
                users["resident_2"],
                UnitMembership.Role.RESIDENT,
                "ACTIVE",
            ),
            (
                pending_unit,
                users["pending_admin"],
                UnitMembership.Role.OWNER,
                UnitMembership.Status.PENDING_ADMIN,
            ),
            (
                primary,
                users["pending_owner"],
                UnitMembership.Role.RESIDENT,
                UnitMembership.Status.PENDING_OWNER,
            ),
        ]
        for unit, user, role, status in memberships:
            UnitMembership.objects.update_or_create(
                unit=unit,
                user=user,
                defaults={"role": role, "status": status},
            )
        return {
            "all": units,
            "primary": primary,
            "secondary": secondary,
            "pending": pending_unit,
        }

    def _seed_membership_history(self, units, users):
        UnitMembershipDecision.objects.filter(
            target_email__endswith="@sunnyvale.test",
            reason__startswith=DEMO,
        ).delete()
        actions = [
            (UnitMembershipDecision.Action.APPROVED, "", users["resident_1"]),
            (
                UnitMembershipDecision.Action.REJECTED,
                f"{DEMO} Cadastro incompleto.",
                users["inactive"],
            ),
            (
                UnitMembershipDecision.Action.REJECTED,
                f"{DEMO} Documento ilegível.",
                users["pending_admin"],
            ),
        ]
        for index, (action, reason, target) in enumerate(actions):
            unit = units["all"][index % len(units["all"])]
            UnitMembershipDecision.objects.create(
                unit=unit,
                unit_kind=unit.kind,
                unit_name=unit.name,
                unit_apartment=unit.apartment,
                unit_block=unit.block,
                unit_display_name=unit.display_name(),
                actor=users["admin"],
                actor_username=users["admin"].username,
                actor_full_name=users["admin"].full_name,
                target=target,
                target_username=target.username,
                target_full_name=target.full_name,
                target_email=target.email,
                action=action,
                reason=reason or f"{DEMO} Aprovado pelo administrador.",
            )

    def _seed_locations(self, condominium):
        specs = [
            (
                f"{DEMO} Churrasqueira",
                "Área gourmet com churrasqueira e mesas.",
                ReservableLocation.Icon.OUTDOOR_GRILL,
            ),
            (
                f"{DEMO} Salão de Festas",
                "Salão para eventos e confraternizações.",
                ReservableLocation.Icon.CELEBRATION,
            ),
            (
                f"{DEMO} Quadra",
                "Quadra poliesportiva.",
                ReservableLocation.Icon.SPORTS_COURT,
            ),
            (
                f"{DEMO} Sala de Reunião",
                "Espaço silencioso para reuniões.",
                ReservableLocation.Icon.MEETING_ROOM,
            ),
        ]
        result = []
        for name, description, icon in specs:
            location, _ = ReservableLocation.objects.update_or_create(
                condominium=condominium,
                name=name,
                defaults={
                    "description": description,
                    "icon": icon,
                    "is_active": True,
                },
            )
            result.append(location)
        return result

    def _seed_reservations(self, condominium, locations, units, users):
        Reservation.objects.filter(
            condominium=condominium,
            location__name__startswith=DEMO,
        ).delete()
        today = timezone.localdate()
        residents = [
            users["sheba"],
            users["nina"],
            users["resident_1"],
            users["resident_2"],
        ]
        statuses = [
            Reservation.Status.PENDING,
            Reservation.Status.APPROVED,
            Reservation.Status.REJECTED,
        ]
        start_times = [time(9, 0), time(13, 0), time(18, 0)]
        for index in range(28):
            user = residents[index % len(residents)]
            membership = (
                UnitMembership.objects.filter(
                    user=user, status=UnitMembership.Status.ACTIVE
                )
                .select_related("unit")
                .first()
            )
            start = start_times[index % len(start_times)]
            Reservation.objects.create(
                condominium=condominium,
                location=locations[index % len(locations)],
                unit=membership.unit if membership else units["primary"],
                reservation_user=user,
                reservation_date=today + timedelta(days=index - 10),
                start_time=start,
                end_time=time(min(start.hour + 2, 23), start.minute),
                guest_count=5 + index,
                status=statuses[index % len(statuses)],
            )

    def _seed_visitors(self, users):
        hosts = [users["sheba"], users["nina"], users["resident_1"]]
        VisitorAccessModel.objects.filter(
            visitor_name__startswith=DEMO,
            host_user__in=hosts,
        ).delete()
        VisitorGroupModel.objects.filter(
            name__startswith=DEMO,
            host_user__in=hosts,
        ).delete()

        now = timezone.now()
        persisted_statuses = [
            VisitorAccessModel.Status.SCHEDULED,
            VisitorAccessModel.Status.CHECKED_IN,
            VisitorAccessModel.Status.CHECKED_OUT,
            VisitorAccessModel.Status.CANCELLED,
        ]
        for index in range(20):
            status = persisted_statuses[index % len(persisted_statuses)]
            scheduled = now + timedelta(days=index - 7, hours=2)
            checkin = (
                scheduled
                if status
                in {
                    VisitorAccessModel.Status.CHECKED_IN,
                    VisitorAccessModel.Status.CHECKED_OUT,
                }
                else None
            )
            checkout = (
                scheduled + timedelta(hours=2)
                if status == VisitorAccessModel.Status.CHECKED_OUT
                else scheduled + timedelta(hours=4)
            )
            VisitorAccessModel.objects.create(
                visitor_name=f"{DEMO} Visitante {index + 1:02d}",
                host_user=hosts[index % len(hosts)],
                email=f"visitor{index + 1:02d}@sunnyvale.test",
                scheduled_date=scheduled,
                checkin_date_time=checkin,
                checkout_date_time=checkout,
                checkin_code=f"CI{index + 1:06d}",
                checkout_code=f"CO{index + 1:06d}",
                status=status,
                description=f"{DEMO} Visita para teste de status.",
                qr_access_enabled=index % 2 == 0,
                access_token=f"demo-visitor-token-{index + 1:04d}",
                access_code=f"D{index + 1:04d}",
            )

        group = VisitorGroupModel.objects.create(
            name=f"{DEMO} Família Oliveira",
            host_user=users["sheba"],
        )
        members = [
            VisitorGroupMemberModel.objects.create(
                group=group,
                name=f"Familiar {index}",
                email=f"family{index}@sunnyvale.test",
            )
            for index in range(1, 5)
        ]
        for index, member in enumerate(members):
            scheduled = now + timedelta(days=index + 2)
            VisitorAccessModel.objects.create(
                visitor_name=f"{DEMO} {member.name}",
                host_user=users["sheba"],
                visitor_group=group,
                email=member.email,
                scheduled_date=scheduled,
                checkout_date_time=scheduled + timedelta(hours=3),
                checkin_code=f"GCI{index + 1:05d}",
                checkout_code=f"GCO{index + 1:05d}",
                status=VisitorAccessModel.Status.SCHEDULED,
                description=f"{DEMO} Visita em grupo.",
                qr_access_enabled=True,
                access_token=f"demo-group-token-{index + 1:04d}",
                access_code=f"G{index + 1:04d}",
            )

    def _seed_service_requests(self, users):
        ServiceRequestModel.objects.filter(title__startswith=DEMO).delete()
        now = timezone.now()
        requesters = [
            users["sheba"],
            users["nina"],
            users["resident_1"],
            users["resident_2"],
        ]
        statuses = list(ServiceRequestModel.Status.values)
        types = list(ServiceRequestModel.ServiceType.values)
        priorities = list(ServiceRequestModel.Priority.values)
        for index in range(20):
            status = statuses[index % len(statuses)]
            responded = status != ServiceRequestModel.Status.PENDING
            ServiceRequestModel.objects.create(
                requester=requesters[index % len(requesters)],
                title=f"{DEMO} Solicitação {index + 1:02d}",
                description="Carga de teste para acompanhar o fluxo completo.",
                service_type=types[index % len(types)],
                location=f"Bloco {chr(65 + index % 3)}",
                priority=priorities[index % len(priorities)],
                request_scheduled_date=now + timedelta(days=index - 5),
                status=status,
                admin_response=(
                    f"{DEMO} Atendimento registrado."
                    if responded
                    else ""
                ),
                responded_by=users["cleaner"] if responded else None,
                responded_at=now - timedelta(days=index) if responded else None,
            )

    def _seed_payments(self, users):
        CondoPaymentModel.objects.filter(title__startswith=DEMO).delete()
        today = timezone.localdate()
        payers = [
            users["sheba"],
            users["nina"],
            users["resident_1"],
            users["resident_2"],
        ]
        statuses = ["pending", "paid", "overdue"]
        for index in range(24):
            status = statuses[index % len(statuses)]
            CondoPaymentModel.objects.create(
                payer_user=payers[index % len(payers)],
                title=f"{DEMO} Condomínio {index + 1:02d}",
                status=status,
                description="Taxa condominial de demonstração.",
                payment_link=f"https://example.test/pay/demo-{index + 1}",
                amount=Decimal("450.00") + Decimal(index * 12),
                due_date=today + timedelta(days=index - 12),
                payment_date=(
                    timezone.now() - timedelta(days=index)
                    if status == "paid"
                    else None
                ),
            )

    def _seed_deliveries(self, units, users):
        DeliveryNotificationModel.objects.filter(
            title__startswith=DEMO,
            unit__in=units["all"],
        ).delete()
        platforms = [choice[0] for choice in DeliveryNotificationModel.PLATFORMS]
        priorities = [choice[0] for choice in DeliveryNotificationModel.PRIORITY]
        holders = [users["nina"], users["resident_1"]]
        for index in range(20):
            holder = holders[index % len(holders)]
            DeliveryNotificationModel.objects.create(
                unit=units["all"][index % len(units["all"])],
                notified_holder_name=holder.full_name,
                notified_holder_email=holder.email,
                title=f"{DEMO} Entrega {index + 1:02d}",
                description="Encomenda disponível na portaria.",
                delivery_platform=platforms[index % len(platforms)],
                delivery_from=f"Loja {index + 1}",
                delivery_to=holder.full_name,
                priority_level=priorities[index % len(priorities)],
            )

    def _seed_news(self, condominium, admin):
        SunnyValeNewsModel.objects.filter(
            condominium=condominium,
            title__startswith=DEMO,
        ).delete()
        kinds = list(SunnyValeNewsModel.Kind.values)
        priorities = [choice[0] for choice in SunnyValeNewsModel.PRIORITY]
        for index in range(15):
            SunnyValeNewsModel.objects.create(
                title=f"{DEMO} Comunicado {index + 1:02d}",
                description=(
                    "Conteúdo de demonstração para testar avisos, eventos "
                    "e manutenções no aplicativo."
                ),
                kind=kinds[index % len(kinds)],
                priority_level=priorities[index % len(priorities)],
                created_by=admin,
                author=admin.full_name,
                author_role=admin.role,
                condominium=condominium,
            )

    def _print_summary(self, condominium):
        counts = {
            "users": User.objects.filter(condominium=condominium).count(),
            "units": Unit.objects.filter(condominium=condominium).count(),
            "memberships": UnitMembership.objects.filter(
                unit__condominium=condominium
            ).count(),
            "membership_history": UnitMembershipDecision.objects.filter(
                unit__condominium=condominium
            ).count(),
            "locations": ReservableLocation.objects.filter(
                condominium=condominium
            ).count(),
            "reservations": Reservation.objects.filter(
                condominium=condominium
            ).count(),
            "visitors": VisitorAccessModel.objects.filter(
                host_user__condominium=condominium
            ).count(),
            "service_requests": ServiceRequestModel.objects.filter(
                requester__condominium=condominium
            ).count(),
            "payments": CondoPaymentModel.objects.filter(
                payer_user__condominium=condominium
            ).count(),
            "deliveries": DeliveryNotificationModel.objects.filter(
                unit__condominium=condominium
            ).count(),
            "news": SunnyValeNewsModel.objects.filter(
                condominium=condominium
            ).count(),
        }
        for label, count in counts.items():
            self.stdout.write(f"  {label}: {count}")
