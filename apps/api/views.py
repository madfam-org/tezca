from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Law

# from engines.openfisca.system import MexicanTaxSystem
from .schema import (
    CalculationDisabledSchema,
    ErrorSchema,
    IngestionRequestSchema,
    IngestionResponseSchema,
)
from .serializers import CalculationRequestSerializer


class CalculationView(APIView):
    @extend_schema(
        tags=["Calculation"],
        summary="Calculate tax obligation",
        description="Calculate ISR tax obligation based on income. Currently disabled pending OpenFisca engine integration.",
        deprecated=True,
        request=CalculationRequestSerializer,
        responses={200: CalculationDisabledSchema, 400: ErrorSchema},
    )
    def post(self, request):
        serializer = CalculationRequestSerializer(data=request.data)
        if serializer.is_valid():
            inputs = serializer.validated_data

            # Initialize System
            # system = MexicanTaxSystem()
            # sim = system.new_simulation()

            # ... (Calculation disabled for Stability)
            return Response(
                {
                    "message": "Calculation temporarily disabled due to missing engine dependencies",
                    "data": inputs,
                }
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


from .ingestion_manager import IngestionManager


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
