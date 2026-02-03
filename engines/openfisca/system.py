from engines.openfisca_mock import TaxBenefitSystem
from engines.openfisca.variables import (
    isr_obligation, gross_income, is_resident, has_mexican_income_source,
    income_cash, income_goods
)

class MexicanTaxSystem(TaxBenefitSystem):
    def __init__(self):
        super().__init__([
            isr_obligation,
            gross_income,
            is_resident,
            has_mexican_income_source,
            income_cash,
            income_goods
        ])

if __name__ == "__main__":
    system = MexicanTaxSystem()
    print("Mexican Tax System loaded successfully.")
