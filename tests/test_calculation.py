from engines.openfisca.system import MexicanTaxSystem
import pytest

def test_tax_calculation_2024():
    """
    Verifies Art. 96 Calculation for 2024.
    Example: Income $25,000 monthly.
    
    From Table:
    Lower Limit: 15,487.72
    Fixed Fee: 1,640.18
    Rate: 21.36%
    
    Base = 25,000 - 15,487.72 = 9,512.28
    Marginal = 9,512.28 * 0.2136 = 2,031.82
    Total = 2,031.82 + 1,640.18 = 3,672.00
    """
    system = MexicanTaxSystem()
    sim = system.new_simulation()
    
    period = "2024-01"
    sim.add_person(name="Juan", period=period, 
                   is_resident=True, 
                   has_mexican_income_source=True,
                   income_cash=25000,
                   income_goods=0
                   )

    isr = sim.calculate("isr_obligation", period)[0]
    limit = sim.calculate("isr_breakdown_lower_limit", period)[0]
    rate = sim.calculate("isr_breakdown_rate", period)[0]
    
    # Assertions with slight tolerance for float math
    assert abs(limit - 15487.72) < 0.01, f"Expected Lower Limit 15487.72, got {limit}"
    assert abs(rate - 21.36) < 0.01, f"Expected Rate 21.36, got {rate}"
    assert abs(isr - 3672.00) < 1.0, f"Expected Tax ~3672.00, got {isr}"
