from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .ingestion_manager import IngestionManager
from .schema import ErrorSchema, IngestionRequestSchema, IngestionResponseSchema


class IngestionView(APIView):
    @extend_schema(
        tags=["Ingestion"],
        summary="Start ingestion",
        description="Start a background ingestion job. Returns 409 if already running.",
        request=IngestionRequestSchema,
        responses={202: IngestionResponseSchema, 409: IngestionResponseSchema},
    )
    def post(self, request):
        params = request.data
        success, message = IngestionManager.start_ingestion(params)
        if success:
            return Response(
                {"status": "started", "message": message},
                status=status.HTTP_202_ACCEPTED,
            )
        return Response(
            {"status": "error", "message": message}, status=status.HTTP_409_CONFLICT
        )

    @extend_schema(
        tags=["Ingestion"],
        summary="Get ingestion status",
        description="Get the current status of the ingestion process.",
        responses={200: IngestionResponseSchema},
    )
    def get(self, request):
        status_data = IngestionManager.get_status()
        return Response(status_data)
