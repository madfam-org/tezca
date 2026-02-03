from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from engines.openfisca.system import MexicanTaxSystem
from .serializers import CalculationRequestSerializer

class CalculationView(APIView):
    def post(self, request):
        serializer = CalculationRequestSerializer(data=request.data)
        if serializer.is_valid():
            inputs = serializer.validated_data
            
            # Initialize System
            system = MexicanTaxSystem()
            sim = system.new_simulation()
            
            # 1. Add Person
            sim.add_person(name="taxpayer", period=inputs['period'], 
                           is_resident=inputs['is_resident'],
                           has_mexican_income_source=True, # Assumed for MVP
                           income_cash=inputs['income_cash'],
                           income_goods=inputs['income_goods']
                          )
            
            # 2. Add Tax Unit (Individual) if necessary, but here we just query variables
            
            # 3. Calculate
            # We fetch all relevant variables
            try:
                gross_income = sim.calculate("gross_income", inputs['period'])[0]
                isr_due = sim.calculate("isr_obligation", inputs['period'])[0]
                lower_limit = sim.calculate("isr_breakdown_lower_limit", inputs['period'])[0]
                fixed_fee = sim.calculate("isr_breakdown_fixed_fee", inputs['period'])[0]
                rate = sim.calculate("isr_breakdown_rate", inputs['period'])[0]
                
                return Response({
                    "period": inputs['period'],
                    "gross_income": gross_income,
                    "isr_obligation": isr_due,  # This is the "Total Tax"
                    "breakdown": {
                        "lower_limit": lower_limit,
                        "fixed_fee": fixed_fee,
                        "rate": rate,
                        "taxable_income": gross_income # Simplified
                    }
                })
            except Exception as e:
                # In production log this
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from .ingestion_manager import IngestionManager

class IngestionView(APIView):
    def post(self, request):
        params = request.data
        success, message = IngestionManager.start_ingestion(params)
        if success:
             return Response({"status": "started", "message": message}, status=status.HTTP_202_ACCEPTED)
        return Response({"status": "error", "message": message}, status=status.HTTP_409_CONFLICT)
        
    def get(self, request):
        status_data = IngestionManager.get_status()
        return Response(status_data)
