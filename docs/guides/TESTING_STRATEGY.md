# 🧪 TESTING_STRATEGY.md - Verification & Validation Protocols

> **SYSTEM NOTICE:** In this repository, "Green Builds" do not mean success. **Legal Accuracy** means success. A test that passes numerically but fails legally (e.g., applying a derogated rule) is a critical failure.

---

## 1. The "Oracle" Philosophy

We do not trust our own code. We trust the **Law** and the **Official Determinators**.

* **The Law:** The text in `data/federal/` is the absolute source of truth.
* **The Oracle:** Official government calculators (e.g., SAT simulators, IMSS SUA) are the "Oracle". If our code disagrees with the SAT's official simulator, our code is presumed wrong until proven otherwise.

---

## 2. Testing Layers

### Level 1: Structural Validation (XML)

Before logic, we validate the container.

* **Tool:** `xmllint` / `bluebell` validation.
* **Command:** `make validate-xml`
* **Check:**
* Does the Akoma Ntoso file conform to the OASIS schema?
* Are all `refersTo` tags resolving to valid Ontology IDs?
* **Crucial:** Does the `original_text` hash match the source PDF hash? (Integrity Check).



### Level 2: Unit Testing (The "Hypotheticals")

Every logical function must have corresponding unit tests representing "Judicial Hypotheticals."

#### 2.1 Catala (Fiscal Logic)

Catala has built-in testing. We use **Scope-based testing**.

* **Location:** `engines/catala/tests/`
* **Method:** Define a `scope` with inputs mimicking a real taxpayer.
* **Example:**
```catala
# Test Case: Resico 2024 - Low Income
scope TestResico:
  input income: 200000 MXN
  assertion tax_due = 2000 MXN # 1.0% rate

```


* **Requirement:** Every tax bracket in the *Anexos de la Resolución Miscelánea Fiscal* must have at least one test case hitting it (100% Branch Coverage).

#### 2.2 Blawx (Rule Logic)

We test logic using "Queries" against known scenarios.

* **Method:** Create a "Fact Scenario" (e.g., "Juan killed Pedro in self-defense").
* **Assertion:** The query `is_guilty(Juan)` must return `FALSE`.

### Level 3: Regression Testing (The "Time Travel" Check)

Law changes over time. New code must not break old years.

* **The Golden Rule:** When you implement the *Reform of 2024*, you must run the test suite for **2023** and **2022**. The results for those years must remain **identical**.
* **Implementation:** We maintain snapshots of calculated outputs for standard personas ("Persona A", "Persona B") for every fiscal year.

---

## 3. The "Legislative Trace" (Explanation Test)

A correct answer is useless without a correct citation.

* **Requirement:** The API response must include a `trace` object.
* **Test:**
* Input: Calculate ISR.
* Output: `$5,000`.
* Trace Check: Does the output list `LISR Art. 93` as a used variable? If the code used an exemption but didn't cite the article, the test **fails**.



---

## 4. Dataset & Benchmarks

We do not use random numbers. We use **Canonical Legal Personas**.

| Persona ID | Description | Usage |
| --- | --- | --- |
| `p_asalariado_min` | Minimum wage worker | Test subsidy mechanics (*Subsidio al Empleo*) |
| `p_resico_limite` | Freelancer earning $3.5M | Test the "exit condition" of RESICO regime |
| `p_moral_lucro` | Standard SA de CV | Test Coeficiente de Utilidad |
| `p_border_zone` | Worker in Tijuana | Test 8% IVA / Border Stimulus |

**Agent Directive:** When writing a new test, import these personas from `tests/fixtures/personas.json`. Do not invent "John Doe" with arbitrary numbers.

---

## 5. CI/CD Gatekeepers

Code cannot merge to `main` unless:

1. **Syntax:** XML and Python linting passes.
2. **Logic:** All Catala proofs verify.
3. **Accuracy:** Output matches the "Oracle" dataset (scraped results from SAT) within a $0.01 MXN tolerance.
4. **Legal Review:** (Human Step) A maintainer with the `legal-reviewer` tag approves the interpretation.
