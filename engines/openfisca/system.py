from engines.openfisca.mock import TaxBenefitSystem
from engines.openfisca.variables import (
    gross_income,
    has_mexican_income_source,
    income_cash,
    income_goods,
    is_resident,
    isr_breakdown_fixed_fee,
    isr_breakdown_lower_limit,
    isr_breakdown_rate,
    isr_obligation,
)


class MexicanTaxSystem(TaxBenefitSystem):
    def __init__(self):
        super().__init__(
            [
                isr_obligation,
                gross_income,
                is_resident,
                has_mexican_income_source,
                income_cash,
                income_goods,
                isr_breakdown_lower_limit,
                isr_breakdown_rate,
                isr_breakdown_fixed_fee,
            ]
        )


if __name__ == "__main__":
    system = MexicanTaxSystem()
    print("Mexican Tax System loaded successfully.")
