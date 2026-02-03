from decimal import Decimal

class Person:
    def __init__(self, residence: bool, income_source_mx: bool):
        self.residence = residence
        self.income_source_mx = income_source_mx

class PhysicalPersonTax:
    def __init__(self, isr_monthly: Decimal, gross_income_monthly: Decimal, breakdown: dict = None):
        self.isr_monthly = isr_monthly
        self.gross_income_monthly = gross_income_monthly
        self.breakdown = breakdown or {}

# LISR 2024 Monthly Table (Annex 8 RMF)
# Format: (LowerLimit, FixedFee, RatePercent)
ISR_TABLE_2024_MONTHLY = [
    (Decimal("0.01"), Decimal("0.00"), Decimal("1.92")),
    (Decimal("746.05"), Decimal("14.32"), Decimal("6.40")),
    (Decimal("6332.06"), Decimal("371.83"), Decimal("10.88")),
    (Decimal("11128.02"), Decimal("893.63"), Decimal("16.00")),
    (Decimal("12935.83"), Decimal("1182.88"), Decimal("17.92")),
    (Decimal("15487.72"), Decimal("1640.18"), Decimal("21.36")),
    (Decimal("31236.50"), Decimal("5004.12"), Decimal("23.52")),
    (Decimal("49233.01"), Decimal("9236.89"), Decimal("30.00")),
    (Decimal("93993.91"), Decimal("22665.17"), Decimal("32.00")),
    (Decimal("125325.21"), Decimal("32691.18"), Decimal("34.00")),
    (Decimal("375975.62"), Decimal("117912.32"), Decimal("35.00")),
]

def calculate_isr_monthly(taxable_income: Decimal) -> dict:
    """
    Calculates the ISR based on the 2024 Monthly Table.
    """
    if taxable_income <= 0:
        return {
            "lower_limit": Decimal("0.00"),
            "excess": Decimal("0.00"),
            "rate": Decimal("0.00"),
            "marginal_tax": Decimal("0.00"),
            "fixed_fee": Decimal("0.00"),
            "total_tax": Decimal("0.00")
        }

    # Find the row
    row = ISR_TABLE_2024_MONTHLY[0]
    for r in ISR_TABLE_2024_MONTHLY:
        if taxable_income >= r[0]:
            row = r
        else:
            break
            
    lower_limit, fixed_fee, rate = row
    
    excess = taxable_income - lower_limit
    marginal_tax = excess * (rate / Decimal("100.0"))
    total_tax = marginal_tax + fixed_fee
    
    return {
        "lower_limit": lower_limit,
        "excess": excess,
        "rate": rate,
        "marginal_tax": marginal_tax,
        "fixed_fee": fixed_fee,
        "total_tax": total_tax
    }

def get_person_tax(person: Person, income_cash: Decimal, income_goods: Decimal) -> PhysicalPersonTax:
    # 1. Gross Income
    gross_income = income_cash + income_goods
    
    # 2. Taxable Income (Simplified: No deductions yet)
    taxable_income = gross_income
    
    # 3. Calculate Tax
    if person.residence and person.income_source_mx:
        result = calculate_isr_monthly(taxable_income)
        return PhysicalPersonTax(
            isr_monthly=result["total_tax"],
            gross_income_monthly=gross_income,
            breakdown=result
        )
    else:
        # Non-residents logic (simplified to 0 for MVP)
        return PhysicalPersonTax(Decimal("0"), gross_income, {})
