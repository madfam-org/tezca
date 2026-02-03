.PHONY: check-syntax test-logic install

install:
	poetry install

check-syntax:
	@echo "Checking XML syntax and Catala types..."
	# Placeholder: command to check AKN and Catala files
	poetry run black --check .

test-logic:
	@echo "Running verification tests..."
	poetry run pytest tests/
