"""
Contribution API views.

Handles community data contribution submissions. Public endpoint for
form submissions, admin endpoints for review workflow.
"""

import logging

from rest_framework import serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Contribution

logger = logging.getLogger(__name__)


class ContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contribution
        fields = [
            "id",
            "submitter_name",
            "submitter_email",
            "submitter_institution",
            "data_type",
            "jurisdiction",
            "description",
            "file_url",
            "file_format",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]


class ContributionCreateSerializer(serializers.Serializer):
    submitter_name = serializers.CharField(max_length=200)
    submitter_email = serializers.EmailField()
    submitter_institution = serializers.CharField(
        max_length=300, required=False, default=""
    )
    data_type = serializers.ChoiceField(choices=Contribution.DataType.choices)
    jurisdiction = serializers.CharField(max_length=200, required=False, default="")
    description = serializers.CharField()
    file_url = serializers.URLField(max_length=500, required=False, default="")
    file_format = serializers.CharField(max_length=50, required=False, default="")


class ExpertContactSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    institution = serializers.CharField(max_length=300, required=False, default="")
    expertise_area = serializers.CharField(max_length=300)
    how_can_help = serializers.CharField()
    contact_preference = serializers.CharField(
        max_length=50, required=False, default="email"
    )


@api_view(["POST"])
def submit_contribution(request):
    """
    Submit a data contribution.

    Public endpoint — no authentication required.
    Creates a Contribution record with pending status.
    """
    serializer = ContributionCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    contribution = Contribution.objects.create(**serializer.validated_data)
    logger.info(
        "New contribution #%d from %s (%s)",
        contribution.id,
        contribution.submitter_name,
        contribution.data_type,
    )

    return Response(
        ContributionSerializer(contribution).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
def submit_expert_contact(request):
    """
    Submit an expert contact form.

    Public endpoint — creates a Contribution record tagged as expert contact.
    """
    serializer = ExpertContactSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    contribution = Contribution.objects.create(
        submitter_name=data["name"],
        submitter_email=data["email"],
        submitter_institution=data.get("institution", ""),
        data_type="other",
        jurisdiction="",
        description=(
            f"Expert contact: {data['expertise_area']}\n"
            f"How they can help: {data['how_can_help']}\n"
            f"Contact preference: {data.get('contact_preference', 'email')}"
        ),
    )
    logger.info(
        "New expert contact #%d from %s", contribution.id, contribution.submitter_name
    )

    return Response(
        {"id": contribution.id, "status": "pending", "message": "Thank you!"},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def list_contributions(request):
    """
    List contributions (admin endpoint, should be protected).
    """
    status_filter = request.query_params.get("status")
    qs = Contribution.objects.all()
    if status_filter:
        qs = qs.filter(status=status_filter)

    return Response(ContributionSerializer(qs[:100], many=True).data)
