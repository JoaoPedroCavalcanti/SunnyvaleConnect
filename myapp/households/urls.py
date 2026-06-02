from django.urls import path

from households.views import (
    DependentDetailView,
    DependentListCreateView,
    HouseholdApproveView,
    HouseholdDecisionListView,
    HouseholdDetailView,
    HouseholdLeaveView,
    HouseholdListView,
    HouseholdMembershipListView,
    HouseholdRejectView,
    HouseholdSearchView,
    HouseholdTransferView,
    MembershipApproveView,
    MembershipDemoteView,
    MembershipPromoteView,
    MembershipRejectView,
    MembershipRemoveView,
    PendingApprovalsView,
)

app_name = "households"

urlpatterns = [
    path("search/", HouseholdSearchView.as_view(), name="search"),
    path(
        "pending-approvals/",
        PendingApprovalsView.as_view(),
        name="pending-approvals",
    ),
    path("", HouseholdListView.as_view(), name="list"),
    path("<int:pk>/", HouseholdDetailView.as_view(), name="detail"),
    path("<int:pk>/approve/", HouseholdApproveView.as_view(), name="approve"),
    path("<int:pk>/reject/", HouseholdRejectView.as_view(), name="reject"),
    path("<int:pk>/leave/", HouseholdLeaveView.as_view(), name="leave"),
    path("<int:pk>/transfer/", HouseholdTransferView.as_view(), name="transfer"),
    path(
        "<int:pk>/memberships/",
        HouseholdMembershipListView.as_view(),
        name="memberships-list",
    ),
    path(
        "<int:pk>/memberships/<int:mid>/approve/",
        MembershipApproveView.as_view(),
        name="membership-approve",
    ),
    path(
        "<int:pk>/memberships/<int:mid>/reject/",
        MembershipRejectView.as_view(),
        name="membership-reject",
    ),
    path(
        "<int:pk>/memberships/<int:mid>/promote/",
        MembershipPromoteView.as_view(),
        name="membership-promote",
    ),
    path(
        "<int:pk>/memberships/<int:mid>/demote/",
        MembershipDemoteView.as_view(),
        name="membership-demote",
    ),
    path(
        "<int:pk>/memberships/<int:mid>/",
        MembershipRemoveView.as_view(),
        name="membership-remove",
    ),
    path(
        "<int:pk>/decisions/",
        HouseholdDecisionListView.as_view(),
        name="decisions-list",
    ),
    path(
        "<int:pk>/dependents/",
        DependentListCreateView.as_view(),
        name="dependents-list-create",
    ),
    path(
        "<int:pk>/dependents/<int:did>/",
        DependentDetailView.as_view(),
        name="dependent-detail",
    ),
]
