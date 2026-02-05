# 🛠️ TECH_STACK.md - The Approved Stack & Standards

> **SYSTEM NOTICE:** This file represents the **Immutable Technical Constitution** of this repository. Autonomous agents are strictly forbidden from introducing frameworks, languages, or libraries not listed here without an explicit `RFC` (Request for Comments) approval.

## 1. Core Philosophy: The "Isomorphic" Standard

Our stack is chosen to support **Isomorphism**: the ability to prove that the code is a faithful representation of the law.

* **No "Black Box" AI:** We do not use LLMs to *execute* law. We use LLMs to *parse* and *tag* law. The execution must be deterministic.
* **Open Standards:** We prioritize UN/OASIS standards (Akoma Ntoso) over proprietary JSON schemas.

---

## 2. Layer 1: Structural Data (The Law as Text)

**Goal:** Ingest, structure, and version-control legislative documents.

| Component | Technology | Version | Constraints |
| --- | --- | --- | --- |
| **Standard** | **Akoma Ntoso (LegalDocML)** | V3.0 (OASIS) | All legal text must be stored as `.xml` files complying with the AKN schema. |
| **CMS Platform** | **Indigo** | Latest (Django) | We use a fork of [Laws.Africa Indigo](https://github.com/laws-africa/indigo). This is the core application for managing the legislative database. |
| **Parsing Lib** | **Bluebell** | Latest | Used for parsing raw text/HTML into Akoma Ntoso structures. |
| **XML Wrapper** | **Cobalt** | Latest | Python library for manipulating Akoma Ntoso metadata and URIs without breaking the XML. |
| **Database** | **PostgreSQL** | 14+ | Primary data store for the Indigo platform and relational metadata. |
| **Search** | **Elasticsearch** | 7.x | For full-text search across the legal corpus. |

**Agent Directive:** When ingesting a new PDF, you must use `juriscraper` to fetch it, then pass it through `bluebell` to generate the XML. Do not write custom Regex parsers if `bluebell` can handle the structure.

---

## 3. Layer 2: Executable Logic (The Law as Code)

**Goal:** Transform normative text into executable functions.

| Domain | Language | Extension | Execution Target |
| --- | --- | --- | --- |
| **Tax & Benefits** | **Catala** | `.catala_en` | **Python 3**. The Catala compiler (`catala-c`) translates the `.catala` file into a Python module that OpenFisca consumes. |
| **General Rules** | **Blawx** | `.blawx` | **s(CASP) / SWI-Prolog**. Used for qualitative logic (e.g., "Is this person a public servant?"). |
| **Microsimulation** | **OpenFisca** | Python Lib | Used to run the compiled Catala modules against population data. |

**Agent Directive:**

* **Strict Typing:** Catala is strictly typed. You cannot mix `Money` and `Integer` without explicit conversion.
* **Literate Programming:** Every `.catala` file **MUST** contain the Markdown text of the law it implements, interleaved with the code. Code without the accompanying legal text is considered "Technical Debt" and will be rejected.

---

## 4. Layer 3: The Semantic Brain

**Goal:** Connect concepts across the federation.

| Component | Tool | Usage |
| --- | --- | --- |
| **NLP Pipeline** | **SpaCy** | Use `es_core_news_lg` as the base model. |
| **Legal NER** | **Custom SpaCy Model** | We train custom pipes to recognize Mexican entities: `Secretaría`, `Tribunal`, `Decreto`, `UMA`. |
| **Ontology** | **OWL / RDF** | Stored in `/ontology`. Defines relationships like `is_subordinate_to` or `repeals`. |

---

## 5. Layer 4: Infrastructure & API

**Goal:** Serve the data to the public.

* **Language:** Python 3.11+
* **API Framework:** **Django REST Framework** (Integrated with Indigo).
* **Task Queue:** Celery + Redis (for processing large PDF ingestion jobs).
* **Containerization:** Docker & Docker Compose.
* **Formatting:** `Black` (Python), `Prettier` (XML/Markdown).

---

## 6. Directory Structure Standards

/
├── apps/
│   ├── indigo/          # The core legislation management app (Forked)
│   ├── api/             # The public-facing State API
│   └── scraper/         # Juriscraper spiders for DOF/OJN
├── data/
│   ├── federal/         # Akoma Ntoso XML files (The "Git for Law")
│   └── ontology/        # OWL/RDF definitions
├── engines/
│   ├── catala/          # Tax algorithms (.catala files)
│   ├── blawx/           # Rule logic (.blawx files)
│   └── openfisca/       # Python wrappers for the engines
└── scripts/             # DevOps and maintenance scripts

## 7. Forbidden Practices 🚫

1. **No Excel Logic:** Never embed calculation logic in CSVs or Excel files. Logic lives in Catala.
2. **No Monkey-Patching:** Do not modify the core `indigo` library files directly. Use Django signals or inheritance/mixins to extend functionality.
3. **No "Magic Numbers":** Hardcoded tax rates (e.g., `0.16` for IVA) are forbidden in code. They must be defined as **Parameters** in the Catala files with temporal validity (e.g., `IVA rate applies from 2014-01-01`).
