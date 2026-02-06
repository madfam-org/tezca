# engines/openfisca/mock.py


class Person:
    """Mock Entity"""

    pass


class Variable:
    value_type = float
    entity = None
    label = ""
    definition_period = "MONTH"


class TaxBenefitSystem:
    def __init__(self, variables):
        self.variables = {v.__name__: v for v in variables}

    def new_simulation(self):
        return Simulation(self)


class Simulation:
    def __init__(self, system):
        self.system = system
        self.persons = {}
        self.inputs = {}

    def add_person(self, name, period, **kwargs):
        self.persons[name] = kwargs

    def calculate(self, variable_name, period):
        # specific mock implementation for our tests
        variable = self.system.variables[variable_name]

        # Prepare inputs for formula
        # In a real engine, this fetches from state. Here we mock it.
        # We assume 1 person calculation for simplicity of the test

        class MockPerson:
            def __init__(self, data):
                self.data = data

            def __call__(self, var_name, period):
                # If var_name is in input data, return it (vectorized as list)
                if var_name in self.data:
                    return [self.data[var_name]]
                return [0]  # default

        results = {}
        for name, data in self.persons.items():
            person_obj = MockPerson(data)
            # Call formula with the mock person
            result = variable.formula(person_obj, period, None)
            results[name] = result[0]

        return list(results.values())
