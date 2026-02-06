# Data Acquisition Escalation Playbook

This playbook defines the five-tier escalation process for acquiring missing law data in the **leyes-como-codigo-mx** platform. Each tier represents an increase in human effort, institutional involvement, and turnaround time. The goal is to resolve data gaps at the lowest possible tier before escalating.

**Audience**: Platform maintainers, data operations team, and contributors.

**Related code**:
- `apps/scraper/dataops/models.py` -- `GapRecord` (tier tracking), `DataSource` (source registry)
- `apps/scraper/dataops/source_discovery.py` -- `SourceDiscoverer` (Tier 1 automation)
- `apps/scraper/dataops/gap_registry.py` -- `GapRegistry` (lifecycle management)
- `apps/scraper/dataops/health_monitor.py` -- `HealthMonitor` (source availability probes)

---

## Tier Overview

| Tier | Method | Effort | Typical Turnaround | Automation |
|------|--------|--------|--------------------|------------|
| 0 | Automated Scraping | None (machine) | Minutes to hours | Fully automated |
| 1 | Web Search + Alt Source Discovery | None (machine) | Hours | Fully automated |
| 2 | Direct Contact with Government IT | Low (email) | 2-4 weeks | Template-assisted |
| 3 | FOIA / Transparency Request (PNT/INAI) | Medium (filing) | 20-40 business days | Template-assisted |
| 4 | Institutional Partnerships | High (negotiation) | Months | Manual |

---

## Tier 0: Automated Scraping

**Precondition**: The source URL is known and registered in `DataSource`.

### Decision Flow

```
Source URL known
  |
  +--> Run scraper
         |
         +--> HTTP 200 + valid content --> SUCCESS (ingest into DB/ES)
         |
         +--> HTTP 404 or 410 ----------> Mark PERMANENT --> Escalate to Tier 1
         |
         +--> HTTP 5xx or timeout -------> TRANSIENT failure
         |      |
         |      +--> Retry up to 3 times (exponential backoff: 30s, 120s, 480s)
         |      |
         |      +--> All retries fail --> Escalate to Tier 1
         |
         +--> Content changed (parse failure on previously working source)
                |
                +--> Likely site redesign --> Escalate to Tier 1
```

### Actions

1. **Run the scraper** for the target `DataSource`. The scraper logs results to `AcquisitionLog`.
2. **On HTTP 200 with valid content**: Mark the `DataSource` as `healthy`. Ingest the downloaded law(s).
3. **On HTTP 404/410**: Update the `GapRecord` status to `permanent` and set `current_tier = 1`.
4. **On HTTP 5xx or timeout**: Retry up to 3 times with exponential backoff. If all retries fail, create or update the `GapRecord` with `current_tier = 1` and `next_action_date` set to 7 days out for a second automated pass.
5. **On content change / parse failure**: If a previously working scraper starts failing due to DOM structure changes, flag the `GapRecord` with `gap_type = site_redesign` and escalate to Tier 1 for alternative source discovery while the scraper is updated.

### Code Reference

The `HealthMonitor` in `health_monitor.py` probes critical sources daily (`OJN Compilacion`, `Diputados Catalog`, `DOF API`) and marks sources as `healthy`, `degraded`, or `down`.

---

## Tier 1: Web Search + Alternative Source Discovery (Automated)

**Precondition**: Tier 0 failed. The source is down, dead, or has been redesigned.

### Discovery Pipeline

The `SourceDiscoverer` class in `source_discovery.py` executes the following checks automatically:

1. **State congress portals**: Probe known URLs from `KNOWN_CONGRESS_PORTALS` (all 32 states mapped). Attempt URL pattern variations from `STATE_CONGRESS_PATTERNS`.
2. **Periodico Oficial del Estado**: Probe state gazette URLs from `PERIODICO_OFICIAL_PATTERNS` for archived legislation text.
3. **Internet Archive Wayback Machine**: Query `https://archive.org/wayback/available` for archived snapshots of the dead source URL.
4. **datos.gob.mx**: Search the federal open data portal for datasets containing legislation metadata or full-text downloads.
5. **Source validation**: For each discovered URL, `validate_discovered_source()` checks accessibility, content type, presence of PDF links, and law-related keywords.

### Decision Flow

```
Tier 1 triggered
  |
  +--> SourceDiscoverer.discover_for_gap(gap_record)
         |
         +--> Alternative source found + validated
         |      |
         |      +--> Create new DataSource entry
         |      +--> Re-run Tier 0 against new source
         |
         +--> No alternative found --> Escalate to Tier 2
```

### Actions

1. Run `SourceDiscoverer.discover_for_gap()` against the `GapRecord`.
2. For each discovered source, run `validate_discovered_source()` to confirm it contains law content.
3. If a valid alternative is found, create a new `DataSource` record and re-enter Tier 0.
4. If no valid alternative is found after exhausting all discovery channels, escalate the `GapRecord` to Tier 2. Set `next_action = "Contact state Unidad de Transparencia or IT office"`.

---

## Tier 2: Direct Contact with Government IT

**Precondition**: Automated discovery (Tiers 0-1) has been exhausted.

### Identifying the Right Contact

For each state, identify the appropriate office in this priority order:

1. **Unidad de Transparencia** of the state congress (Congreso del Estado) -- responsible for public information access.
2. **IT or Systems department** (Direccion de Informatica / Sistemas) of the state congress.
3. **Consejeria Juridica** or equivalent state legal counsel office.
4. **SEGOB's Direccion General de Compilacion y Consulta del Orden Juridico Nacional** -- for issues with the OJN portal (`compilacion.ordenjuridico.gob.mx`).

### Process

1. **Send initial contact email** using the appropriate template from the [Contact Templates](#contact-templates) section below.
2. **Log the attempt** in the `GapRecord.attempts` JSON field with the date, recipient, and method.
3. **Set a 14-day follow-up** (`next_action_date = today + 14 days`).
4. **First follow-up** (Day 14): If no response, send a polite follow-up referencing the original email. Reset `next_action_date` to 14 days.
5. **Second follow-up** (Day 28): If still no response, send a final follow-up stating intent to file a formal transparency request.
6. **After 2 follow-ups with no response** (Day 42+): Escalate to Tier 3.

### Record-Keeping

For each contact attempt, append an entry to `GapRecord.attempts`:

```json
{
  "tier": 2,
  "action": "Email sent to Unidad de Transparencia, Congreso de Michoacan",
  "date": "2026-02-05T10:00:00Z",
  "result": "awaiting_response"
}
```

Update the result field when a response is received (`"response_received"`, `"data_provided"`, `"refused"`, `"no_response"`).

---

## Tier 3: FOIA / Transparency Request (PNT / INAI)

**Precondition**: Government IT contacts are unresponsive or unable to help after Tier 2 follow-ups.

### Filing a Request

Mexico's transparency framework provides a legal right to request public information. File through the **Plataforma Nacional de Transparencia (PNT)**.

1. **Portal**: [https://www.plataformadetransparencia.org.mx/](https://www.plataformadetransparencia.org.mx/)
2. **Create an account** (or use an existing one). Requests can be filed by any person; no citizenship requirement.
3. **Select the target entity** (sujeto obligado): the specific state congress, executive branch office, or municipal government that holds the data.
4. **Draft the request**: Reference **Ley General de Transparencia y Acceso a la Informacion Publica, Articulo 70, Fraccion I**, which requires public entities to publish their normative framework (marco normativo).
5. **Submit** and record the **folio number** (request tracking ID).

### Legal Timeline

Per the Ley General de Transparencia:

- **20 business days** for the entity to respond (Articulo 132).
- **10 business day extension** is permitted if the entity notifies in writing (Articulo 132).
- **Response types**: Full disclosure, partial disclosure with justification, declaration of nonexistence, or incompetence referral.

### If the Request Is Denied

1. **File an appeal** (recurso de revision) with the appropriate body:
   - Federal entities: **INAI** (Instituto Nacional de Transparencia, Acceso a la Informacion y Proteccion de Datos Personales).
   - State entities: The corresponding state transparency commission (e.g., ITEI Jalisco, INFOCDMX, ITAIP Nuevo Leon).
2. The appeal must be filed within **15 business days** of receiving the denial.
3. The reviewing body has **40 business days** to issue a resolution (Articulo 155).

### Record-Keeping

Track in `GapRecord`:

```json
{
  "tier": 3,
  "action": "PNT request filed - Folio XXXXXXXX",
  "date": "2026-03-01T10:00:00Z",
  "result": "pending_response"
}
```

Set `next_action_date` to 30 business days (approximately 42 calendar days) from filing.

---

## Tier 4: Institutional Partnerships

**Precondition**: Individual requests have not resolved the gap, or the gap requires ongoing data access that cannot be sustained through one-off requests.

### Target Institutions

| Category | Institutions | Value Proposition |
|----------|-------------|-------------------|
| Government | SEGOB (Secretaria de Gobernacion), Consejeria Juridica del Ejecutivo Federal | Direct access to compilacion data, official gazette feeds |
| Legislative | Camara de Diputados, Senado de la Republica, state congresses | Legislative text, reform tracking, committee records |
| Academic | CIDE (Centro de Investigacion y Docencia Economicas), ITAM (Instituto Tecnologico Autonomo de Mexico), UNAM IIJ (Instituto de Investigaciones Juridicas) | Research collaboration, data validation, academic credibility |
| Civil Society | Mexico Abierto, Gobierno Facil, Codeando Mexico | Open data advocacy, shared infrastructure, community reach |

### Process

1. **Draft a collaboration proposal** using the template in the [Contact Templates](#contact-templates) section.
2. **Identify a champion**: Find an internal contact or shared connection who can introduce the project.
3. **Propose a Memorandum of Understanding (MOU)** or a less formal data-sharing agreement, depending on the institution's requirements.
4. **Define the data exchange**: Specify what data is needed, in what format, at what frequency, and under what license.
5. **Establish a review cadence**: Quarterly check-ins to ensure the partnership is delivering value to both parties.

### What to Offer Partners

- Attribution and co-branding on the platform.
- API access to structured legal data.
- Research collaboration opportunities (computational law, NLP on legislation, legislative analytics).
- Technical support for their own data publication efforts.
- Open-source tooling (scrapers, parsers, Akoma Ntoso converters) that partners can reuse.

---

## Escalation Summary Flowchart

```
[Data Gap Identified]
        |
        v
  TIER 0: Scrape
   |           |
 SUCCESS    FAIL (404/5xx/redesign)
   |           |
   v           v
 [Done]   TIER 1: Auto-discover alt sources
            |              |
          FOUND          NOT FOUND
            |              |
            v              v
        Tier 0 again   TIER 2: Email gov IT
                         |             |
                       RESPONSE    NO RESPONSE (2 follow-ups)
                         |             |
                         v             v
                       [Done]      TIER 3: PNT/FOIA request
                                     |              |
                                   GRANTED        DENIED
                                     |              |
                                     v              v
                                   [Done]     Appeal to INAI
                                                |          |
                                              GRANTED    DENIED
                                                |          |
                                                v          v
                                              [Done]   TIER 4: Partnership
                                                            |
                                                            v
                                                    [Negotiate MOU]
```

---

## Contact Templates

### Template 1: Missing Laws from State Congress

**Purpose**: Formal transparency request to a state congress Unidad de Transparencia, requesting digital copies of their complete legislation catalog.

**Use when**: Tier 2 or Tier 3 escalation for states with missing or inaccessible legislation.

**Language**: Spanish (required for government correspondence).

---

> **Asunto**: Solicitud de acceso a catalogo digital de legislacion estatal vigente
>
> Estimada Unidad de Transparencia del H. Congreso del Estado de [ESTADO]:
>
> Por medio de la presente, y con fundamento en los articulos 4, 6 y 70 fraccion I de la Ley General de Transparencia y Acceso a la Informacion Publica, me permito solicitar la siguiente informacion:
>
> **Informacion solicitada**:
>
> Copia digital del catalogo completo de legislacion vigente del Estado de [ESTADO], incluyendo:
>
> 1. Constitucion Politica del Estado
> 2. Leyes y codigos estatales vigentes
> 3. Reglamentos vigentes emitidos por el Congreso
> 4. Decretos legislativos vigentes
>
> Se solicitan los documentos en formato digital (PDF o texto), preferentemente con la version mas actualizada que obre en los archivos del H. Congreso.
>
> **Contexto y proposito**:
>
> Esta solicitud se realiza en el marco del proyecto de datos abiertos "Leyes como Codigo Mexico", cuyo objetivo es facilitar el acceso ciudadano a la legislacion mexicana en formatos abiertos y estructurados. El proyecto busca contribuir al derecho de acceso a la informacion consagrado en el articulo 6o. constitucional.
>
> **Fundamento legal**:
>
> El articulo 70 fraccion I de la Ley General de Transparencia establece que los sujetos obligados deberan poner a disposicion del publico su marco normativo aplicable. En caso de que esta informacion se encuentre publicada en un portal web de acceso libre, agradecere se me proporcione la URL correspondiente.
>
> **Formato de entrega preferido**: Archivos digitales (PDF o texto plano) mediante la plataforma, correo electronico o enlace de descarga.
>
> Agradezco de antemano su atencion a la presente solicitud.
>
> Atentamente,
>
> [NOMBRE COMPLETO]
> [CORREO ELECTRONICO]
> Proyecto Leyes como Codigo Mexico
> [URL DEL PROYECTO]

---

### Template 2: Dead OJN Links Notification

**Purpose**: Notify SEGOB's Direccion General de Compilacion y Consulta del Orden Juridico Nacional about dead links on the OJN portal.

**Use when**: Tier 2 escalation for `dead_link` gap records sourced from `compilacion.ordenjuridico.gob.mx`.

**Language**: Spanish (required for government correspondence).

---

> **Asunto**: Reporte de enlaces inaccesibles en el portal de Compilacion del Orden Juridico Nacional
>
> Estimada Direccion General de Compilacion y Consulta del Orden Juridico Nacional:
>
> Me permito informar a esa Direccion General que se han detectado enlaces inaccesibles (errores HTTP 404/410) en el portal de Compilacion del Orden Juridico Nacional (https://compilacion.ordenjuridico.gob.mx/).
>
> **Resumen del reporte**:
>
> - **Total de enlaces inaccesibles detectados**: [NUMERO_TOTAL] (de los cuales [NUMERO_PERMANENTES] presentan errores permanentes 404/410)
> - **Estados mas afectados**: [LISTA_DE_ESTADOS]
> - **Fecha de verificacion**: [FECHA]
> - **Metodo de verificacion**: Solicitudes HTTP automatizadas con reintentos, ejecutadas desde multiples ubicaciones durante un periodo de [PERIODO].
>
> **Detalle por estado (muestra representativa)**:
>
> | Estado | file_id (OJN) | Tipo de error | URL |
> |--------|--------------|---------------|-----|
> | [ESTADO_1] | [FILE_ID_1] | 404 Not Found | https://compilacion.ordenjuridico.gob.mx/fichaOrdenamiento2.php?idArchivo=[FILE_ID_1]&ambession= |
> | [ESTADO_2] | [FILE_ID_2] | 410 Gone | https://compilacion.ordenjuridico.gob.mx/fichaOrdenamiento2.php?idArchivo=[FILE_ID_2]&ambession= |
> | [ESTADO_3] | [FILE_ID_3] | 404 Not Found | https://compilacion.ordenjuridico.gob.mx/fichaOrdenamiento2.php?idArchivo=[FILE_ID_3]&ambession= |
>
> Se puede proporcionar el listado completo de file_ids afectados en formato CSV o JSON si resulta util para su equipo tecnico.
>
> **Solicitud**:
>
> 1. Confirmacion de recepcion de este reporte.
> 2. Informacion sobre si los documentos referenciados seran restaurados o si han sido dados de baja del acervo digital.
> 3. En caso de que los documentos se encuentren disponibles en una ubicacion alternativa, se agradecera la referencia correspondiente.
>
> Este reporte se realiza en el marco del proyecto de datos abiertos "Leyes como Codigo Mexico", que busca ampliar el acceso ciudadano a la legislacion mexicana. Quedamos a disposicion para colaborar con su equipo en la identificacion y correccion de estos enlaces.
>
> Atentamente,
>
> [NOMBRE COMPLETO]
> [CORREO ELECTRONICO]
> Proyecto Leyes como Codigo Mexico
> [URL DEL PROYECTO]

---

### Template 3: Institutional Collaboration Proposal

**Purpose**: Formal partnership proposal for ongoing open law data sharing.

**Use when**: Tier 4 escalation targeting academic institutions (CIDE, ITAM, UNAM IIJ) or government offices interested in structured data collaboration.

**Language**: English (suitable for bilingual academic and international audiences; translate to Spanish as needed for domestic government entities).

---

> **Subject**: Collaboration Proposal -- Open Law Data Partnership
>
> Dear [NAME / TITLE],
>
> I am writing on behalf of **Leyes como Codigo Mexico**, an open-source platform dedicated to making Mexican legislation accessible, searchable, and machine-readable. We currently index over 11,000 federal, state, and municipal laws and are working toward comprehensive national coverage.
>
> **Proposal Summary**
>
> We would like to explore a data-sharing partnership with [INSTITUTION NAME] to improve the completeness and accuracy of publicly available Mexican legal data. Specifically, we propose:
>
> 1. **Data Exchange**: [INSTITUTION NAME] provides access to [SPECIFIC DATA -- e.g., legislative text databases, gazette archives, or reform tracking systems]. In return, we offer full API access to our structured legal data corpus, including full-text search, cross-reference mappings, and version history.
>
> 2. **Technical Collaboration**: Our open-source tooling -- including scrapers, Akoma Ntoso XML parsers, and an Elasticsearch-backed search engine -- is available for [INSTITUTION NAME] to use, adapt, or extend for its own data publication needs.
>
> 3. **Research Opportunities**: The platform provides a rich dataset for research in computational law, legislative analytics, natural language processing on legal text, and regulatory impact analysis. We welcome joint research proposals and are open to co-authorship on publications.
>
> **About the Platform**
>
> - **Coverage**: 11,600+ laws across federal, state, and municipal levels (87% of estimated total)
> - **Data quality**: 98.9% parser accuracy on structured legal text
> - **Technology**: Django REST API, Elasticsearch, Next.js frontend, Celery task pipeline
> - **License**: Open source (code and data)
> - **Standards**: Akoma Ntoso XML for legislative markup; structured metadata in PostgreSQL
>
> **What We Seek**
>
> - Access to [SPECIFIC DATA GAPS -- e.g., "complete state legislation catalogs for states where online portals are incomplete or down"]
> - A designated point of contact for data quality issues and update coordination
> - Willingness to explore a Memorandum of Understanding (MOU) or lighter-weight data-sharing agreement
>
> **What We Offer**
>
> - Attribution and co-branding on the platform for contributing partners
> - Full API access to structured legal data (REST + Elasticsearch)
> - Open-source tools: scrapers, parsers, cross-reference detection, and ingestion pipelines
> - Technical support for data publication and open data compliance
> - Quarterly progress reports and review meetings
>
> We would be happy to schedule a call or meeting to discuss this proposal in more detail. I have attached a brief project overview document for your reference.
>
> Thank you for your time and consideration.
>
> Sincerely,
>
> [YOUR NAME]
> [YOUR TITLE]
> Leyes como Codigo Mexico
> [EMAIL]
> [PROJECT URL]

---

## Operational Notes

### Priority Assignment

Gaps are assigned a priority from 1 (highest) to 5 (lowest) based on impact:

| Priority | Criteria | Example |
|----------|----------|---------|
| 1 | Federal law missing or inaccessible | Constitution, federal codes |
| 2 | State with >100 dead links or suspiciously low count | Michoacan (504 dead links), EDOMEX (141) |
| 3 | State with <100 dead links or unscraped OJN powers | SLP (47), powers 1/3/4 |
| 4 | Missing source category (no scraper exists) | NOMs, Periodicos Oficiales |
| 5 | Low-priority or long-term aspirations | SIL tracking, international treaties |

### SLA by Tier

| Tier | Target Resolution Time | Escalation Trigger |
|------|----------------------|-------------------|
| 0 | Same day | 3 failed retries |
| 1 | 7 days | No valid source discovered |
| 2 | 42 days (14 days x 3 attempts) | 2 follow-ups with no response |
| 3 | 60 business days (request + appeal) | Denial without legal basis |
| 4 | 90 days (initial contact to MOU) | No institutional interest |

### Known High-Priority Gaps (as of February 2026)

- **782 permanent dead links on OJN**: Michoacan (504), Estado de Mexico (141), San Luis Potosi (47), remaining states (<30 each).
- **23,660 laws in OJN powers 1/3/4**: State-level Ejecutivo, Judicial, and Organismos Autonomos legislation not yet downloaded.
- **Low-count states**: Durango (1), Quintana Roo (1), Baja California (1), Hidalgo (38) -- likely incomplete OJN data rather than actual counts.
- **Missing scrapers**: DOF daily monitoring, NOMs, SCJN Jurisprudencia, state Periodicos Oficiales.
