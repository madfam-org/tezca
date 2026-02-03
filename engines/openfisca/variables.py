from engines.openfisca_mock import Person, TaxBenefitSystem, Variable
# from openfisca_core.variables import Variable
from engines.catala.lisr_catala import Person as CatalaPerson, PhysicalPersonTax, get_person_tax
from decimal import Decimal

# Helper to process single person logic for vectorised OpenFisca
def calculate_single(residence, source_mx, income_c, income_g, output_field=None):
    p_catala = CatalaPerson(residence=residence, income_source_mx=source_mx)
    result = get_person_tax(p_catala, Decimal(str(income_c)), Decimal(str(income_g)))
    
    if output_field == "total":
        return float(result.isr_monthly)
    elif output_field in result.breakdown:
        return float(result.breakdown[output_field])
    return 0.0

class isr_obligation(Variable):
    value_type = float
    entity = Person
    label = "Impuesto Sobre la Renta a Cargo (Mensual)"
    definition_period = "MONTH"

    def formula(person, period, parameters):
        residence = person("is_resident", period)
        source_mx = person("has_mexican_income_source", period)
        cash = person("income_cash", period)
        goods = person("income_goods", period)

        return [
            calculate_single(r, s, c, g, "total_tax")
            for r, s, c, g in zip(residence, source_mx, cash, goods)
        ]

class gross_income(Variable):
    value_type = float
    entity = Person
    label = "Ingresos Totales (Efectivo + Bienes)"
    definition_period = "MONTH"

    def formula(person, period, parameters):
        cash = person("income_cash", period)
        goods = person("income_goods", period)
        return cash + goods

# Breakdown Variables

class isr_breakdown_lower_limit(Variable):
    value_type = float
    entity = Person
    label = "Límite Inferior"
    definition_period = "MONTH"
    def formula(person, period, parameters):
        return [
            calculate_single(r, s, c, g, "lower_limit")
            for r, s, c, g in zip(person("is_resident", period), person("has_mexican_income_source", period), person("income_cash", period), person("income_goods", period))
        ]

class isr_breakdown_fixed_fee(Variable):
    value_type = float
    entity = Person
    label = "Cuota Fija"
    definition_period = "MONTH"
    def formula(person, period, parameters):
        return [
            calculate_single(r, s, c, g, "fixed_fee")
            for r, s, c, g in zip(person("is_resident", period), person("has_mexican_income_source", period), person("income_cash", period), person("income_goods", period))
        ]

class isr_breakdown_rate(Variable):
    value_type = float
    entity = Person
    label = "Tasa Aplicable (%)"
    definition_period = "MONTH"
    def formula(person, period, parameters):
        return [
            calculate_single(r, s, c, g, "rate")
            for r, s, c, g in zip(person("is_resident", period), person("has_mexican_income_source", period), person("income_cash", period), person("income_goods", period))
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
