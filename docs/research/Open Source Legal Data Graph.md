# **Architecting a National Legal Knowledge Graph: Permissive Open-Source Technologies for the Mexican Legal Framework**

The digitization, semantic structuring, and topological mapping of a national legal system represent one of the most formidable challenges in modern computational jurisprudence and data science. The Mexican legal framework constitutes a vast, deeply hierarchical, and intricately interconnected universe of constitutional mandates, federal codes, state laws, regulatory decrees, and binding supreme court jurisprudence. Traditionally, this massive corpus has existed as a highly fragmented collection of unstructured or semi-structured flat-text documents distributed across various government portals. Transforming this static, document-centric repository into a computationally accessible, dynamic, and highly interconnected data universe requires a fundamental paradigm shift. Specifically, it necessitates the architectural transition toward a Legal Knowledge Graph (LKG), a sophisticated data structure that maps legal entities, statutory provisions, jurisdictional metadata, and their complex cross-references as discrete nodes and semantic edges.

The technological stack required to ingest, process, store, interrogate, and visualize this colossal data universe must inherently possess extreme horizontal scalability, robust fault tolerance, and high-performance querying capabilities. Furthermore, to ensure sovereign control, prevent vendor lock-in, and foster collaborative civic-tech innovation, this infrastructure must be governed by permissive open-source licenses. Permissive licenses, such as the MIT License, the Apache License 2.0, and the BSD 2-Clause License, are highly preferred in enterprise and governmental architectures because they allow for extensive modification, commercial use, and private distribution without the restrictive copyleft constraints imposed by licenses like the GNU General Public License (GPL).1 The Apache License 2.0, in particular, provides explicit patent grants and critical protection against patent trolling, thereby serving as a legally robust foundation for building scalable, mission-critical national infrastructure.3

The ensuing comprehensive analysis delineates the optimal open-source technology stack necessary to leverage the entirety of the Mexican legal framework. By evaluating architectural solutions spanning ontological modeling, distributed graph database storage, natural language processing (NLP), and WebGL-based network visualization, this report provides a definitive blueprint for constructing a Mexican Legal Knowledge Graph under MIT, Apache 2.0, or equivalent permissive licensing frameworks.

## **The Mexican Legal Data Ecosystem: Scale, Volatility, and Context**

To properly architect a graph database capable of representing the Mexican legal system, system designers must first decode the structural nuances, sheer scale, and dynamic volatility of the underlying data. Mexico operates under a civil law system, deeply influenced by Roman law traditions, which relies heavily on codified statutes rather than the purely precedent-based approach characteristic of common law jurisdictions.5 The hierarchy of legal norms places the Political Constitution of the United Mexican States at the absolute apex, followed in descending order by international treaties, federal laws, state laws, and local municipal regulations.6

New legislation, presidential decrees, and regulatory acts are officially promulgated through the Diario Oficial de la Federación (DOF), which serves as the official government organ in charge of publishing laws, agreements, and circulars issued by the Powers of the Federation.7 Concurrently, the Supreme Court of Justice of the Nation (SCJN) interprets these laws, defends the Constitution, and maintains the balance between the different spheres of government.6 In the Mexican judicial system, binding precedent (known as *jurisprudencia*) is historically formed when the SCJN issues five consecutive rulings with the identical legal criteria on a specific issue, although recent constitutional reforms have shifted this mechanism toward a system of precedents established by a qualified majority in a single ruling.10

### **The Scale of the Unstructured Corpus**

The sheer volume of this legal universe is staggering. A foundational academic effort to digitize and structure a minute subset of this data was undertaken by researchers at the Instituto Politécnico Nacional (UPIITA-IPN), who successfully created a unified, labeled, and semi-structured database of pre-processed Mexican laws.7 This limited corpus alone contains 305 documents, encompassing the Mexican Constitution, 289 federal laws, codes, and regulations, comprising a total of 27,404 distinct articles with an average of 91.95 articles per document.12 When scaling this methodology to encompass the entire historical archives of the DOF, the millions of physical files digitized by the SCJN during its digital transformation initiatives 6, and the state-level legislation across all 32 federal entities, the resulting knowledge graph will easily comprise hundreds of millions of discrete nodes and billions of semantic edges.

The complexity is further compounded by the continuous integration of specialized regulatory frameworks, such as the complex energy sector reforms and environmental regulations, where interconnected decrees constantly modify existing operational parameters for state-owned enterprises like Pemex and private providers.7 Furthermore, Mexican data protection laws, overseen by the National Institute for Transparency, Access to Information and Personal Data Protection (INAI), introduce additional layers of regulatory compliance that must be mapped accurately.15

### **Systemic Volatility and Institutional Transformations**

The Mexican legal framework is highly dynamic and subject to profound structural volatility. A static database architecture is entirely insufficient to capture this reality. For instance, the 2025 judicial elections marked an unprecedented institutional transformation, filling 881 judicial positions including ministers, judges, and magistrates through a direct public vote aimed at democratizing the justice system.16 This massive turnover in judicial personnel generates new vectors of jurisprudential interpretation that must be tracked dynamically.

Furthermore, recent SCJN rulings highlight the rapid evolution of digital law within the jurisdiction. In 2025, the Second Chamber of the SCJN unanimously ruled that works autonomously generated by artificial intelligence (in this specific case, a digital work created using the AI platform Leonardo) are not eligible for copyright protection under Mexican law, reaffirming that copyright is an exclusive human right derived from human creativity.17 This ruling possesses profound third-order implications for the construction of the Legal Knowledge Graph itself. Because the vast networks of metadata, hierarchical segmentations, and structural edges generated by the system's AI algorithms cannot be legally siloed under proprietary copyright frameworks in Mexico, leveraging universally permissive open-source licenses aligns perfectly with the national legal reality. It legally inoculates the project and ensures the graph remains in the public domain, fostering widespread institutional adoption.

To interact with this evolving data, the SCJN has already begun deploying advanced Application Programming Interfaces (APIs) and AI tools, such as the "Sor Juana AI" platform, which allows citizens to query public drafts of rulings currently being voted on by the ministers.19 The proposed open-source graph architecture must be capable of integrating with these emerging APIs, consuming their output, and mapping the findings into a cohesive, centralized topological structure.

## **Ontological Engineering and Bitemporal Data Modeling**

Before selecting database infrastructure, the raw unstructured data must be mapped to a formal semantic ontology. Flat-text retrieval systems and standard Retrieval-Augmented Generation (RAG) architectures are fundamentally blind to the hierarchical, diachronic, and causal structure of the law.20 When standard vector databases perform semantic similarity searches, they often retrieve anachronistic and unreliable answers because they fail to understand that an article from a 2010 law may have been partially derogated by a 2022 supreme court ruling.21 To interconnect all nodes of information effectively, the underlying schema must define the taxonomy of legal entities, their structural containment, and their temporal validity.

### **Formal Modeling of Legal Concepts**

The architecture requires an ontology that elevates legal concepts from mere metadata tags to first-class ontological entities within the graph.20 Several standard open-source ontologies and conceptual models are available for mapping legal data, each with distinct advantages and focus areas.

| Legal Ontology / Model | Primary Focus and Architecture | Relevance to the Mexican Legal Graph |
| :---- | :---- | :---- |
| **ELI (European Legislation Identifier)** | Standardized HTTP URIs and RDF metadata for legislative documents.23 | Provides excellent high-level document description (jurisdiction, type of act) but lacks deep internal hierarchical granularity.23 |
| **Akoma Ntoso / LegalDocML** | XML-based standard for parliamentary and legislative documents.25 | Industry standard for document markup, though it tends to trap conceptual layers within XML tags rather than exposing them as graph nodes.20 |
| **LKIF-Core** | Legal Knowledge Interchange Format, designed for expressing legal rules and semantics.25 | Useful for rule-based reasoning across different legal systems, though potentially overly abstract for raw text ingestion.27 |
| **ILGS (Isaacus Legal Graph Schema)** | Hierarchical graphitization ontology released under CC BY 4.0.28 | Highly optimized for mapping the deep structural hierarchy of documents (divisions, articles, clauses) and semantic edges.28 |
| **FRBR / LRMoo** | Functional Requirements for Bibliographic Records, distinguishing abstract Works from materialized Expressions.20 | Crucial for tracking the evolution of a law. The Mexican Constitution is the "Work," while the 2024 reformed text is the "Expression".20 |

Adopting a hybrid ontological approach provides the most robust blueprint for mapping the Mexican DOF and SCJN corpora. The system must ground its knowledge graph in a formal model inspired by FRBR/LRMoo, distinguishing abstract legal works from their versioned expressions.20 In this schema, ELI metadata elements define the external properties of the document, while ILGS dictates the internal structural segmentation.

### **The Imperative of Temporal Graphs**

Because the Mexican legal framework is continuously amended, the ontology must support bitemporal modeling.25 A methodology such as Structure-Aware Temporal Graph RAG (SAT-Graph RAG) explicitly models the formal structure and diachronic nature of legal norms.21 In this paradigm, legislative events—such as the passing of a new reform by the *Cámara de Diputados*—are reified as first-class "Action" nodes to make causality explicit and queryable.15 Temporal states are treated as efficient aggregations that reuse the versioned expressions of unchanged components.21 Consequently, when a user queries the graph to understand the regulatory status of an energy contract signed in 2018, the system traverses the temporal edges to reconstruct the precise legal framework active at that specific point in time, ignoring subsequent 2021 reforms that do not apply retroactively.14

## **Distributed Graph Database Infrastructure: Storing the Universe**

To leverage a massive data universe where all nodes are interconnected, traditional relational databases (SQL) and document stores (NoSQL) are architecturally insufficient. Relational joins become computationally prohibitive at scale when traversing deep, multi-hop relationships (e.g., finding all SCJN amparo cases that cite a specific clause of a federal law that was subsequently modified by a presidential decree). Native graph databases utilize index-free adjacency, where connected nodes physically point to each other in memory, reducing complex traversal operations from logarithmic index lookups to constant-time pointer dereferences.

The selection of the graph database must strictly adhere to permissive open-source licensing constraints while providing linear scalability.

### **Licensing Constraints: The Case for Apache 2.0**

While many developers equate "open source" with free software, the specific legal parameters of the license dictate enterprise viability.33

* **GPL (GNU General Public License):** A restrictive, copyleft license that requires any derivative work to also be released under the GPL.4 This is often unacceptable for governmental or enterprise environments that wish to build proprietary applications atop the open-source core.2  
* **MIT License:** A highly permissive license allowing users to modify and distribute code with minimal restrictions, widely favored in the JavaScript ecosystem.3  
* **Apache License 2.0:** A modern permissive license that, crucially, includes explicit patent grants and retaliation clauses against patent trolling.3 In a complex legal ecosystem, the Apache 2.0 license serves as "neutral ground," protecting organizations from predatory intellectual property litigation while permitting closed-source commercialization of derivative works.3

### **Comparative Analysis of Graph Databases**

System architects must evaluate the premier graph databases against these stringent licensing and scalability requirements.

| Database Technology | Primary License | Architecture Type | Scalability & Performance Capacity | Core Strengths and Limitations |
| :---- | :---- | :---- | :---- | :---- |
| **NebulaGraph** | Apache 2.0 | Distributed, Shared-Nothing, Native Graph | Capable of hosting hundreds of billions of vertices and trillions of edges.34 | Extreme horizontal scalability, separation of storage and compute, millisecond latency, native C++ execution.36 |
| **JanusGraph** | Apache 2.0 | Distributed, Pluggable Backend | Scales to hundreds of billions of vertices.38 | Supports pluggable storage backends (Cassandra, HBase), offers ACID transactions.38 High memory consumption during massive data loads.40 |
| **Neo4j (Community)** | GPL v3 (Restrictive) | Single-Server, Native Graph | Excellent for single-node instances, bound by available RAM.40 | Ubiquitous query language (Cypher) and massive community, but strictly excluded due to restrictive GPL licensing limitations.41 |
| **TigerGraph** | Proprietary / Commercial | Distributed, Native Graph | High-performance parallel processing.40 | Exceptional performance, but user friendliness is sacrificed and the enterprise edition is highly expensive. Not open source.42 |
| **Memgraph** | BSL (converts to Apache 2.0) | In-Memory, Native Graph | High-speed real-time analytics, constrained by total RAM available.39 | Millisecond IAM checking, optimized for high-speed dynamic data.39 |

### **The Optimal Choice: NebulaGraph**

For the construction of a national legal knowledge graph, **NebulaGraph** emerges unequivocally as the superior technological foundation. Released under the permissive Apache 2.0 License, NebulaGraph is an open-source, distributed, native graph database explicitly engineered to host massive networks while serving highly concurrent queries with millisecond latency.36

NebulaGraph's architectural superiority is rooted in its decoupled design, which cleanly separates compute and storage operations.43 The architecture comprises three core components: the Meta Service, the Graph Service (Compute), and the Storage Service.43 This separation allows for independent linear scaling.34 If the NLP layer generates an enormous volume of new edges during the initial historical ingestion of the DOF archives, the storage nodes can be scaled horizontally. Conversely, if query volume spikes due to public access during a highly publicized SCJN trial, compute nodes can be scaled effortlessly to accommodate the spiky online traffic patterns.34

Data integrity and reliability are paramount for public legal infrastructure. NebulaGraph's Storage Service utilizes the Raft consensus protocol to automatically replicate data across multiple nodes, ensuring fault tolerance and 99.999% high availability, eliminating single points of failure.34 Furthermore, NebulaGraph utilizes nGQL, an expressive, SQL-like graph query language that supports complex match patterns, making it highly suitable for developers accustomed to traditional relational logic who are transitioning to graph topologies.36

Performance benchmarks consistently validate NebulaGraph's capacity to handle massive datasets. In comparative evaluations using the LDBC SNB benchmark against JanusGraph and Neo4j, NebulaGraph demonstrates superior data import efficiency and lower query execution times, particularly when executing complex two-hop and shared-friends network queries across datasets exceeding 10 million edges.35 While JanusGraph is a capable Apache 2.0 alternative, its reliance on third-party backend storage introduces intermediate latency, resulting in significantly higher memory consumption and multi-day loading times for massive datasets.40 By deploying NebulaGraph, the Mexican legal universe—comprising every constitutional article, statutory amendment, and jurisprudential precedent—can be centralized in a highly performant, fault-tolerant cluster capable of executing deeply nested relational queries in real-time.

## **Information Extraction and Natural Language Processing (NLP)**

The primary barrier to constructing the legal knowledge graph is the highly unstructured nature of the source data. The DOF, SCJN databases, and legislative portals output text primarily in PDF, HTML, or raw text formats.7 To populate NebulaGraph with structured triples (Subject ![][image1] Predicate ![][image1] Object), this raw text must undergo rigorous Information Extraction (IE) powered by advanced Natural Language Processing (NLP).

### **Data Acquisition and Automated Scraping**

The ingestion pipeline necessitates a robust, fault-tolerant scraping framework capable of navigating the heterogeneous digital endpoints of the Mexican government. Utilizing permissive open-source extraction libraries allows system architects to bypass fragile, ad-hoc scraping scripts.

**Juriscraper**, licensed under the BSD 2-Clause license, is a highly robust data gathering library written in Python.46 While originally developed to scrape millions of records from the American court system, its generalized, XPath-based scraping architecture—powered by the highly optimized lxml HTML parser—enables it to be easily adapted for international geographies, including Mexican judicial portals.47 Juriscraper handles metadata extraction and document retrieval without requiring an intermediary database, providing a clean, continuous data stream into the processing pipeline.47 Furthermore, metadata extraction from diverse file types (including legacy PDFs) can be augmented using **Apache Tika**, an Apache 2.0 licensed toolkit capable of parsing over a thousand different file types through a single interface.48

For the critical task of identifying and extracting legal citations from the raw text, **Eyecite** (BSD 2-Clause) provides a high-performance open-source solution.46 While its default configuration recognizes American legal decisions, its underlying regex-based architecture can be customized to identify the unique citation formats of Mexican law, accurately matching string patterns referring to the "Código de Comercio" or specific constitutional articles.15

### **Spanish Legal NLP and Transformer Models**

Once the text is acquired, the core extraction engine must decipher the semantic meaning. To comply with permissive licensing requirements and mitigate data privacy risks associated with sending sensitive legal data to proprietary third-party APIs (such as OpenAI's GPT models), the pipeline must utilize open-source or open-weight NLP models.5

**1\. Foundational NLP Framework: spaCy** **spaCy**, available under the MIT License, represents the industry standard for production-grade NLP in Python.7 It provides highly efficient pipelines for foundational linguistic tasks, including tokenization, part-of-speech (PoS) tagging, morphological analysis, and dependency parsing.7 During the creation of the UPIITA-IPN dataset of Mexican laws, basic NLP techniques akin to those provided by spaCy were instrumental in identifying PoS and named entities within the JSON structures.7

**2\. Transformer Models for Spanish Legal Text**

Traditional regular expressions and baseline Named Entity Recognition (NER) models struggle profoundly with the syntactic complexity, deep nesting, and semantic density of legal language. Transformer-based architectures are required to achieve high accuracy in NER and Relation Extraction.

The ecosystem provides several powerful permissive models:

* **XLM-RoBERTa:** A multilingual version of the RoBERTa architecture trained on the CC100 corpus (2.5TB of data across 100 languages), available under the MIT license.51 It provides a massive foundational understanding of the Spanish language.  
* **DeBERTaV3:** Another highly capable multilingual model (mDeBERTaV3) released under the MIT license, known for exceptional performance on natural language inference tasks.51  
* **Domain-Specific Spanish Models:** The Spanish government's PlanTL-GOB-ES initiative has released several highly optimized, open-source models on HuggingFace, including Legal Language Models and RoBERTa-base-BNE models fine-tuned specifically for Spanish POS and NER tasks.52  
* **Regional Fine-Tuning:** Models such as legner\_law\_money and nlp-dr-ner (fine-tuned on Latin American legal texts, specifically Dominican Republic judicial bulletins) demonstrate the viability of adapting foundational transformers to recognize the specific legal dialects, date formats, and entity structures prevalent in Latin American jurisprudence.53

### **The Paradigm Shift: Hierarchical Graphitization**

Traditional, flat Named Entity Recognition is insufficient for building a true legal hypergraph. Identifying that "Andrés Manuel López Obrador" is a PERSON and that "PEMEX" is an ORGANIZATION is helpful, but the graph must also comprehend structural layout—recognizing that Clause B is a condition of Section 2, which falls under Article 4, Title 1 of the Constitution.

Emerging architectures in the open-source machine learning space, characterized by models like **Kanon 2 Enricher**, demonstrate a revolutionary concept known as hierarchical graphitization.28 Unlike auto-regressive generative Large Language Models (LLMs) that output text token-by-token (a process that inherently introduces the risk of generative hallucinations), a hierarchical graphitization model natively outputs knowledge graphs.29

Kanon 2 Enricher, for example, is engineered with a graph-first architecture utilizing 58 distinct task heads jointly optimized with 70 different loss terms.28 By treating document structuring as a joint structured prediction problem rather than an autoregressive generation problem, the model performs direct token-level classification across the entire document in a single shot.28 This makes it architecturally incapable of hallucinating text outside the source document.55 It simultaneously performs hierarchical segmentation (breaking documents into divisions, articles, sections), entity extraction, disambiguation, classification, and hierarchical linking.31

To replicate this capability for the Mexican system utilizing entirely open-source technology, system architects can synthesize a pipeline by taking a highly permissive open-weights LLM and fine-tuning it to perform Information Extraction (IE) based strictly on the ILGS ontology.49 This model parses the raw text of the Diario Oficial de la Federación, identifies the overarching legal act, segments it into individual articles (generating structural containment edges), extracts referenced entities, and definitively resolves cross-references to other laws. For instance, if a newly promulgated decree modifies the "Ley General de Sociedades Mercantiles," the NLP pipeline automatically generates a MODIFIES edge connecting the new decree node directly to the existing statutory node, immediately updating the topological reality of the database.15

## **High-Performance Graph Visualization: Rendering the Topological Network**

A knowledge graph comprising millions of interconnected legal nodes provides no actionable utility if it cannot be fluidly explored, visualized, and interrogated by human analysts, legal scholars, or automated agents. The frontend visualization framework must process complex network topologies and render them without latency in a standard web browser.

Rendering highly dense graph data in JavaScript typically relies on three underlying technologies: SVG, Canvas, or WebGL.58

* **SVG (Scalable Vector Graphics):** Treats each node and edge as a distinct DOM element in the browser tree. This offers ultimate styling flexibility and easy interactivity, but suffers catastrophic performance degradation when exceeding 2,000 nodes due to DOM bloat.58  
* **Canvas:** Uses immediate-mode rendering for direct pixel manipulation. While faster than SVG, performance degrades rapidly when pushing past 5,000 to 10,000 nodes.58  
* **WebGL:** Leverages the local machine's Graphics Processing Unit (GPU) for hardware-accelerated rendering. It is the only web technology capable of fluidly animating and interacting with massive graphs containing 50,000 to over 100,000 nodes while maintaining 60 frames per second.58

Given that visualizing even a minor subset of the Mexican legal framework (such as mapping all historical amparo rulings related to a single constitutional article) will instantly require rendering tens of thousands of connections, WebGL support is an absolute architectural prerequisite.

### **Comparative Analysis of Open-Source Graph Visualization Libraries**

Selecting the correct visualization library requires balancing raw rendering performance with layout algorithm support and permissive licensing.

| Visualization Library | License | Primary Rendering Engine | Max Node Scalability | Core Strengths and Architectural Focus |
| :---- | :---- | :---- | :---- | :---- |
| **Sigma.js** | MIT | WebGL | 100,000+ | Unmatched performance for massive datasets. Separates data modeling (Graphology) from rendering. Highly optimized for pure WebGL output.61 |
| **G6 (AntV)** | MIT | Canvas / WebGL | \~50,000 | Comprehensive suite of layout algorithms. Exceptional for hierarchical tree layouts and complex relational data. Strong animation capabilities.59 |
| **Cytoscape.js** | MIT | Canvas (WebGL extensions) | \~100,000 | Highly scalable, feature-rich, deeply integrated with bioinformatics and complex network theory. Excellent layout algorithms.60 |
| **Apache ECharts** | Apache 2.0 | Canvas / WebGL | 50,000+ | Broad data visualization toolkit. Excels in standard charts (bar, line), but less specialized for pure topological graph traversal and network clustering.58 |

(Note: Commercial libraries such as KeyLines, yFiles, and Ogma offer exceptional performance but are excluded due to the strict open-source licensing mandate.38)

### **The Optimal Visualization Stack: Sigma.js and Graphology**

For rendering the holistic, macro-level universe of the Mexican legal framework, **Sigma.js** (MIT License) is the definitive optimal choice.3 Designed specifically for high-performance network graph visualization, Sigma.js relies exclusively on a highly optimized WebGL rendering pipeline, completely bypassing the bottlenecks of the browser DOM.61

The defining architectural advantage of Sigma.js is its symbiotic, decoupled integration with **Graphology**, a multipurpose graph manipulation and data modeling library.59 In this paradigm, rendering and computation are strictly separated:

* **Graphology (Data & Mathematics):** Handles the underlying data model, storing the nodes and edges locally in the browser's memory. Crucially, it executes computationally heavy layout algorithms, such as the *ForceAtlas2* layout (a continuous, force-directed algorithm that clusters highly connected nodes together and pushes disconnected nodes apart) and community detection algorithms.61 Algorithms like the Louvain method have previously been successfully applied to Mexican knowledge graphs to study spatial relationships and community clusters.67  
* **Sigma.js (Rendering):** Reads the complex mathematical state from the Graphology model and pushes it directly to the GPU via WebGL, allowing for seamless panning, zooming, and interactive highlighting of massive graph structures.58

While WebGL makes deep custom styling slightly more complex than SVG, Sigma.js supports node customization, enabling distinct visual styling for different classes of legal entities.61 Within the Mexican legal graph, a SCJN jurisprudential ruling could be rendered as a prominent red node, a fundamental constitutional article as a massive gold hub, and standard federal laws as interconnected blue nodes. As the user hovers their cursor over a specific SCJN node, Sigma.js instantly highlights its immediate neighborhood, illuminating the specific federal laws, state regulations, and constitutional articles that the ruling cites and influences.

For applications requiring highly structured, hierarchical tree visualizations (for example, exploring the internal nested tree of a single piece of legislation, from *Libro* to *Título* to *Capítulo* to *Artículo*), **AntV G6** (MIT License) serves as a powerful complementary tool.68 G6 focuses extensively on relational data and provides flexible, extendable interfaces for dynamic relationship analysis, making it ideal for micro-level legal exploration and nested hierarchy views, while Sigma.js handles the macro-level universe map.65

## **Synthesized System Architecture and Data Workflow**

Synthesizing these permissive open-source components results in a highly cohesive, horizontally scalable system architecture for the Mexican Legal Knowledge Graph. The data flows sequentially from the government portals to the end-user's browser through the following architectural layers:

1. **Data Acquisition Layer:**  
   * **Juriscraper** and customized Python extraction scripts continuously monitor and parse the HTML and XML outputs of the Diario Oficial de la Federación (DOF), the Supreme Court (SCJN) jurisprudence systems, and the "Orden Juridico Nacional" portals.7  
2. **Semantic Structuring & NLP Layer:**  
   * Raw text is streamed into a processing pipeline orchestrated by **spaCy** and open-weights Transformer models (such as **XLM-RoBERTa** or fine-tuned **PlanTL-GOB-ES** variants).50  
   * The text is hierarchically segmented using the logic defined by the **ILGS** (CC BY 4.0) ontology, distinguishing abstract works from specific temporal expressions.21  
   * Entities (e.g., Judges, Ministers, Corporations, Government Bodies like INAI or Pemex) are extracted.14  
   * **Eyecite** derivatives resolve complex cross-references to other laws, programmatically generating structural CITES, MODIFIES, and DEROGATES edges.46  
3. **Graph Storage & Compute Layer:**  
   * The structured triples (nodes, edges, and temporal properties) are bulk-loaded into an Apache 2.0 **NebulaGraph** cluster.34  
   * The decoupled Storage Service safely replicates the data via the Raft consensus protocol. The Compute Service exposes a high-performance endpoint, allowing analysts to execute complex **nGQL** queries.36  
4. **Application Programming Interface (API):**  
   * A middleware backend service translates REST or GraphQL requests from the client into optimized nGQL queries, retrieving precise subgraphs or specific traversals (e.g., a query requesting "all active environmental laws enacted between 2020 and 2025 that reference Article 27 of the Constitution").15  
5. **Visualization & Interaction Layer:**  
   * The frontend client receives the localized subgraph data. **Graphology** calculates the network layout (e.g., running ForceAtlas2 to cluster related environmental decrees), establishing the visual topology of the legal interconnections.61  
   * **Sigma.js** leverages the client's GPU via WebGL to render the graph fluidly in the browser, allowing the user to visually navigate the complex web of Mexican law in real-time.61

## **Systemic Implications and Strategic Outlook**

The successful architectural implementation of a national legal knowledge graph utilizing this open-source stack yields profound second and third-order implications for the Mexican judicial ecosystem, legal tech industry, and civic engagement.

### **From Semantic Search to Deterministic Topological Analysis**

Traditional legal research platforms—including the SCJN's existing digital access systems and conventional AI chatbots—rely primarily on semantic vector search or basic keyword indexing (TF-IDF).6 While vector databases excel at finding semantically similar text, they fundamentally fail to capture multi-hop relational logic and the cascading impact of statutory modifications.22 A purely semantic search might successfully return an article from the *Código de Comercio*, but it remains entirely blind to the fact that an obscure regulatory decree passed two years later partially derogated that specific clause.

By modeling the data definitively in NebulaGraph, the legal framework is transformed from a static library into a dynamic, explorable topology. Advanced Retrieval-Augmented Generation (RAG) systems can utilize this graph to execute GraphRAG operations.22 Instead of simply feeding a Large Language Model isolated paragraphs, GraphRAG queries the NebulaGraph database to extract an exact, deterministic subgraph—comprising the law, its historical amendments, the precise temporal state of the statute, and the latest SCJN interpretations. It then feeds this deeply interconnected context to the AI model. This structured approach eliminates the generative hallucinations caused by temporal blindness, which is a critical necessity in the legal domain, where anachronistic or hallucinatory answers carry severe professional liability.5

### **Democratization of Justice and Institutional Transparency**

The Mexican legal framework is notoriously complex and difficult for laypersons to navigate. Traditional models of legal production, as noted by industry analyses of the Mexican market, treat land, capital, and labor as restrictive factors, creating prohibitively high financial barriers to accessing legal intelligence.5 The 2025 judicial elections underscored a massive public demand for a more efficient, austere, and transparent justice system, yet low voter turnout simultaneously highlighted a persistent disconnect in civic engagement.16

An open-source legal knowledge graph fundamentally democratizes access to justice. By architecting the system utilizing exclusively open-source components (MIT/Apache 2.0), the public sector, academic institutions, and civic-tech organizations can deploy this massive infrastructure without being subjected to prohibitive commercial licensing fees or vendor lock-in.3 Visualizing the law through highly performant libraries like Sigma.js translates esoteric legal jargon into an intuitive, visual map. A citizen, journalist, or public policy advocate can visually trace the flow of legal influence—seeing exactly how a specific corporate entity is affected by a web of energy sector reforms and SCJN amparo rulings.14

### **Predictive Justice and Systemic Risk Mitigation**

Once the entire corpus of SCJN rulings and DOF publications is mapped as a topological network, advanced graph analytics can be deployed directly within the NebulaGraph engine.34 Algorithms evaluating node centrality (such as PageRank or Betweenness Centrality) can mathematically identify the most "load-bearing" articles in the Mexican Constitution—those critical nodes upon which the highest volume of lower-court rulings and federal statutes rely.

Furthermore, analyzing the graph topologically can reveal systemic contradictions, deep-rooted legal vulnerabilities, or open source package vulnerabilities mirroring software supply chains.70 If the graph visualization reveals a dense, tangled cluster of contradictory jurisprudence in a specific sector (for example, energy law regulations involving private providers challenging administrative decrees), it mathematically flags an area of severe legal instability that requires immediate legislative clarification.14

Ultimately, orchestrating these powerful open-source technologies—the ILGS ontology, NebulaGraph, advanced Spanish Transformer models, and Sigma.js—enables the Mexican legal system to transcend the limitations of static text documents. It transforms the law into a dynamic, queryable, and visually explorable mathematical reality, representing a critical architectural leap toward transparent, deterministic, and universally accessible national legal intelligence.

#### **Works cited**

1. Top 12 Open Source AI Platforms to Add to Your Tech Stack | DigitalOcean, accessed March 7, 2026, [https://www.digitalocean.com/resources/articles/open-source-ai-platforms](https://www.digitalocean.com/resources/articles/open-source-ai-platforms)  
2. What Lawyers Need to Know About Open Source Licensing and Management \- Black Duck, accessed March 7, 2026, [https://www.blackduck.com/content/dam/black-duck/en-us/whitepapers/wp-lawyers-open-source-licensing-management.pdf](https://www.blackduck.com/content/dam/black-duck/en-us/whitepapers/wp-lawyers-open-source-licensing-management.pdf)  
3. Favorite Permissive License: Apache 2.0 or MIT? : r/opensource \- Reddit, accessed March 7, 2026, [https://www.reddit.com/r/opensource/comments/1q80yea/favorite\_permissive\_license\_apache\_20\_or\_mit/](https://www.reddit.com/r/opensource/comments/1q80yea/favorite_permissive_license_apache_20_or_mit/)  
4. The most popular licenses for each language in 2023 \- Open Source Initiative, accessed March 7, 2026, [https://opensource.org/blog/the-most-popular-licenses-for-each-language-2023](https://opensource.org/blog/the-most-popular-licenses-for-each-language-2023)  
5. The World's First Claude Code-Native Law Firm Is Not in Silicon Valley. It's in Mexico., accessed March 7, 2026, [https://www.legalparadox.com/insights/claude-code-native-law-firm-mexico](https://www.legalparadox.com/insights/claude-code-native-law-firm-mexico)  
6. Mexico's Supreme Court of Justice of the Nation provides the public with digital access to the court's historical documents with the help of Azure | Microsoft Customer Stories, accessed March 7, 2026, [https://www.microsoft.com/en/customers/story/1656442281606099981-supreme-court-of-justice-of-the-nation-national-government-microsoft-azure](https://www.microsoft.com/en/customers/story/1656442281606099981-supreme-court-of-justice-of-the-nation-national-government-microsoft-azure)  
7. Unified, Labeled, and Semi-Structured Database of Pre-Processed Mexican Laws \- ORBilu, accessed March 7, 2026, [https://orbilu.uni.lu/bitstream/10993/51615/1/data-07-00091-v3.pdf](https://orbilu.uni.lu/bitstream/10993/51615/1/data-07-00091-v3.pdf)  
8. antoniotorres/dof: Diario Oficial de la Fedaración \- GitHub, accessed March 7, 2026, [https://github.com/antoniotorres/dof](https://github.com/antoniotorres/dof)  
9. Esta funcion contacta al web server del Diario Oficial de la Federación y trae la paridad del peso frente al dólar de acuerdo al día. \- gists · GitHub, accessed March 7, 2026, [https://gist.github.com/673630](https://gist.github.com/673630)  
10. openlegaldata/awesome-legal-data: A collection of datasets and other resources for legal text processing. \- GitHub, accessed March 7, 2026, [https://github.com/openlegaldata/awesome-legal-data](https://github.com/openlegaldata/awesome-legal-data)  
11. 0JCRG0/InteliJuris: A cutting-edge legal research platform, enhancing Mexico's SCJN jurisprudence exploration through Generative AI and Retrieval-Augmented Generation (RAG) for a more intuitive and context-aware search process. \- GitHub, accessed March 7, 2026, [https://github.com/0JCRG0/InteliJuris](https://github.com/0JCRG0/InteliJuris)  
12. Unified, Labeled, and Semi-Structured Database of Pre-Processed Mexican Laws, accessed March 7, 2026, [https://ideas.repec.org/a/gam/jdataj/v7y2022i7p91-d856500.html](https://ideas.repec.org/a/gam/jdataj/v7y2022i7p91-d856500.html)  
13. Unified, Labeled, and Semi-Structured Database of Pre-Processed Mexican Laws \- MDPI, accessed March 7, 2026, [https://www.mdpi.com/2306-5729/7/7/91](https://www.mdpi.com/2306-5729/7/7/91)  
14. Reforms in the energy legal framework in Mexico and challenge mechanisms | DLA Piper, accessed March 7, 2026, [https://www.dlapiper.com/en/insights/publications/2021/06/reforms-in-the-energy-legal-framework-in-mexico-and-challenge-mechanisms](https://www.dlapiper.com/en/insights/publications/2021/06/reforms-in-the-energy-legal-framework-in-mexico-and-challenge-mechanisms)  
15. Ansvar-Systems/mexican-law-mcp: Mexican federal law database covering data protection (LFPDPPP), fintech, cybercrime, commercial law, and consumer protection with Spanish full-text search \- GitHub, accessed March 7, 2026, [https://github.com/Ansvar-Systems/mexican-law-mcp](https://github.com/Ansvar-Systems/mexican-law-mcp)  
16. Mexico's judicial elections 2025: A step toward a more accessible justice system?, accessed March 7, 2026, [https://www.thomsonreuters.com/en-us/posts/government/mexico-judicial-elections-2025/](https://www.thomsonreuters.com/en-us/posts/government/mexico-judicial-elections-2025/)  
17. Mexico's Supreme Court Rules That Works Created by Artificial Intelligence Cannot Be Registered as Intellectual Property \- BASHAM, accessed March 7, 2026, [https://basham.com.mx/en/mexicos-supreme-court-rules-that-works-created-by-artificial-intelligence-cannot-be-registered-as-intellectual-property/](https://basham.com.mx/en/mexicos-supreme-court-rules-that-works-created-by-artificial-intelligence-cannot-be-registered-as-intellectual-property/)  
18. Client Alert – Draft Ruling from Mexico's Supreme Court (SCJN) Declares AI‑Generated Works Ineligible for Copyright Protection \- FisherBroyles, accessed March 7, 2026, [https://fisherbroyles.com/news/client-alert-draft-ruling-from-mexicos-supreme-court-scjn-declares-ai%E2%80%91generated-works-ineligible-for-copyright-protection/](https://fisherbroyles.com/news/client-alert-draft-ruling-from-mexicos-supreme-court-scjn-declares-ai%E2%80%91generated-works-ineligible-for-copyright-protection/)  
19. Sor Juana: an AI that Brings Supreme Court Rulings Closer to Mexican Citizens \- TecScience, accessed March 7, 2026, [https://tecscience.tec.mx/en/education-and-humanism/sor-juana-ai/](https://tecscience.tec.mx/en/education-and-humanism/sor-juana-ai/)  
20. An Ontology-Driven Graph RAG for Legal Norms: A Structural, Temporal, and Deterministic Approach \- arXiv, accessed March 7, 2026, [https://arxiv.org/html/2505.00039v5](https://arxiv.org/html/2505.00039v5)  
21. \[2505.00039\] An Ontology-Driven Graph RAG for Legal Norms: A Structural, Temporal, and Deterministic Approach \- arXiv, accessed March 7, 2026, [https://arxiv.org/abs/2505.00039](https://arxiv.org/abs/2505.00039)  
22. From Legal Documents to Knowledge Graphs \- Graph Database & Analytics \- Neo4j, accessed March 7, 2026, [https://neo4j.com/blog/developer/from-legal-documents-to-knowledge-graphs/](https://neo4j.com/blog/developer/from-legal-documents-to-knowledge-graphs/)  
23. Spanish Legislation as Linked Data \- CEUR-WS.org, accessed March 7, 2026, [https://ceur-ws.org/Vol-2309/12.pdf](https://ceur-ws.org/Vol-2309/12.pdf)  
24. Legal Knowledge Graph Ontology \- Lynx, accessed March 7, 2026, [https://www.lynx-project.eu/doc/lkg/](https://www.lynx-project.eu/doc/lkg/)  
25. legalis\_lod \- Rust \- Docs.rs, accessed March 7, 2026, [https://docs.rs/legalis-lod](https://docs.rs/legalis-lod)  
26. A list of selected resources, methods, and tools dedicated to legal data schemes and ontologies. \- GitHub, accessed March 7, 2026, [https://github.com/Liquid-Legal-Institute/Legal-Ontologies](https://github.com/Liquid-Legal-Institute/Legal-Ontologies)  
27. Knowledge Graphs for Analyzing and Searching Legal Data \- penni, accessed March 7, 2026, [https://penni.wu.ac.at/supervision/Erwin%20Filtz%20Thesis%202021.pdf](https://penni.wu.ac.at/supervision/Erwin%20Filtz%20Thesis%202021.pdf)  
28. We invented a new ML architecture to one-shot legal knowledge graph creation \- Reddit, accessed March 7, 2026, [https://www.reddit.com/r/deeplearning/comments/1rmbbf3/we\_invented\_a\_new\_ml\_architecture\_to\_oneshot/](https://www.reddit.com/r/deeplearning/comments/1rmbbf3/we_invented_a_new_ml_architecture_to_oneshot/)  
29. Isaacus announces Kanon 2 Enricher: a new AI architecture for extracting knowledge graphs : r/singularity \- Reddit, accessed March 7, 2026, [https://www.reddit.com/r/singularity/comments/1rjjcuy/isaacus\_announces\_kanon\_2\_enricher\_a\_new\_ai/](https://www.reddit.com/r/singularity/comments/1rjjcuy/isaacus_announces_kanon_2_enricher_a_new_ai/)  
30. Introducing Kanon 2 Enricher \- Isaacus, accessed March 7, 2026, [https://isaacus.com/blog/kanon-2-enricher](https://isaacus.com/blog/kanon-2-enricher)  
31. Enrichment \- Isaacus Docs, accessed March 7, 2026, [https://docs.isaacus.com/capabilities/enrichment](https://docs.isaacus.com/capabilities/enrichment)  
32. A Foundational Schema.org Mapping for a Legal Knowledge Graph: Representing Brazilian Legal Norms as FRBR Works \- arXiv, accessed March 7, 2026, [https://arxiv.org/html/2508.00827v2](https://arxiv.org/html/2508.00827v2)  
33. Open Source Licenses: Types and Comparison \- Snyk, accessed March 7, 2026, [https://snyk.io/articles/open-source-licenses/](https://snyk.io/articles/open-source-licenses/)  
34. NebulaGraph | Unlimited Scalability and High Performance Graph Database, accessed March 7, 2026, [https://nebula-graph.io/](https://nebula-graph.io/)  
35. Graph Database Performance Comparison: Neo4j vs NebulaGraph vs JanusGraph, accessed March 7, 2026, [https://nebula-graph.io/posts/performance-comparison-neo4j-janusgraph-nebula-graph](https://nebula-graph.io/posts/performance-comparison-neo4j-janusgraph-nebula-graph)  
36. What is NebulaGraph, accessed March 7, 2026, [https://docs.nebula-graph.io/3.8.0/1.introduction/1.what-is-nebula-graph/](https://docs.nebula-graph.io/3.8.0/1.introduction/1.what-is-nebula-graph/)  
37. Amazon Neptune vs NebulaGraph, accessed March 7, 2026, [https://nebula-graph.io/posts/amazon-neptune-vs-nebulagraph](https://nebula-graph.io/posts/amazon-neptune-vs-nebulagraph)  
38. How To Choose A Graph Database: We Compare 8 Favorites \- Cambridge Intelligence, accessed March 7, 2026, [https://cambridge-intelligence.com/choosing-graph-database/](https://cambridge-intelligence.com/choosing-graph-database/)  
39. DB-Engines Ranking: Top Graph Databases You Should Use \- Memgraph, accessed March 7, 2026, [https://memgraph.com/blog/db-engines-ranking-top-graph-databases](https://memgraph.com/blog/db-engines-ranking-top-graph-databases)  
40. Experimental Evaluation of Graph Databases: JanusGraph, Nebula Graph, Neo4j, and TigerGraph \- MDPI, accessed March 7, 2026, [https://www.mdpi.com/2076-3417/13/9/5770](https://www.mdpi.com/2076-3417/13/9/5770)  
41. Feature matrix comparing community and enterprise versions? \- Newbie Questions, accessed March 7, 2026, [https://community.neo4j.com/t/feature-matrix-comparing-community-and-enterprise-versions/62252](https://community.neo4j.com/t/feature-matrix-comparing-community-and-enterprise-versions/62252)  
42. Nebula Graph: A distributed, scalable, lighting-fast graph database : r/programming \- Reddit, accessed March 7, 2026, [https://www.reddit.com/r/programming/comments/dag2oo/nebula\_graph\_a\_distributed\_scalable\_lightingfast/](https://www.reddit.com/r/programming/comments/dag2oo/nebula_graph_a_distributed_scalable_lightingfast/)  
43. NebulaGraph Database Manual, accessed March 7, 2026, [https://docs.nebula-graph.io/](https://docs.nebula-graph.io/)  
44. Top 10 open source databases: Detailed feature comparison \- Instaclustr, accessed March 7, 2026, [https://www.instaclustr.com/education/managed-database/top-10-open-source-databases-detailed-feature-comparison/](https://www.instaclustr.com/education/managed-database/top-10-open-source-databases-detailed-feature-comparison/)  
45. Technical Preview of NebulaGraph Enterprise Latest Version \- Medium, accessed March 7, 2026, [https://medium.com/@nebulagraph/technical-preview-of-nebulagraph-enterprise-v5-0-e9db0d520832](https://medium.com/@nebulagraph/technical-preview-of-nebulagraph-enterprise-v5-0-e9db0d520832)  
46. Open Source Tools | Free Law Project | Making the legal ecosystem more equitable and competitive., accessed March 7, 2026, [https://free.law/open-source-tools/](https://free.law/open-source-tools/)  
47. freelawproject/juriscraper: An API to scrape American court websites for metadata. \- GitHub, accessed March 7, 2026, [https://github.com/freelawproject/juriscraper](https://github.com/freelawproject/juriscraper)  
48. NLP Frameworks — Free and Open Machine Learning \- NoComplexity.com, accessed March 7, 2026, [https://nocomplexity.com/documents/fossml/nlpframeworks.html](https://nocomplexity.com/documents/fossml/nlpframeworks.html)  
49. How to use open source or open weights LLMs & other models and adapt them with fine tuning & RAG | by Tony Mathew | Medium, accessed March 7, 2026, [https://medium.com/@tonymathew/how-to-use-open-source-or-open-weights-llms-other-models-and-adapt-them-with-fine-tuning-rag-a64e66384fca](https://medium.com/@tonymathew/how-to-use-open-source-or-open-weights-llms-other-models-and-adapt-them-with-fine-tuning-rag-a64e66384fca)  
50. spaCy · Industrial-strength Natural Language Processing in Python, accessed March 7, 2026, [https://spacy.io/](https://spacy.io/)  
51. A comparative analysis of Spanish Clinical encoder-based models on NER and classification tasks \- PMC, accessed March 7, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC11339503/](https://pmc.ncbi.nlm.nih.gov/articles/PMC11339503/)  
52. PlanTL-GOB-ES/lm-spanish: Official source for spanish Language Models and resources made @ BSC-TEMU within the "Plan de las Tecnologías del Lenguaje" (Plan-TL). \- GitHub, accessed March 7, 2026, [https://github.com/PlanTL-GOB-ES/lm-spanish](https://github.com/PlanTL-GOB-ES/lm-spanish)  
53. agomez302/nlp-dr-ner \- Hugging Face, accessed March 7, 2026, [https://huggingface.co/agomez302/nlp-dr-ner](https://huggingface.co/agomez302/nlp-dr-ner)  
54. Spanish NER for Laws and Money | legner\_law\_money | Legal NLP 1.0.0, accessed March 7, 2026, [https://nlp.johnsnowlabs.com/2022/09/28/legner\_law\_money\_es.html](https://nlp.johnsnowlabs.com/2022/09/28/legner_law_money_es.html)  
55. Introducing Kanon 2 Enricher \-the world's first hierarchical graphitization model \- Reddit, accessed March 7, 2026, [https://www.reddit.com/r/KnowledgeGraph/comments/1rjjiaj/introducing\_kanon\_2\_enricher\_the\_worlds\_first/](https://www.reddit.com/r/KnowledgeGraph/comments/1rjjiaj/introducing_kanon_2_enricher_the_worlds_first/)  
56. Show HN: Kanon 2 Enricher – the first hierarchical graphitization model | Hacker News, accessed March 7, 2026, [https://news.ycombinator.com/item?id=47229931](https://news.ycombinator.com/item?id=47229931)  
57. LLM-assisted Construction of the United States Legislative Graph \- VLDB Endowment, accessed March 7, 2026, [https://www.vldb.org/2025/Workshops/VLDB-Workshops-2025/LLM+Graph/LLMGraph-2.pdf](https://www.vldb.org/2025/Workshops/VLDB-Workshops-2025/LLM+Graph/LLMGraph-2.pdf)  
58. 15 Top JavaScript Data Visualization Libraries \- Monterail, accessed March 7, 2026, [https://www.monterail.com/blog/javascript-libraries-data-visualization](https://www.monterail.com/blog/javascript-libraries-data-visualization)  
59. A Comparison of Javascript Graph / Network Visualisation Libraries \- Cylynx, accessed March 7, 2026, [https://www.cylynx.io/blog/a-comparison-of-javascript-graph-network-visualisation-libraries/](https://www.cylynx.io/blog/a-comparison-of-javascript-graph-network-visualisation-libraries/)  
60. Graph visualization efficiency of popular web-based libraries \- PMC \- NIH, accessed March 7, 2026, [https://pmc.ncbi.nlm.nih.gov/articles/PMC12061801/](https://pmc.ncbi.nlm.nih.gov/articles/PMC12061801/)  
61. Sigma.js, accessed March 7, 2026, [https://www.sigmajs.org/](https://www.sigmajs.org/)  
62. Frameworks for working with graph visualizations, which one do you prefer? \- Reddit, accessed March 7, 2026, [https://www.reddit.com/r/reactjs/comments/1f9lis9/frameworks\_for\_working\_with\_graph\_visualizations/](https://www.reddit.com/r/reactjs/comments/1f9lis9/frameworks_for_working_with_graph_visualizations/)  
63. Top 10 JavaScript Libraries for Knowledge Graph Visualization \- Focal, accessed March 7, 2026, [https://www.getfocal.co/post/top-10-javascript-libraries-for-knowledge-graph-visualization](https://www.getfocal.co/post/top-10-javascript-libraries-for-knowledge-graph-visualization)  
64. The Best Libraries and Methods to Render Large Force-Directed Graphs on the Web, accessed March 7, 2026, [https://weber-stephen.medium.com/the-best-libraries-and-methods-to-render-large-network-graphs-on-the-web-d122ece2f4dc](https://weber-stephen.medium.com/the-best-libraries-and-methods-to-render-large-network-graphs-on-the-web-d122ece2f4dc)  
65. AntV \- G6 Graph Visualization Framework in JavaScript, accessed March 7, 2026, [https://g6.antv.antgroup.com/en/](https://g6.antv.antgroup.com/en/)  
66. antvis/G6: A Graph Visualization Framework in JavaScript. \- GitHub, accessed March 7, 2026, [https://github.com/antvis/G6](https://github.com/antvis/G6)  
67. Knowledge graph representation of open-source homicide information \- University of Twente, accessed March 7, 2026, [https://www.utwente.nl/en/eemcs/vmbo2025/papers/vmbo-2025-paper-7.pdf](https://www.utwente.nl/en/eemcs/vmbo2025/papers/vmbo-2025-paper-7.pdf)  
68. G6, a Graph Vis Framework \- DEV Community, accessed March 7, 2026, [https://dev.to/antv36700460/g6-a-graph-vis-framework-4cda](https://dev.to/antv36700460/g6-a-graph-vis-framework-4cda)  
69. Lessons from open source in the Mexican government \- LWN.net, accessed March 7, 2026, [https://lwn.net/Articles/1013776/](https://lwn.net/Articles/1013776/)  
70. Use knowledge graphs to discover open source package vulnerabilities | Red Hat Developer, accessed March 7, 2026, [https://developers.redhat.com/blog/2021/05/10/use-knowledge-graphs-to-discover-open-source-package-vulnerabilities](https://developers.redhat.com/blog/2021/05/10/use-knowledge-graphs-to-discover-open-source-package-vulnerabilities)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABMAAAAXCAYAAADpwXTaAAABRElEQVR4Xo1TO05EMQyMJQrq7XiihFPsdRANFeIA1ByDAm217XYranrOg3ASf8ZOAjuSn+0Zf5K3b0tpIDGBhuwJaKG8GupCv8c9CA2hjlIb5m11Wh8Y1zWyJSObeHVZA8R6X5SVnA6oF1lIXZxB6bRiAXlv9RFeqbLBAyTv8tCtQOofudAzcpNqxKLK83e2+3aquKTX9GM7B3JtSRLt2Z+wxiHjZ78UDkmf5BMTj556tON4Y78xtdVYfeWaYez2wXYUzfDGdjCjciDLyfnRvth+2F7blIpwtemHN+Go3PHzzMpeiQlWLy6Q12zfbLejpKgkCnBKiid+YHvxVLRhssYyOIzw5JOTq0jiQPAX4Maii5ussB/zz765KPfD1FzSambXgs2hRAdYbxySo6G3j9MpuAh1zZMYoP9NK1u/H1+ZNjJ+AQoTFaudNq1ZAAAAAElFTkSuQmCC>