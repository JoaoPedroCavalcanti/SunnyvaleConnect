from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import date, time

from django.utils import timezone

from reservations.models import Reservation, ReservationDecision
from reservations.repositories.reservable_location_repository import (
    IReservableLocationRepository,
)
from reservations.repositories.reservation_decision_repository import (
    IReservationDecisionRepository,
)
from reservations.repositories.reservation_repository import (
    IReservationRepository,
)
from shared.availability import AvailabilityRange, build_availability_range
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.infrastructure.email_sender import IEmailSender
from shared.roles import ensure_not_employee, is_admin
from shared.tenant import (
    assert_same_condominium,
    is_platform_superuser,
    require_condominium_id,
)
from shared.time_slots import slots_overlap, slots_too_close
from units.repositories.unit_membership_repository import (
    IUnitMembershipRepository,
)
from users.repositories.user_repository import IUserRepository


_MAX_AVAILABILITY_DAYS = 93


class IReservationService(ABC):
    @abstractmethod
    def list(
        self,
        user,
        *,
        status: str | None = None,
        period: str | None = None,
        condominium_id: int | None = None,
        location_id: int | None = None,
    ): ...

    @abstractmethod
    def availability(
        self,
        user,
        location_id: int,
        *,
        from_date: date,
        to_date: date,
    ) -> AvailabilityRange: ...

    @abstractmethod
    def get(self, user, pk: int) -> Reservation: ...

    @abstractmethod
    def create(self, user, payload: dict) -> Reservation: ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict) -> Reservation: ...

    @abstractmethod
    def delete(self, user, pk: int) -> None: ...

    @abstractmethod
    def approve(self, user, pk: int) -> Reservation: ...

    @abstractmethod
    def reject(
        self, user, pk: int, reason: str = ""
    ) -> Reservation: ...


class ReservationService(IReservationService):
    def __init__(
        self,
        repository: IReservationRepository,
        location_repository: IReservableLocationRepository,
        membership_repository: IUnitMembershipRepository,
        user_repository: IUserRepository,
        email_sender: IEmailSender,
        decision_repository: IReservationDecisionRepository,
    ):
        self._repo = repository
        self._locations = location_repository
        self._memberships = membership_repository
        self._users = user_repository
        self._email = email_sender
        self._decisions = decision_repository

    def list(
        self,
        user,
        *,
        status=None,
        period=None,
        condominium_id=None,
        location_id=None,
    ):
        ensure_not_employee(user, action="acessar reservas")
        normalized = self._normalize_status(status)
        normalized_period = self._normalize_period(period)
        normalized_location = self._normalize_location_id(location_id)
        tenant_id = self._list_tenant_id(user, condominium_id)
        reference = None
        if normalized_period:
            reference = (
                timezone.localdate(),
                timezone.localtime().time().replace(tzinfo=None),
            )
        if is_admin(user):
            return self._repo.list_for_condominium(
                tenant_id,
                status=normalized,
                period=normalized_period,
                reference=reference,
                location_id=normalized_location,
            )
        return self._repo.list_for_user(
            user.id,
            tenant_id,
            status=normalized,
            period=normalized_period,
            reference=reference,
            location_id=normalized_location,
        )

    def availability(
        self, user, location_id, *, from_date, to_date
    ):
        ensure_not_employee(user, action="acessar reservas")
        self._validate_availability_range(from_date, to_date)
        location = self._active_location_for_user(user, location_id)
        blocking_by_date = defaultdict(list)
        for item in self._repo.list_blocking_between(
            location.id, from_date, to_date
        ):
            blocking_by_date[item.reservation_date].append(item)
        return build_availability_range(
            from_date=from_date,
            to_date=to_date,
            blocking_by_date=blocking_by_date,
        )

    def get(self, user, pk):
        ensure_not_employee(user, action="acessar reservas")
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("Reserva não encontrada.")
        assert_same_condominium(user, instance.condominium_id)
        if not is_admin(user) and instance.reservation_user_id != user.id:
            raise NotFoundError("Reserva não encontrada.")
        return instance

    def create(self, user, payload):
        ensure_not_employee(user, action="fazer reservas")
        data = dict(payload)
        location = self._active_location_for_user(
            user, data.pop("location_id")
        )
        target_user = self._resolve_reservation_user(
            user,
            data.pop("reservation_user_id", None),
            location.condominium_id,
        )
        unit = self._first_active_unit(
            target_user, location.condominium_id, requester=user
        )
        self._validate_start(
            data["reservation_date"],
            data.get("start_time"),
        )
        self._validate_slot(
            location.id,
            data["reservation_date"],
            data.get("start_time"),
            data.get("end_time"),
        )
        data.update(
            {
                "condominium": location.condominium,
                "location": location,
                "reservation_user": target_user,
                "unit": unit,
                "status": (
                    Reservation.Status.APPROVED
                    if is_admin(user)
                    else Reservation.Status.PENDING
                ),
            }
        )
        created = self._repo.create(data)
        if created.status == Reservation.Status.APPROVED:
            self._record_decision(
                created,
                actor=user,
                action=ReservationDecision.Action.APPROVED,
                reason="",
            )
        return created

    def update(self, user, pk, payload):
        ensure_not_employee(user, action="fazer reservas")
        instance = self.get(user, pk)
        if instance.status not in {
            Reservation.Status.PENDING,
            Reservation.Status.APPROVED,
        }:
            raise BusinessRuleError(
                "Apenas reservas pendentes ou aprovadas podem ser editadas.",
                field="status",
            )
        if self._is_past(instance):
            raise BusinessRuleError(
                "Reservas passadas não podem ser editadas.",
                field="reservation_date",
            )
        data = dict(payload)
        if "location_id" in data:
            raise BusinessRuleError(
                "O local da reserva não pode ser alterado.",
                field="location_id",
            )
        if "status" in data:
            raise BusinessRuleError(
                "O status da reserva não pode ser alterado diretamente.",
                field="status",
            )
        location = instance.location
        target_user = instance.reservation_user
        if "reservation_user_id" in data:
            target_user = self._resolve_reservation_user(
                user,
                data.pop("reservation_user_id"),
                location.condominium_id,
            )
            data["reservation_user"] = target_user
            data["unit"] = self._first_active_unit(
                target_user,
                location.condominium_id,
                requester=user,
            )
        if target_user and target_user.condominium_id != location.condominium_id:
            raise NotFoundError("Usuário da reserva não encontrado.")
        reservation_date = data.get(
            "reservation_date", instance.reservation_date
        )
        start_time = data.get("start_time", instance.start_time)
        end_time = data.get("end_time", instance.end_time)
        self._validate_start(reservation_date, start_time)
        self._validate_slot(
            location.id,
            reservation_date,
            start_time,
            end_time,
            exclude_id=instance.id,
        )
        data.update(
            {
                "location": location,
                "condominium": location.condominium,
            }
        )
        return self._repo.update(instance, data)

    def delete(self, user, pk):
        ensure_not_employee(user, action="fazer reservas")
        instance = self.get(user, pk)
        if instance.status not in {
            Reservation.Status.PENDING,
            Reservation.Status.APPROVED,
        }:
            raise BusinessRuleError(
                "Apenas reservas pendentes ou aprovadas podem ser excluídas.",
                field="status",
            )
        if self._is_past(instance):
            raise BusinessRuleError(
                "Reservas passadas não podem ser excluídas.",
                field="reservation_date",
            )
        self._repo.delete(instance)

    def approve(self, user, pk):
        self._ensure_staff(user, "aprovar")
        instance = self.get(user, pk)
        if instance.status == Reservation.Status.APPROVED:
            return instance
        self._validate_start(
            instance.reservation_date,
            instance.start_time,
        )
        self._validate_slot(
            instance.location_id,
            instance.reservation_date,
            instance.start_time,
            instance.end_time,
            exclude_id=instance.id,
        )
        updated = self._repo.update(
            instance, {"status": Reservation.Status.APPROVED}
        )
        self._record_decision(
            updated,
            actor=user,
            action=ReservationDecision.Action.APPROVED,
            reason="",
        )
        self._notify(updated, approved=True)
        return updated

    def reject(self, user, pk, reason=""):
        self._ensure_staff(user, "rejeitar")
        if not reason or not reason.strip():
            raise BusinessRuleError(
                "O motivo da rejeição é obrigatório.", field="reason"
            )
        instance = self.get(user, pk)
        if instance.status == Reservation.Status.REJECTED:
            return instance
        updated = self._repo.update(
            instance, {"status": Reservation.Status.REJECTED}
        )
        self._record_decision(
            updated,
            actor=user,
            action=ReservationDecision.Action.REJECTED,
            reason=reason.strip(),
        )
        self._notify(updated, approved=False, reason=reason)
        return updated

    def _active_location_for_user(self, user, location_id):
        location = self._locations.get_by_id(location_id)
        if not location or not location.is_active:
            raise NotFoundError("Local reservável não encontrado.")
        assert_same_condominium(user, location.condominium_id)
        return location

    def _resolve_reservation_user(
        self, requester, user_id, condominium_id
    ):
        if not is_admin(requester):
            if user_id is not None and user_id != requester.id:
                raise PermissionDeniedError(
                    "Moradores só podem criar reservas para si mesmos."
                )
            return requester
        if user_id is None:
            if (
                getattr(requester, "condominium_id", None)
                != condominium_id
            ):
                return None
            return requester
        target = self._users.get_by_id(user_id)
        if not target or target.condominium_id != condominium_id:
            raise NotFoundError("Usuário da reserva não encontrado.")
        return target

    def _first_active_unit(
        self, target_user, condominium_id, *, requester
    ):
        if target_user is None and is_admin(requester):
            return None
        for membership in self._memberships.list_active_for_user(
            target_user.id
        ):
            if membership.unit.condominium_id == condominium_id:
                return membership.unit
        if is_admin(requester):
            return None
        raise BusinessRuleError(
            "O usuário deve pertencer a uma unidade ativa para reservar este local."
        )

    def _validate_slot(
        self,
        location_id,
        reservation_date,
        start_time,
        end_time,
        *,
        exclude_id=None,
    ):
        if start_time and end_time and start_time >= end_time:
            raise BusinessRuleError(
                "start_time deve ser anterior a end_time.",
                field="start_time",
            )
        existing_items = self._repo.list_blocking_for_location_date(
            location_id,
            reservation_date,
            exclude_id=exclude_id,
        )
        for existing in existing_items:
            if slots_overlap(
                start_time,
                end_time,
                existing.start_time,
                existing.end_time,
            ):
                raise BusinessRuleError(
                    "Este local já possui uma reserva nesse horário.",
                    field="reservation_date",
                )
            if slots_too_close(
                start_time,
                end_time,
                existing.start_time,
                existing.end_time,
            ):
                raise BusinessRuleError(
                    "As reservas devem ter ao menos 30 minutos de intervalo entre elas.",
                    field="start_time",
                )

    @staticmethod
    def _validate_start(reservation_date, start_time):
        today = timezone.localdate()
        if reservation_date < today:
            raise BusinessRuleError(
                "Não é possível fazer reservas para uma data passada.",
                field="reservation_date",
            )
        current_time = timezone.localtime().time().replace(tzinfo=None)
        if reservation_date == today and (start_time or time.min) < current_time:
            raise BusinessRuleError(
                "A reserva não pode começar em um horário passado.",
                field="start_time",
            )

    @staticmethod
    def _is_past(instance) -> bool:
        today = timezone.localdate()
        if instance.reservation_date < today:
            return True
        if instance.reservation_date > today or instance.end_time is None:
            return False
        current_time = timezone.localtime().time().replace(tzinfo=None)
        return instance.end_time < current_time

    @staticmethod
    def _validate_availability_range(from_date, to_date):
        if to_date < from_date:
            raise BusinessRuleError(
                "`to` deve ser igual ou posterior a `from`.", field="to"
            )
        if (to_date - from_date).days + 1 > _MAX_AVAILABILITY_DAYS:
            raise BusinessRuleError(
                "O intervalo de disponibilidade não pode exceder 93 dias.", field="to"
            )

    @staticmethod
    def _normalize_status(status):
        if not status:
            return None
        normalized = status.upper()
        valid = {choice.value for choice in Reservation.Status}
        if normalized not in valid:
            raise BusinessRuleError(
                f"Filtro de status inválido: {status!r}.",
                field="status",
            )
        return normalized

    @staticmethod
    def _normalize_location_id(location_id):
        if location_id is None or str(location_id).strip() == "":
            return None
        try:
            return int(location_id)
        except (TypeError, ValueError) as exc:
            raise BusinessRuleError(
                "location_id deve ser um número inteiro.",
                field="location_id",
            ) from exc

    def _record_decision(self, reservation, *, actor, action, reason):
        location = getattr(reservation, "location", None)
        unit = getattr(reservation, "unit", None)
        target = getattr(reservation, "reservation_user", None)
        unit_display = ""
        if unit is not None:
            display = getattr(unit, "display_name", None)
            unit_display = display() if callable(display) else (display or "")
        self._decisions.record(
            {
                "reservation": reservation,
                "condominium_id": reservation.condominium_id,
                "location": location,
                "location_name": getattr(location, "name", "") or "",
                "location_icon": getattr(location, "icon", "") or "",
                "reservation_date": reservation.reservation_date,
                "start_time": reservation.start_time,
                "end_time": reservation.end_time,
                "unit": unit,
                "unit_display_name": unit_display,
                "target": target,
                "target_username": getattr(target, "username", "") or "",
                "target_full_name": getattr(target, "full_name", "") or "",
                "target_email": getattr(target, "email", "") or "",
                "actor": actor,
                "actor_username": getattr(actor, "username", "") or "",
                "actor_full_name": getattr(actor, "full_name", "") or "",
                "actor_email": getattr(actor, "email", "") or "",
                "actor_role": "ADMIN",
                "action": action,
                "reason": reason or "",
            }
        )

    @staticmethod
    def _normalize_period(period):
        if not period:
            return None
        normalized = period.lower()
        if normalized not in {"future", "past"}:
            raise BusinessRuleError(
                f"Filtro de período inválido: {period!r}. "
                "Esperado 'future' ou 'past'.",
                field="period",
            )
        return normalized

    @staticmethod
    def _ensure_staff(user, action):
        if not is_admin(user):
            raise PermissionDeniedError(
                f"Apenas a equipe do condomínio pode {action} reservas."
            )

    @staticmethod
    def _list_tenant_id(user, condominium_id):
        if is_platform_superuser(user):
            if condominium_id is None:
                raise BusinessRuleError(
                    "condominium_id é obrigatório para superusuários da plataforma.",
                    field="condominium_id",
                )
            return condominium_id
        tenant_id = require_condominium_id(user)
        if condominium_id is not None and condominium_id != tenant_id:
            raise NotFoundError("Condomínio não encontrado.")
        return tenant_id

    def _notify(self, instance, *, approved, reason=""):
        target = instance.reservation_user
        if not target or not getattr(target, "email", None):
            return
        common = {
            "to_email": target.email,
            "user_name": getattr(target, "full_name", None)
            or target.username,
            "resource_name": instance.location.name,
            "reservation_date": instance.reservation_date,
            "start_time": instance.start_time,
            "end_time": instance.end_time,
        }
        if approved:
            self._email.send_reservation_approved(**common)
        else:
            self._email.send_reservation_rejected(
                **common, reason=reason
            )
