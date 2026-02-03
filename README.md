# 🇲🇽📜 Leyes Como Código México (Mexican Open Law Engine)

> **"Code is Law, Law is Code."**
> Transformando el orden jurídico mexicano de texto estático a código ejecutable, abierto e isomórfico.

[](https://www.gnu.org/licenses/agpl-3.0)
([https://img.shields.io/badge/Standard-Akoma_Ntoso_V3-orange](https://www.google.com/search?q=https://img.shields.io/badge/Standard-Akoma_Ntoso_V3-orange))]([http://www.akomantoso.org/](http://www.akomantoso.org/))
[](https://www.google.com/search?q=%5Bhttps://catala-lang.org/%5D(https://catala-lang.org/))
([https://img.shields.io/badge/Engine-Blawx-yellow](https://www.google.com/search?q=https://img.shields.io/badge/Engine-Blawx-yellow))]([https://www.blawx.com/](https://www.blawx.com/))
([https://img.shields.io/badge/Status-Pre--Alpha-red](https://www.google.com/search?q=https://img.shields.io/badge/Status-Pre--Alpha-red))]([https://github.com/madfam-org/leyes-como-codigo-mx](https://www.google.com/search?q=https://github.com/madfam-org/leyes-como-codigo-mx))

---

## 📖 Introduction

**Leyes Como Código México** (Mexican Open Law Engine) is an open-source initiative to digitize, structure, and encode the entirety of the Mexican Legal System.

Currently, the law exists as PDF and Word documents scattered across government portals like the *Orden Jurídico Nacional* (OJN) and the *Diario Oficial de la Federación* (DOF). This format is **read-only**. It requires human interpretation for every single query, leading to high compliance costs, opacity, and inequality in access to justice.

**We are building the "State API".**
By converting laws into **Akoma Ntoso** (structure) and **Catala/Blawx** (logic), we turn the law into a database that machines can understand, query, and execute deterministically.

### 🎯 The Goal

To enable a future where:

1. **Entrepreneurs** calculate their exact taxes via an open API, not expensive proprietary software.
2. **Citizens** instantly know their eligibility for social programs (*Bienestar*) without standing in line.
3. **Legislators** can simulate the budgetary impact of a reform *before* voting on it.

---

## 🏗️ Architecture: The 3-Layer Stack

We strictly separate the **Normative Source** (the text) from the **Executable Artifact** (the code) to ensure legal validity.

| Layer | Function | Technology | Status |
| --- | --- | --- | --- |
| **1. Structure** | **The "Git for Law".** A version-controlled history of every statute, reform, and decree. | **Akoma Ntoso (XML)**, **Indigo** | 🚧 In Progress |
| **2. Semantics** | **The "Brain".** A Knowledge Graph linking concepts (e.g., *Sujeto Obligado* -> *SAT*). | **RDF/OWL**, **SpaCy NLP** | 📅 Planned |
| **3. Logic** | **The "Engine".** Executable functions that take inputs (income, facts) and return legal outputs (tax due, verdict). | **Catala** (Fiscal), **Blawx** (Rules) | 📅 Planned |

---

## 🚀 Quick Start

### Prerequisites

* Python 3.9+
* Docker & Docker Compose
* Node.js (for the Viewer)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/madfam-org/leyes-como-codigo-mx.git
cd leyes-como-codigo-mx

# 2. Install dependencies (using Poetry)
poetry install

# 3. Spin up the Indigo Platform (Database & API)
docker-compose up -d

# 4. Run the Scraper (Fetch latest DOF updates)
poetry run python scrapers/dof_daily.py --date=today

```

### Usage Example: Querying the Law (Mock)

```python
from leyes_mx.api import LawEngine

# Load the Income Tax Law (LISR) for 2024
lisr = LawEngine.load('mx-fed-ley-lisr-2024')

# Calculate ISR for a specific persona
result = lisr.calculate(
    rule="article_96_monthly_retention",
    inputs={
        "income_monthly": 25000.00,
        "regime": "sueldos_y_salarios"
    }
)

print(f"Tax Due: ${result.amount} MXN")
print(f"Legal Basis: {result.trace}") 
# Output: Tax Due: $3,840.50 MXN
# Legal Basis:

```

---

## 🗺️ Roadmap

We are currently in **Phase 1**.

* **Phase 1: Foundation (Months 1-6)** 👈 *We are here*
* [ ] Build scrapers for OJN and Chamber of Deputies.
* [ ] Deploy Indigo platform for managing Akoma Ntoso XML.
* [ ] Ingest the *Constitución Política (CPEUM)* and *Código Civil Federal*.


* **Phase 2: The Fiscal Pilot (Months 7-12)**
* [ ] Encode *Título IV* of the **Ley del ISR** in Catala.
* [ ] Achieve mathematical parity with the SAT simulator.
* [ ] Release the first NPM/Python calculation packages.


* **Phase 3: Semantic Web & Rules (Months 13-18)**
* [ ] Train NLP models to auto-tag entities (Institutions, Dates, Fines).
* [ ] Implement **Blawx** for qualitative logic (e.g., Civil Code rules).


* **Phase 4: The State API (Maturity)**
* [ ] Public GraphQL API gateway.
* [ ] Federation kit for State Congresses (Jalisco, Nuevo León, etc.).



---

## 🤖 For AI Agents

If you are an autonomous agent (LLM) contributing to this repo, **YOU MUST READ** the following files before making changes:

1. (./AGENTS.md) - Your core instructions and persona.
2. (./TECH_STACK.md) - Allowed libraries and constraints.
3. (./ONTOLOGY.md) - The dictionary of legal concepts.

**Strict Rule:** Never hallucinate legal text. If the XML does not match the PDF from the government, the build fails.

---

## 🤝 Contributing

We welcome contributions from **Lawyers**, **Developers**, and **Legal Engineers**.

### For Developers

* See(./CONTRIBUTING.md) for code standards.
* We use **Conventional Commits**.
* All logic changes require a regression test against the "Oracle" (SAT/Government calculators).

### For Lawyers

* You don't need to know Python! You can contribute by:
* Validating the structure of Akoma Ntoso files.
* Defining test cases ("Hypotheticals") for the logic engines.
* Using the **Blawx** visual interface (coming soon).



---

## ⚖️ Disclaimer

**This repository is NOT legal advice.**
While we strive for **Isomorphism** (exact correspondence with the law), the official source of truth remains the *Diario Oficial de la Federación* and the printed gazettes of the State Congresses. Use this code for simulation, compliance automation, and research, but always consult a qualified attorney for specific legal matters.

**License:** This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. If you use this engine in a public-facing application, you must open-source your modifications.

---

<div align="center">
<sub>Built with ❤️ by <a href="[https://github.com/madfam-org](https://www.google.com/search?q=https://github.com/madfam-org)">madfam-org</a> and the Open Source Community.</sub>





<sub><i>"La ignorancia de la ley no exime de su cumplimiento." — Ahora, el código tampoco.</i></sub>
</div>
