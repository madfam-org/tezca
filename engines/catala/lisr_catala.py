from decimal import Decimal

# Mocking the generated python code from Catala
# In a real scenario, this is auto-generated.

class Person:
    def __init__(self, residence: bool, income_source_mx: bool):
        self.residence = residence
        self.income_source_mx = income_source_mx

    def tax_obligation(self) -> bool:
        if self.residence:
            return True
        if not self.residence and self.income_source_mx:
            return True
        return False

class PhysicalPersonTax:
    def __init__(self, income_cash: Decimal, income_goods: Decimal):
        self.income_cash = income_cash
        self.income_goods = income_goods

    def total_income(self) -> Decimal:
        return self.income_cash + self.income_goods
