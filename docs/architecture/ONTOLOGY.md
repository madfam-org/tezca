# 🧠 ONTOLOGY.md - The Semantic Dictionary of Mexican Law

> **SYSTEM NOTICE:** This file defines the **Domain Model** for the Mexican Legal System. Autonomous agents must strictly adhere to these definitions when naming variables, defining classes, or structuring logic. Do not invent new terms for concepts defined here.

---

## 1. The Hierarchy of Norms (Kelsenian Pyramid)

In any logical conflict between rules, the higher-ranking rule **always** prevails. You must implement this precedence in your logic engines (Blawx/Catala).

1. **Level 0: Supremacy (The Constitution)**
* **Node:** `mx-fed-const-cpeum`
* **Includes:** *Constitución Política de los Estados Unidos Mexicanos* (CPEUM) AND International Human Rights Treaties (Article 1 CPEUM).
* **Logic Rule:** If a lower law contradicts Level 0, the lower law is *Unconstitutional* (invalid), unless a *Jurisprudence* explicitly saves it.


2. **Level 1: General & Federal Laws**
* **Node:** `mx-fed-ley`
* **Examples:** *Código Civil Federal*, *Ley del Impuesto Sobre la Renta*.
* **Scope:** Applies to the entire Federation or specific federal matters.


3. **Level 2: Regulations (Reglamentos)**
* **Node:** `mx-fed-reg`
* **Definition:** Rules issued by the Executive Branch (President) to enable the execution of a Law.
* **Constraint:** A Regulation cannot go beyond the Law it regulates (*Principio de Reserva de Ley*). Code representing a Regulation cannot define a tax; it can only define *how* to pay it.


4. **Level 3: Administrative Rules (Misceláneas & NOMs)**
* **Node:** `mx-fed-rsc` (Resolución), `mx-fed-nom` (Norma Oficial Mexicana).
* **Examples:** *Resolución Miscelánea Fiscal* (RMF).
* **Volatility:** These change frequently (annually or monthly). Code depending on these must be heavily parameterized.



---

## 2. Temporal Logic (Vigencia)

Time is the most critical variable in legal code.

* **Vigencia (Validity):** The period during which a law is active.
* *Start:* `fecha_inicio_vigencia` (usually `D+1` after publication, or specific date).
* *End:* `fecha_fin_vigencia` (when abrogated or expired).


* **Abrogación (Abrogation):** The **total** elimination of a law. It is replaced by a new one.
* *Code Action:* The old file is moved to `/archive`, but remains accessible for historical calculations.


* **Derogación (Derogation):** The partial elimination of specific articles within a valid law.
* *Code Action:* The specific article function returns `None` or raises `DerogatedException` for dates after the derogation.


* **Vacatio Legis:** The gap between publication and entry into force.
* *Code Action:* Logic must check `if current_date >= entry_force_date`.


* **Retroactivity:**
* **Tax/Civil:** STRICTLY FORBIDDEN to apply new laws to old facts (Article 14 CPEUM).
* **Penal:** PERMITTED only if it benefits the accused (*In Dubio Pro Reo*).



---

## 3. Core Entities & Variable Naming

When creating classes or variables in Python/Catala, use these standard English mappings to maintain code readability while preserving Spanish legal precision in comments.

| Spanish Concept | Variable Name | Definition |
| --- | --- | --- |
| **Sujeto Obligado** | `obligated_subject` | The person/entity required to comply (e.g., taxpayer). |
| **Persona Física** | `natural_person` | A human being. |
| **Persona Moral** | `legal_entity` | A corporation, NGO, or association. |
| **Hecho Imponible** | `taxable_event` | The action that triggers a tax (e.g., earning income). |
| **Base Gravable** | `tax_base` | The amount upon which tax is calculated. |
| **Tasa** | `rate` | A percentage applied to the base (e.g., 16% IVA). |
| **Cuota** | `quota` | A fixed amount applied (e.g., $5 pesos per liter). |
| **Salario Mínimo** | `min_wage` | *Warning:* Rarely used now. See UMA. |
| **UMA** | `uma` | *Unidad de Medida y Actualización*. The standard unit for fines and thresholds since 2016. |
| **Zona Fronteriza** | `border_zone` | Specific municipalities with different tax rules (e.g., 8% IVA). |

---

## 4. Jurisdictional Logic (Federalism)

Mexican law is federated. The engine must determine which law applies based on **Territory** and **Subject Matter**.

### 4.1 Subject Matter Competence (Article 124 CPEUM)

* **Residual Principle:** Anything not explicitly granted to the Federation is reserved for the States.
* **Federal Matters (Explicit):** Commerce (*Comercio*), Labor (*Trabajo*), Financial Services, Hydrocarbons, War.
* *Code implication:* A generic contract is usually State Civil Law. A commercial contract is Federal Commercial Code.



### 4.2 The "State" Parameter

Every simulation function must accept a `jurisdiction` parameter.

* `jurisdiction='mx'` -> Federal Law.
* `jurisdiction='mx-nl'` -> Nuevo León State Law.
* `jurisdiction='mx-jal'` -> Jalisco State Law.

---

## 5. Identification Standards (URIs)

We use **ELIs (European Legislation Identifiers)** adapted for Mexico to create unique, machine-readable IDs for every atom of law.

**Template:** `/mx/{jurisdiction}/{type}/{year}/{month}/{day}/{title}/{level_1}/{level_2}`

**Examples:**

* **Whole Law:** `/mx/fed/ley/2013/12/11/lisr` (Ley ISR)
* **Specific Article:** `/mx/fed/ley/2013/12/11/lisr/art/93`
* **Specific Fraction:** `/mx/fed/ley/2013/12/11/lisr/art/93/frac/I`

**Agent Directive:** When generating JSON output or error logs, ALWAYS refer to the source law using this URI format. Do not use vague terms like "The Income Tax Law."
