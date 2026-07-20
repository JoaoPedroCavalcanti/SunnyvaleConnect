"""Business rules for UnitMembership lifecycle."""

from abc import ABC, abstractmethod

from units.models import Unit, UnitMembership, UnitMembershipDecision
from units.repositories.unit_membership_decision_repository import (
    IUnitMembershipDecisionRepository,
)
from units.repositories.unit_membership_repository import IUnitMembershipRepository
from units.repositories.unit_repository import IUnitRepository
from shared.exceptions import (
    BusinessRuleError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.infrastructure.email_sender import IEmailSender
from shared.infrastructure.transactions import ITransactionRunner
from shared.tenant import assert_same_condominium, require_condominium_id
from users.repositories.user_repository import IUserRepository


class IUnitMembershipService(ABC):
    @abstractmethod
    def list_for_unit(self, user, unit_id: int): ...

    @abstractmethod
    def list_pending_approvals(self, user): ...

    @abstractmethod
    def request_join(self, user, unit_id: int) -> UnitMembership: ...

    @abstractmethod
    def provision_join(
        self, admin, user, unit_id: int
    ) -> UnitMembership: ...

    @abstractmethod
    def approve(self, actor, membership_id: int) -> UnitMembership: ...

    @abstractmethod
    def reject(
        self, actor, membership_id: int, reason: str = ""
    ) -> None: ...

    @abstractmethod
    def remove(self, owner, membership_id: int) -> None: ...

    @abstractmethod
    def leave(self, user, unit_id: int) -> None: ...

    @abstractmethod
    def transfer_ownership(
        self, owner, unit_id: int, membership_id: int
    ) -> dict: ...


class UnitMembershipService(IUnitMembershipService):
    def __init__(
        self,
        membership_repository: IUnitMembershipRepository,
        unit_repository: IUnitRepository,
        user_repository: IUserRepository,
        email_sender: IEmailSender,
        decision_repository: IUnitMembershipDecisionRepository,
        transaction_runner: ITransactionRunner,
    ):
        self._repo = membership_repository
        self._units = unit_repository
        self._users = user_repository
        self._email = email_sender
        self._decisions = decision_repository
        self._tx = transaction_runner

    def list_for_unit(self, user, unit_id):
        unit = self._get_unit_or_404(unit_id)
        if not getattr(user, "is_staff", False):
            self._require_active_membership(user.id, unit.id)
        return list(self._repo.list_for_unit(unit.id))

    def list_pending_approvals(self, user):
        if getattr(user, "is_staff", False):
            condominium_id = require_condominium_id(user)
            return list(
                self._repo.list_pending_admin(condominium_id=condominium_id)
            )
        return list(self._repo.list_pending_owner_for_units_of(user.id))

    def request_join(self, user, unit_id):
        unit = self._get_unit_or_404(unit_id)
        if unit.status != Unit.Status.ACTIVE:
            raise BusinessRuleError("This unit is not open for new members.")

        existing = self._repo.get_for_user_and_unit(user.id, unit.id)
        if existing and existing.status != UnitMembership.Status.LEFT:
            raise BusinessRuleError(
                "You already have a pending or active membership for this unit."
            )

        if self._repo.list_active_for_user(user.id):
            raise BusinessRuleError(
                "User is already an active member of another unit."
            )
        if self._repo.list_pending_for_user(user.id):
            raise BusinessRuleError("User already has a pending unit request.")

        vacant = self._repo.get_active_owner(unit.id) is None
        if vacant:
            role = UnitMembership.Role.OWNER
            status = UnitMembership.Status.PENDING_ADMIN
        else:
            role = UnitMembership.Role.RESIDENT
            status = UnitMembership.Status.PENDING_OWNER

        with self._tx.atomic():
            membership = self._repo.create(
                {
                    "unit": unit,
                    "user": user,
                    "role": role,
                    "status": status,
                }
            )

        self._notify_approvers(membership)
        return membership

    def provision_join(self, admin, user, unit_id):
        if not getattr(admin, "is_staff", False):
            raise PermissionDeniedError(
                "Only staff can provision unit memberships."
            )

        unit = self._get_unit_or_404(unit_id)
        assert_same_condominium(admin, unit.condominium_id)
        if unit.status != Unit.Status.ACTIVE:
            raise BusinessRuleError(
                "This unit is not open for new members.",
                field="unit_id",
            )

        existing = self._repo.get_for_user_and_unit(user.id, unit.id)
        if existing and existing.status != UnitMembership.Status.LEFT:
            raise BusinessRuleError(
                "This user already has a pending or active membership for this unit.",
                field="unit_id",
            )

        if self._repo.list_active_for_user(user.id):
            raise BusinessRuleError(
                "User is already an active member of another unit.",
                field="unit_id",
            )
        if self._repo.list_pending_for_user(user.id):
            raise BusinessRuleError(
                "User already has a pending unit request.",
                field="unit_id",
            )

        vacant = self._repo.get_active_owner(unit.id) is None
        role = (
            UnitMembership.Role.OWNER
            if vacant
            else UnitMembership.Role.RESIDENT
        )

        with self._tx.atomic():
            return self._repo.create(
                {
                    "unit": unit,
                    "user": user,
                    "role": role,
                    "status": UnitMembership.Status.ACTIVE,
                }
            )

    def approve(self, actor, membership_id):
        membership = self._get_membership_or_404(membership_id)
        unit = membership.unit

        if membership.status == UnitMembership.Status.PENDING_ADMIN:
            if not getattr(actor, "is_staff", False):
                raise PermissionDeniedError(
                    "Only staff can approve owner requests."
                )
            assert_same_condominium(actor, unit.condominium_id)
        elif membership.status == UnitMembership.Status.PENDING_OWNER:
            self._require_owner(actor, unit.id)
        else:
            raise BusinessRuleError(
                "This membership is not pending approval."
            )

        with self._tx.atomic():
            self._repo.update(
                membership, {"status": UnitMembership.Status.ACTIVE}
            )
            self._users.set_active(membership.user, True)
            self._decisions.record(
                self._build_decision_payload(
                    membership,
                    actor=actor,
                    action=UnitMembershipDecision.Action.APPROVED,
                    reason="",
                )
            )

        if membership.user.email:
            self._email.send_household_request_approved(
                to_email=membership.user.email,
                requester_name=(
                    membership.user.full_name or membership.user.username
                ),
                apartment=unit.display_name(),
                block="",
            )

        return membership

    def reject(self, actor, membership_id, reason=""):
        membership = self._get_membership_or_404(membership_id)
        unit = membership.unit

        if membership.status == UnitMembership.Status.PENDING_ADMIN:
            if not getattr(actor, "is_staff", False):
                raise PermissionDeniedError(
                    "Only staff can reject owner requests."
                )
            assert_same_condominium(actor, unit.condominium_id)
        elif membership.status == UnitMembership.Status.PENDING_OWNER:
            self._require_owner(actor, unit.id)
        else:
            raise BusinessRuleError(
                "This membership is not pending approval."
            )

        user = membership.user
        recipient_email = user.email
        recipient_name = user.full_name or user.username
        unit_label = unit.display_name()

        with self._tx.atomic():
            self._decisions.record(
                self._build_decision_payload(
                    membership,
                    actor=actor,
                    action=UnitMembershipDecision.Action.REJECTED,
                    reason=reason,
                )
            )
            self._repo.delete(membership)
            if (
                not user.is_active
                and not self._repo.list_active_for_user(user.id)
                and not self._repo.list_pending_for_user(user.id)
            ):
                self._users.delete(user)

        if recipient_email:
            self._email.send_household_request_rejected(
                to_email=recipient_email,
                requester_name=recipient_name,
                apartment=unit_label,
                block="",
                reason=reason,
            )

    def remove(self, owner, membership_id):
        membership = self._get_membership_or_404(membership_id)
        self._require_owner(owner, membership.unit_id)
        self._require_active(membership)

        if membership.user_id == owner.id:
            raise BusinessRuleError(
                "Use /leave to remove yourself; /remove is for other members."
            )
        if membership.role == UnitMembership.Role.OWNER:
            raise BusinessRuleError("Cannot remove an owner directly.")

        self._repo.soft_leave(membership)

    def leave(self, user, unit_id):
        unit = self._get_unit_or_404(unit_id)
        membership = self._repo.get_for_user_and_unit(user.id, unit.id)
        if not membership or membership.status != UnitMembership.Status.ACTIVE:
            raise NotFoundError("You are not a member of this unit.")

        if membership.role != UnitMembership.Role.OWNER:
            raise PermissionDeniedError(
                "Residents cannot leave a unit without owner action."
            )

        other_members = [
            m
            for m in self._repo.list_active_for_unit(unit.id)
            if m.id != membership.id
        ]
        if other_members:
            raise BusinessRuleError(
                "You are the owner but there are other members. "
                "Remove them first or contact an administrator."
            )

        self._repo.soft_leave(membership)

        remaining = list(self._repo.list_active_for_unit(unit.id))
        if not remaining:
            self._units.update(unit, {"status": Unit.Status.ARCHIVED})

    def transfer_ownership(self, owner, unit_id, membership_id):
        unit = self._get_unit_or_404(unit_id)
        owner_membership = self._repo.get_for_user_and_unit(owner.id, unit.id)
        if (
            not owner_membership
            or owner_membership.status != UnitMembership.Status.ACTIVE
            or owner_membership.role != UnitMembership.Role.OWNER
        ):
            raise PermissionDeniedError(
                "Only the active owner can transfer ownership."
            )

        new_owner = self._get_membership_or_404(membership_id)
        if new_owner.unit_id != unit.id:
            raise NotFoundError("No membership matches the given query.")
        if new_owner.user_id == owner.id:
            raise BusinessRuleError(
                "Ownership must be transferred to another member."
            )
        self._require_active(new_owner)
        if new_owner.role != UnitMembership.Role.RESIDENT:
            raise BusinessRuleError(
                "Ownership can only be transferred to an active resident."
            )
        if not getattr(new_owner.user, "is_active", False):
            raise BusinessRuleError(
                "Ownership cannot be transferred to an inactive user."
            )

        with self._tx.atomic():
            self._repo.update(
                owner_membership, {"role": UnitMembership.Role.RESIDENT}
            )
            self._repo.update(
                new_owner, {"role": UnitMembership.Role.OWNER}
            )

        return {
            "previous_owner": owner_membership,
            "new_owner": new_owner,
        }

    def _get_unit_or_404(self, unit_id) -> Unit:
        unit = self._units.get_by_id(unit_id)
        if not unit:
            raise NotFoundError("No unit matches the given query.")
        return unit

    def _get_membership_or_404(self, pk) -> UnitMembership:
        membership = self._repo.get_by_id(pk)
        if not membership:
            raise NotFoundError("No membership matches the given query.")
        return membership

    def _require_owner(self, user, unit_id) -> None:
        if getattr(user, "is_staff", False):
            return
        owner = self._repo.get_for_user_and_unit(user.id, unit_id)
        if (
            not owner
            or owner.status != UnitMembership.Status.ACTIVE
            or owner.role != UnitMembership.Role.OWNER
        ):
            raise PermissionDeniedError(
                "Only an active owner can perform this action."
            )

    def _require_active_membership(self, user_id, unit_id) -> None:
        membership = self._repo.get_for_user_and_unit(user_id, unit_id)
        if (
            not membership
            or membership.status != UnitMembership.Status.ACTIVE
        ):
            raise PermissionDeniedError(
                "You must be an active member of this unit."
            )

    def _require_active(self, membership) -> None:
        if membership.status != UnitMembership.Status.ACTIVE:
            raise BusinessRuleError("Membership is not active.")

    def _build_decision_payload(
        self, membership, actor, action, reason
    ) -> dict:
        user = membership.user
        unit = membership.unit
        return {
            "unit": unit,
            "unit_kind": unit.kind,
            "unit_name": unit.name,
            "unit_apartment": unit.apartment,
            "unit_block": unit.block,
            "unit_display_name": unit.display_name(),
            "actor": actor,
            "actor_username": getattr(actor, "username", "") or "",
            "actor_full_name": getattr(actor, "full_name", "") or "",
            "actor_email": getattr(actor, "email", "") or "",
            "actor_role": (
                "ADMIN" if getattr(actor, "is_staff", False) else "OWNER"
            ),
            "target": user,
            "target_username": getattr(user, "username", "") or "",
            "target_full_name": getattr(user, "full_name", "") or "",
            "target_email": getattr(user, "email", "") or "",
            "action": action,
            "reason": reason or "",
        }

    def _notify_approvers(self, membership) -> None:
        user = membership.user
        unit = membership.unit
        requester_name = user.full_name or user.username
        unit_label = unit.display_name()

        if membership.status == UnitMembership.Status.PENDING_ADMIN:
            for to_email in self._users.list_admin_emails(
                condominium_id=unit.condominium_id
            ):
                self._email.send_household_creation_request(
                    to_email=to_email,
                    requester_name=requester_name,
                    apartment=unit_label,
                    block="",
                )
            return

        if membership.status == UnitMembership.Status.PENDING_OWNER:
            for owner_m in self._repo.list_active_owners(unit.id):
                if not owner_m.user.email:
                    continue
                self._email.send_household_join_request(
                    to_email=owner_m.user.email,
                    holder_name=(
                        owner_m.user.full_name or owner_m.user.username
                    ),
                    requester_name=requester_name,
                    apartment=unit_label,
                    block="",
                )
