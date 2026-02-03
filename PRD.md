Based on our research, here is the Product Requirements Document (PRD) for the **`leyes-como-codigo-mx`** repository.

This document outlines the strategy to transform the Mexican legal system from a static collection of PDFs into an isomorphic, executable codebase.

---

# Product Requirements Document (PRD)

## Project Name: Leyes Como Código México

**Repository Name:** `madfam-org/leyes-como-codigo-mx`
**License:** GNU Affero General Public License v3.0 (AGPL-3.0)
**Version:** 0.1.0 (Inception)

---

## 1. Executive Summary

**Vision:** To establish a public, open-source, and cryptographically verifiable repository where the entirety of Mexican Law exists as executable code ("Rules as Code").
**Mission:** To bridge the gap between *Normativity* (what the law says) and *Execution* (what happens in reality) by creating a "State API" that is accessible to all—from the Supreme Court Justice to the rural entrepreneur.
**Core Philosophy:** "Code is Law, Law is Code." The repository serves as a mirror where every legal text (`.xml`) has a corresponding logical representation (`.catala`, `.blawx`) that creates a deterministic output.

---

## 2. Target Audience & Personas

* **The Entrepreneur (PyME):** Needs to know exact tax liabilities (ISR/IVA) without hiring expensive firms. Needs an API to integrate compliance directly into their point-of-sale software.
* **The Citizen (Beneficiary):** Needs to know eligibility for social programs (e.g., *Pensión Bienestar*) via a simple interface, even with low connectivity.
* **The Legislator:** Needs to simulate the budgetary impact of a proposed reform before voting on it (Policy Microsimulation).
* **The Developer:** Needs a clean JSON/GraphQL API to build legal-tech apps without scraping broken government websites.

---

## 3. Technical Architecture (The Stack)

The repository will be structured into three distinct layers, mirroring the "MOLE" architecture identified in our research.

### Layer 1: Structural Data (The "Git for Law")

* **Standard:** **Akoma Ntoso (LegalDocML)**. This is the UN standard for parliamentary documents.
* **Function:** Stores the text of the law with rigorous semantic tagging (e.g., distinguishing between a `date`, a `penalty`, and a `definition`).
* **Source of Truth:** Scrapers monitoring the *Diario Oficial de la Federación* (DOF) and *Orden Jurídico Nacional* (OJN).


* **File Structure:**
/leyes
/federal
/constitucion
/CPEUM-2024-05-01.xml (Akoma Ntoso)
/codigo-fiscal
/CFF-2024.xml
/estatal
/guanajuato
/codigo-civil.xml

### Layer 2: Semantic Knowledge (The "Brain")

* **Tools:** Python, **SpaCy** (NLP), RDF/OWL Ontologies.
* **Function:** A Knowledge Graph mapping legal concepts. It links the term "Salario Mínimo" in a contract to the specific numeric value defined in the annual commission resolution.
* **Identifier System:** Implementation of **ELIs (European Legislation Identifiers)** adapted for Mexico (e.g., `/mx/fed/ley/isr/2024/art/10`).

### Layer 3: Executable Logic (The "Engine")

* **Domain 1: Algorithmic Law (Tax & Benefits)**
* **Language:** **Catala**.


* **Reason:** Formally verifiable language designed for tax codes. Prevents "interpretation bugs."


* **Domain 2: Logic & Rules (Civil/Penal)**
* **Language:** **Blawx** (Prolog-based).


* **Reason:** Handles complex logic with exceptions (e.g., "Forbidden, *unless* X").


* **Simulation:** **OpenFisca** (Python wrapper).


* **Reason:** For calculating impacts on populations (microsimulation).



---

## 4. Roadmap to Maturity

### Phase 1: Foundation & "The Git for Law" (Months 1-6)

* **Goal:** A clean, version-controlled mirror of federal laws.
* **Key Deliverables:**
1. **Scraper Pipeline:** Python scripts (`juriscraper` fork) targeting the OJN and Chamber of Deputies sites to fetch DOCX/PDFs.


2. **Indigo Implementation:** Fork and deploy the **Indigo Platform** (by Laws.Africa) to manage Akoma Ntoso conversion.


3. **Git Repository:** Initialize `leyes-como-codigo-mx`. Every legislative reform found by the scraper triggers a new Commit.
4. **Viewer:** A static web frontend (GitHub Pages) rendering the XML as human-readable HTML.



### Phase 2: The Logic Pilot (Months 7-12)

* **Goal:** "The First Executable Law." Proof of concept.
* **Target:** *Ley del Impuesto Sobre la Renta* (LISR) - Title IV (Personal Income Tax).
* **Action:**
1. **Catala Transcription:** "Pair programming" sessions with a tax lawyer and a developer.


2. **Unit Testing:** Write tests against the SAT's own manual scenarios to prove the code returns the exact same tax calculation as the government.
3. **Release:** `npm install @madfam-org/lisr-mexico`. A JS library that computes income tax with legal certitude.



### Phase 3: The Semantic Web (Months 13-18)

* **Goal:** Connect the dots.
* **Deliverables:**
1. **Mexican Legal Ontology:** Defined in OWL. Maps terms like "UMA" (Unit of Measurement and Update) to their dynamic values.


2. **NLP Tagger:** An AI model (SpaCy/BERT fine-tuned on Mexican legal text) that automatically tags entities in the XML files (e.g., identifying "Secretaría de Salud" as an `Organization`).


3. **Cross-Linking:** Automatic hyperlinking. Clicking "Article 123" in the Labor Law takes you to Article 123 of the Constitution.



### Phase 4: Maturity & Federation (Months 18+)

* **Goal:** State-level adoption and full API.
* **Deliverables:**
1. **The State API:** A unified REST/GraphQL endpoint (`api.leyes.mx`) allowing queries like: `GET /calculate/isr?income=50000&state=NL`.
2. **Federation Kit:** A Docker container for State Congresses (e.g., Nuevo León, Jalisco) to spin up their own node of the engine and maintain their local laws.
3. **Visual Editor:** Implementation of Blawx's block-based coding interface so non-technical lawyers can contribute rules.





---

## 5. Accessibility & Inclusivity Standards

To ensure this resource serves *all* of Mexico, not just the tech-elite:

* **Low-Bandwidth First:** The "Viewer" must be static HTML, functional on 3G networks and older Android devices common in rural Mexico.
* **Offline First:** The entire legal corpus must be downloadable as a compressed SQLite file for offline access in remote communities.
* **Plain Language Layer:** Integration of a "Sumarizador" (Summarizer) using a local LLM to provide simplified explanations of complex articles for citizens with lower literacy levels.
* **Multilingual Support:** Architecture must support future translations into indigenous languages (Nahuatl, Maya), leveraging the Akoma Ntoso `<expression>` tag.

---

## 6. Contribution & Governance

* **Open Maintainership:** While `madfam-org` initiates, maintainership will be federated to trusted legal clinics (University Law Schools like UNAM/IIJ) and civic tech NGOs (e.g., Codeando México).


* **Verification Process:** Code cannot be merged into `main` without a "Legal Review" (lawyer) and "Code Review" (developer).
* **AGPLv3 Enforcement:** Ensures that any corporation (e.g., tax software giants) modifying the engine must contribute those improvements back to the community.

---

## 7. Success Metrics

* **Coverage:** % of Federal Laws converted to valid Akoma Ntoso XML.
* **Execution:** % of the *Ley del ISR* successfully covered by Unit Tests.
* **Adoption:** Number of external projects (startups, NGOs) importing the NPM/Python packages.
* **Latency:** Time between a publication in the *Diario Oficial* and its appearance as a Commit in the repo (Target: < 24 hours).
