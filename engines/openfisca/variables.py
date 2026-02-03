from engines.openfisca_mock import Person, TaxBenefitSystem, Variable
from engines.catala.lisr_catala import Person as CatalaPerson, PhysicalPersonTax
from decimal import Decimal

class isr_obligation(Variable):
    value_type = bool
    entity = Person
    label = "Obligación de pago de ISR"
    definition_period = "MONTH"

    def formula(person, period, parameters):
        residence = person("is_resident", period)
        source_mx = person("has_mexican_income_source", period)
        
        # Using the Mock Catala Logic
        # We vectorise explicitly here for simplicity, though real Catala is cleaner
        return [
            CatalaPerson(r, s).tax_obligation() 
            for r, s in zip(residence, source_mx)
        ]

class gross_income(Variable):
    value_type = float
    entity = Person
    label = "Ingresos Totales (Efectivo + Bienes)"
    definition_period = "MONTH"

    def formula(person, period, parameters):
        cash = person("income_cash", period)
        goods = person("income_goods", period)

        return [
            float(PhysicalPersonTax(Decimal(c), Decimal(g)).total_income())
            for c, g in zip(cash, goods)
        ]

# Input Variables
class is_resident(Variable):
    value_type = bool
    entity = Person
    label = "Es residente en México"
    definition_period = "MONTH"

class has_mexican_income_source(Variable):
    value_type = bool
    entity = Person
    label = "Tiene fuente de riqueza en México"
    definition_period = "MONTH"

class income_cash(Variable):
    value_type = float
    entity = Person
    label = "Ingresos en efectivo"
    definition_period = "MONTH"

class income_goods(Variable):
    value_type = float
    entity = Person
    label = "Ingresos en bienes"
    definition_period = "MONTH"
