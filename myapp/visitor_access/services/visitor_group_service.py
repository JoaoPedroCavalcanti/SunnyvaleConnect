"""Business rules for visitor groups (reusable lists of visitors)."""

from abc import ABC, abstractmethod

from shared.exceptions import BusinessRuleError, NotFoundError
from shared.roles import ensure_not_employee, is_admin
from visitor_access.models import VisitorGroupModel
from visitor_access.repositories.visitor_group_repository import (
    IVisitorGroupRepository,
)
from visitor_access.services.visitor_access_service import IVisitorAccessService


class IVisitorGroupService(ABC):
    @abstractmethod
    def list_for(self, user): ...

    @abstractmethod
    def get_for(self, user, pk: int) -> VisitorGroupModel: ...

    @abstractmethod
    def create(self, user, payload: dict) -> VisitorGroupModel: ...

    @abstractmethod
    def update(self, user, pk: int, payload: dict) -> VisitorGroupModel: ...

    @abstractmethod
    def delete(self, user, pk: int) -> None: ...

    @abstractmethod
    def schedule_visit(self, user, pk: int, payload: dict): ...


class VisitorGroupService(IVisitorGroupService):
    def __init__(
        self,
        repository: IVisitorGroupRepository,
        visitor_access_service: IVisitorAccessService,
    ):
        self._repo = repository
        self._access = visitor_access_service

    # ------------------------------------------------------------------ #
    # listing                                                            #
    # ------------------------------------------------------------------ #
    def list_for(self, user):
        if user.is_staff:
            return self._repo.list_all()
        return self._repo.list_for_user(user.id)

    def get_for(self, user, pk):
        instance = self._repo.get_by_id(pk)
        if not instance:
            raise NotFoundError("No visitor group matches the given query.")
        if not user.is_staff and instance.host_user_id != user.id:
            raise NotFoundError("No visitor group matches the given query.")
        return instance

    # ------------------------------------------------------------------ #
    # create / update / delete                                           #
    # ------------------------------------------------------------------ #
    def create(self, user, payload: dict):
        ensure_not_employee(user, action="manage visitor groups")
        data = dict(payload)
        members = data.pop("members", []) or []
        name = (data.get("name") or "").strip()

        if not name:
            raise BusinessRuleError("Name is required.", field="name")

        self._validate_members(members)

        if self._repo.exists_with_name_for_user(user.id, name):
            raise BusinessRuleError(
                "You already have a group with this name.", field="name"
            )

        group = self._repo.create({"name": name, "host_user": user})
        self._repo.add_members(group, members)
        return self._repo.get_by_id(group.id)

    def update(self, user, pk: int, payload: dict):
        ensure_not_employee(user, action="manage visitor groups")
        instance = self.get_for(user, pk)
        data = dict(payload)

        new_name = data.get("name")
        if new_name is not None:
            new_name = new_name.strip()
            if not new_name:
                raise BusinessRuleError("Name cannot be blank.", field="name")
            if self._repo.exists_with_name_for_user(
                instance.host_user_id, new_name, exclude_pk=instance.id
            ):
                raise BusinessRuleError(
                    "You already have a group with this name.", field="name"
                )
            self._repo.update(instance, {"name": new_name})

        if "members" in data:
            members = data["members"] or []
            self._validate_members(members)
            self._repo.replace_members(instance, members)

        return self._repo.get_by_id(instance.id)

    def delete(self, user, pk: int) -> None:
        ensure_not_employee(user, action="manage visitor groups")
        instance = self.get_for(user, pk)
        self._repo.delete(instance)

    # ------------------------------------------------------------------ #
    # schedule a visit for the whole group                               #
    # ------------------------------------------------------------------ #
    def schedule_visit(self, user, pk: int, payload: dict):
        ensure_not_employee(user, action="schedule visits")
        """Create a single visit row representing the whole group.

        The visit reuses VisitorAccessModel (so it inherits status,
        check-in/out, links). The downstream access service expands the
        members list when sending invites and notifications.
        """
        group = self.get_for(user, pk)
        if group.members.count() == 0:
            raise BusinessRuleError(
                "This group has no members. Add members before scheduling a visit."
            )

        scheduled_date = payload.get("scheduled_date")
        if scheduled_date is None:
            raise BusinessRuleError(
                "scheduled_date is required.", field="scheduled_date"
            )

        # admin schedules in name of the group's owner
        host_user = group.host_user
        acting_user = host_user if is_admin(user) else user

        visit_payload = {
            "scheduled_date": scheduled_date,
            "all_day": payload.get("all_day", False),
            "description": payload.get("description", "") or "",
            "visitor_name": group.name,
            "email": "",
            "visitor_group": group,
        }
        if not visit_payload["all_day"] and payload.get("checkout_date_time"):
            visit_payload["checkout_date_time"] = payload["checkout_date_time"]

        return self._access.create(acting_user, visit_payload)

    # ------------------------------------------------------------------ #
    # helpers                                                            #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validate_members(members: list[dict]) -> None:
        for idx, m in enumerate(members):
            name = (m.get("name") or "").strip()
            if not name:
                raise BusinessRuleError(
                    f"Member at index {idx} requires a name.", field="members"
                )
