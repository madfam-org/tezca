from engines.openfisca.system import MexicanTaxSystem

def test_tax_obligation():
    system = MexicanTaxSystem()
    sim = system.new_simulation()
    
    sim.add_person(name="Juan", period="2024-01", 
                   is_resident=True, 
                   has_mexican_income_source=False)
    
    obligation = sim.calculate("isr_obligation", "2024-01")
    assert obligation["Juan"] == True

def test_gross_income_calc():
    system = MexicanTaxSystem()
    sim = system.new_simulation()
    
    sim.add_person(name="Maria", period="2024-01", 
                   income_cash=10000, 
                   income_goods=5000)
    
    total = sim.calculate("gross_income", "2024-01")
    assert total["Maria"] == 15000.0
