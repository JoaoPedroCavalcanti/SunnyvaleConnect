from django.urls import path

from units.views import (
    MembershipDecisionHistoryView,
    PendingApprovalsView,
    UnitBulkProvisionView,
    UnitCatalogFiltersView,
    UnitDecisionListView,
    UnitDetailView,
    UnitLeaveView,
    UnitListCreateView,
    UnitMembershipApproveView,
    UnitMembershipListView,
    UnitMembershipRejectView,
    UnitMembershipRemoveView,
    UnitOwnershipTransferView,
)

app_name = "units"

urlpatterns = [
    path(
        "pending-approvals/",
        PendingApprovalsView.as_view(),
        name="pending-approvals",
    ),
    path(
        "decision-history/",
        MembershipDecisionHistoryView.as_view(),
        name="decision-history",
    ),
    path(
        "bulk-provision/",
        UnitBulkProvisionView.as_view(),
        name="bulk-provision",
    ),
    path(
        "filters/",
        UnitCatalogFiltersView.as_view(),
        name="filters",
    ),
    path("", UnitListCreateView.as_view(), name="list"),
    path("<int:pk>/", UnitDetailView.as_view(), name="detail"),
    path("<int:pk>/leave/", UnitLeaveView.as_view(), name="leave"),
    path(
        "<int:pk>/decisions/",
        UnitDecisionListView.as_view(),
        name="decisions-list",
    ),
    path(
        "<int:pk>/memberships/",
        UnitMembershipListView.as_view(),
        name="memberships-list",
    ),
    path(
        "<int:pk>/memberships/<int:mid>/approve/",
        UnitMembershipApproveView.as_view(),
        name="membership-approve",
    ),
    path(
        "<int:pk>/memberships/<int:mid>/reject/",
        UnitMembershipRejectView.as_view(),
        name="membership-reject",
    ),
    path(
        "<int:pk>/memberships/<int:mid>/",
        UnitMembershipRemoveView.as_view(),
        name="membership-remove",
    ),
    path(
        "<int:pk>/memberships/<int:mid>/transfer-ownership/",
        UnitOwnershipTransferView.as_view(),
        name="ownership-transfer",
    ),
]
