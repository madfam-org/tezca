# Contributing to Leyes Como Código México

Thank you for your interest in contributing to the "State API"!

## Isomorphism Principle
This project adheres to the principle of **Isomorphism**: The code must be a faithful, verifyable representation of the law.

- **Lawyers**: Focus on `data/federal` (XML structure) and defining test cases.
- **Developers**: Focus on `engines/` (Logic) and `apps/` (Platform).

## Workflow

1. **Pick a Law**: Check the Roadmap in README.md.
2. **Scrape**: Use tools in `apps/scraper` to fetch the DOF/OJN source.
3. **Structure**: Convert to Akoma Ntoso XML in `data/federal`.
4. **Encode**: Implement logic in `engines/catala`.
5. **Verify**: Run `make test-logic`.

## Standards

- **Commits**: Follow Conventional Commits.
  - `feat(isr): encode article 93`
  - `fix(xml): typo in art 23 structure`
- **Formatting**:
  - Python: Black
  - XML/Markdown: Prettier (if configured)

## Pull Request Process

1. Ensure `make check-syntax` passes.
2. Ensure `make test-logic` passes.
3. Link to the official DOF/OJN source in your PR description.
