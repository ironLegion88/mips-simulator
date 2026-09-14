# Ontology and Knowledge Graph Explorer: Product Specification

- **Document type:** Normative product requirements and system specification
- **Status:** Draft for implementation
- **Version:** 1.0.0
- **Last updated:** 2026-09-10
- **Product scope:** Standalone ontology and knowledge graph exploration
- **Supported frontend:** Cytoscape detail view with cosmos.gl overview
- **Experimental frontend:** Ontodia compatibility prototype
- **Reasoning target:** Full OWL 2 DL through an external offline reasoner

The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are
normative. A requirement identified with a stable ID is testable unless it is
explicitly marked as a future extension.

## 1. Purpose

This document defines the final intended behavior and architecture of the
standalone Ontology and Knowledge Graph Explorer. The application allows users
to discover, inspect, navigate, query, compare, explain, and visualize ontology
schema and knowledge graph instance data without requiring knowledge of SPARQL,
RDF serialization syntax, or the underlying storage implementation.

The product is the complete explorer vertical slice:

```text
Explorer Frontends
        |
Public GraphQL API
        |
Graph and Ontology Services
        |
Repository and Reasoning Ports
        |
Indexed RDF Store + Offline OWL 2 DL Reasoner
        |
Versioned Ontology Sources and Imports
```

This specification supersedes the application scope in
[OWL Store Migration Specification](owl-store-migration-requirements.md). That
document remains normative for compatible embedded-store migration and
operational requirements until they are replaced here or by an approved ADR.

## 2. Product Definition

The Explorer is a research and ontology-engineering application with two
separate frontend implementations over the same GraphQL contracts:

1. A supported application using Cytoscape.js for bounded semantic detail and
   cosmos.gl for aggregated or sampled GPU overview.
2. A prototype-only application using Ontodia to evaluate ontology-oriented
   diagramming and navigation.

Both applications MUST use the same canonical entity identifiers, semantic
metadata, traversal limits, provenance model, saved-view format, and public
GraphQL API. Neither implementation may access RDF files, the embedded store,
or an internal SPARQL interface directly.

## 3. Goals

### PG-001 Ontology-aware exploration

The application MUST represent OWL/RDF semantics rather than flattening every
statement into an indistinguishable node-edge pair.

### PG-002 Ontology replacement

Operators MUST be able to replace the underlying ontology and instance data
without changing core GraphQL, service, graph-state, or renderer contracts.

### PG-003 Progressive graph navigation

Users MUST be able to explore very large indexed ontologies through bounded,
progressive retrieval, filtering, aggregation, sampling, and drill-down.

### PG-004 Semantic transparency

The application MUST distinguish asserted, imported, materialized, and inferred
facts and MUST expose the active reasoning profile and source build.

### PG-005 Accessible exploration

Every critical graph operation and every visible relationship MUST have a
keyboard-operable, non-canvas representation.

### PG-006 Storage independence

No public client contract may depend on PyOxigraph, GraphDB, RocksDB, SPARQL,
RDFLib, Owlready2, or a particular reasoner.

## 4. Non-Goals

### PNG-001 Search-platform integration

Typesense recipe search, ranked recipe discovery, intent parsing, entity
linking, and the existing Search Interface are outside this application's scope.

### PNG-002 LLM chat

An LLM assistant or natural-language intent system is not required by this
specification. Explanation results MUST be generated from semantic provenance,
not invented natural-language claims.

### PNG-003 Public SPARQL

The application MUST NOT expose an unrestricted public SPARQL endpoint or raw
query editor. "Direct graph querying" means typed GraphQL filters, visual query
composition, paths, comparison, and semantic inspection.

### PNG-004 Browser-side ontology processing

The supported applications MUST NOT parse, index, validate, or reason over
arbitrary OWL/RDF files in the browser.

### PNG-005 Ontology authoring

Editing classes, axioms, restrictions, or instance facts is outside the first
product release. Diagram layout editing and annotations do not imply ontology
mutation.

### PNG-006 Unbounded rendering

Simultaneously rendering every node in a million-entity graph is not a product
requirement and MUST NOT be used as a measure of successful large-ontology
support.

## 5. Users And Primary Workflows

### Personas

- **Researcher:** explores entities, relationships, paths, and graph patterns.
- **Ontology engineer:** inspects classes, axioms, property definitions,
  consistency, and inference explanations.
- **Data curator:** validates labels, annotations, provenance, and unexpected
  relationships.
- **Operator:** installs ontology builds, configures reasoners, promotes stores,
  and rolls back deployments.

### UW-001 Discover an entity

A user MUST be able to search labels, aliases, IRIs, semantic kinds, classes,
and namespaces and select a canonical entity as an exploration starting point.

### UW-002 Explore an instance neighborhood

A user MUST be able to expand incoming, outgoing, or bidirectional relationships
with predicate, provenance, and depth filters.

### UW-003 Explore ontology schema

A user MUST be able to browse classes and properties, inspect hierarchy,
restrictions, domains, ranges, characteristics, and instance counts, and add
selected schema entities to a diagram.

### UW-004 Find a path

A user MUST be able to select two canonical entities and request a bounded path
with direction, predicate, maximum-depth, and visited-node constraints.

### UW-005 Compare entities

A user MUST be able to compare shared and unique types, annotations,
properties, predicates, and neighboring entities using bounded results.

### UW-006 Explain an inference

A user MUST be able to ask why a supported inferred type or relationship exists
and receive a bounded proof trace grounded in source and inferred axioms.

### UW-007 Investigate consistency

An ontology engineer MUST be able to see build-level consistency status,
unsatisfiable classes, validation findings, unsupported constructs, and
reasoner failures.

### UW-008 Save and share work

A user SHOULD be able to save a diagram/session, restore it against a compatible
ontology build, create a shareable deep link, and export data or an image.

## 6. System Architecture

```text
                Operator
                   |
       Versioned ingestion and validation
                   |
      External OWL 2 DL reasoning provider
                   |
      Immutable promoted RDF store build
                   |
            GraphRepository port
                   |
    OntologyService + GraphService + ExplanationService
                   |
            Public GraphQL API
             /             \
Supported Cytoscape/Cosmos  Ontodia prototype
```

### AR-101 Public boundary

All user-facing applications MUST communicate exclusively through the public
GraphQL API and MUST NOT bypass the service layer.

### AR-102 Service ownership

Graph and ontology services MUST own validation, business semantics, budgets,
authorization hooks, error translation, and orchestration.

### AR-103 Repository ownership

The repository adapter MUST own RDF terms, internal SPARQL, indexes, named
graphs, store access, and result mapping.

### AR-104 Reasoning ownership

Reasoner invocation, materialization, consistency checks, and explanation
artifacts MUST be isolated behind a `ReasoningProvider` port.

### AR-105 Renderer independence

Application graph state MUST NOT contain Cytoscape, cosmos.gl, or Ontodia
objects. Renderer adapters MUST consume immutable renderer-neutral models.

### AR-106 Separate frontend builds

The supported Cytoscape/Cosmos implementation and Ontodia prototype MUST be
separately buildable and deployable applications. They SHOULD share packages
for GraphQL clients, semantic models, graph state, design tokens, session
formats, accessibility utilities, and conformance tests.

### AR-107 No request-time global reasoning

API requests MUST NOT trigger ontology classification or global materialization.
Reasoning MUST operate on versioned builds outside the request path.

## 7. Ontology Package And Swapping

Ontology replacement is an authenticated operator workflow. End-user ontology
upload is not required by this specification.

### OP-001 Source manifest

Every ontology installation MUST use a versioned source manifest defining:

- Ontology and instance source files.
- Explicit RDF serialization formats.
- Destination named graphs.
- Approved imports and local artifacts.
- SHA-256 checksums.
- Base IRI and prefix declarations.
- Preferred label, description, image, and identifier predicates.
- Preferred languages and fallback order.
- Searchable classes and semantic kinds.
- Traversable, hidden, and sensitive predicates.
- Display labels, colors, icons, and grouping categories.
- Reasoning provider and configuration.
- Validation shapes and policies.
- Build and visible-graph limits.

### OP-002 Supported serializations

Ingestion MUST support RDF/XML and Turtle. It SHOULD support JSON-LD,
N-Triples, N-Quads, TriG, and OWL/XML through approved parsers. File extensions
MUST NOT substitute for explicit/detected syntax.

### OP-003 Profile-driven behavior

Core backend and frontend code MUST NOT hard-code Wine classes, namespaces,
predicates, colors, labels, or relation filters. These values MUST come from the
active ontology profile or generic RDF/OWL discovery.

### OP-004 Wine as fixture

The W3C Wine ontology MUST remain a conformance fixture and demonstration
dataset. It MUST NOT define the product taxonomy.

### OP-005 Content-addressed builds

Ontology builds MUST be immutable and content-addressed by sources,
configuration, imported artifacts, reasoner identity/version, and semantic
profile.

### OP-006 Atomic promotion

Operators MUST be able to build and verify a candidate store without affecting
the active application, then atomically promote or roll back the active build.

### OP-007 Import resolution

`owl:imports` MUST resolve only to allowlisted, pinned, and preferably vendored
artifacts. The runtime API MUST NOT retrieve ontology imports from the network.

### OP-008 Profile discovery API

The active ontology profile, build ID, prefixes, languages, semantic categories,
display configuration, limits, reasoner status, and supported capabilities MUST
be available through backend-neutral GraphQL metadata.

### OP-009 Compatibility on swap

When an ontology build changes, saved sessions MUST be checked for compatible
entity IRIs, predicates, semantic profiles, and session schema versions. Missing
entities MUST be reported rather than silently replaced.

## 8. Full OWL 2 DL Reasoning

The product target is full OWL 2 DL reasoning through an external maintained
reasoner. The embedded RDF store remains the query runtime; it is not itself the
DL reasoner.

### RS-001 Reasoning provider port

The system MUST define a replaceable `ReasoningProvider` interface supporting
classification, consistency checking, materialization/export, and explanation
when the selected implementation provides it.

### RS-002 Provider selection ADR

Before implementation is considered production-ready, an ADR MUST compare
maintained OWL 2 DL reasoners such as HermiT, Openllet, Konclude, or another
candidate for standards coverage, explanation support, licensing, performance,
deployment isolation, and maintenance.

### RS-003 Offline execution

Full reasoning MUST run as a bounded external build job with CPU, memory,
elapsed-time, disk, process, and output limits.

### RS-004 Consistency gate

The reasoner MUST determine ontology consistency before promotion. Promotion of
an inconsistent ontology MUST be blocked by default. An explicit operator policy
MAY allow a quarantined, read-only build that visibly reports inconsistency.

### RS-005 Classification

The reasoning build MUST capture inferred class hierarchy and individual type
assertions required for ontology navigation and search.

### RS-006 Property inference

The reasoning build MUST capture supported inferred object/data property facts,
including inverse, symmetric, transitive, equivalent, subproperty, and property
chain consequences required by the ontology.

### RS-007 OWL class expressions

The semantic model MUST preserve and expose named and anonymous expressions,
including intersections, unions, complements, enumerations, existential and
universal restrictions, value restrictions, and cardinality restrictions.

### RS-008 Axiom support

Equivalent, disjoint, same-as, different-from, domain, range, property
characteristics, and negative assertions MUST be preserved when present and
represented according to the selected reasoner's supported OWL 2 DL behavior.

### RS-009 Provenance

Every materialized fact MUST record whether it is asserted or inferred, the
reasoner build, and source graph/build. A fact MAY have both asserted and
inferred provenance.

### RS-010 Explanation

For reasoner-supported entailments, the system MUST expose a bounded explanation
artifact containing the conclusion, supporting axioms/facts, proof structure or
justification set, provider identity, and build ID.

### RS-011 Explanation limitations

If the selected reasoner cannot explain a valid entailment, the API MUST return
`EXPLANATION_UNAVAILABLE` with reasoner capability metadata. It MUST NOT invent a
proof.

### RS-012 Unsupported constructs

Parser, profile, datatype, and provider limitations MUST be recorded in build
metadata and displayed in the UI. Unsupported content MUST NOT be silently
discarded.

### RS-013 Determinism evidence

Identical sources and pinned reasoning configuration SHOULD produce equivalent
semantic output and explanation fixtures. Non-deterministic ordering MUST be
normalized in build evidence.

### RS-014 Current profile transition

The existing `rdfs-wine-parity` profile MAY remain as a fast development option,
but builds using it MUST be clearly distinguished from full OWL 2 DL builds.

## 9. Ontology-Aware Domain Model

### SM-001 Semantic resource kinds

The domain model MUST represent at least:

- OWL classes.
- Named individuals.
- Object properties.
- Datatype properties.
- Annotation properties.
- RDF properties with unknown specialization.
- Literals.
- Anonymous class expressions/restrictions.
- Axioms or explanation steps where exposed.

### SM-002 Canonical identity

IRI resources MUST use their full IRI as canonical identity. Blank nodes MUST
use build-scoped stable identifiers and MUST NOT be assumed stable across
ontology builds unless canonicalized.

### SM-003 Multilingual labels

Resources MUST preserve all available labels with language/datatype metadata and
MUST expose a preferred label based on the active language policy.

### SM-004 Typed values

Literal values MUST preserve lexical form, datatype IRI, language tag, and a
safe normalized value where conversion is valid.

### SM-005 Resource metadata

Resource inspection MUST support:

- IRI, compact IRI, namespace, and local name.
- Semantic kinds and asserted/inferred types.
- Labels, descriptions, aliases, images, and annotations.
- Source graphs and provenance.
- Direct and inferred relationships.
- Active ontology build.

### SM-006 Class model

Class inspection MUST support direct/all parents, direct/all children,
equivalent/disjoint classes, instance counts, paginated instances, annotations,
and supported restrictions/class expressions.

### SM-007 Property model

Property inspection MUST support semantic property kind, domain, range,
inverse/equivalent/subproperties, characteristics (functional, inverse
functional, transitive, symmetric, asymmetric, reflexive, irreflexive), labels,
annotations, and usage counts.

### SM-008 Relationship model

Each relationship MUST expose:

- Stable relationship identity within a build.
- Source and target resource IDs.
- Full predicate IRI.
- Preferred predicate label and compact IRI.
- Canonical direction.
- Asserted/inferred provenance.
- Source graph/build.
- Optional explanation handle.

### SM-009 Validation model

Validation and reasoning findings MUST include severity, code, message,
affected resources/axioms, source location when available, provider, build ID,
and remediation metadata where known.

## 10. Public GraphQL API

GraphQL is the only supported application API. Internal SPARQL MAY be used by
repositories but MUST remain private.

### GQ-101 Backend neutrality

No public field, error, or type may expose storage paths, PyOxigraph, RocksDB,
GraphDB, internal SPARQL text, or reasoner process details.

### GQ-102 Compatibility

Existing generic fields (`get_entity`, `search_entities`,
`get_relationships`, and `expand_graph`) SHOULD remain compatible while new
ontology-aware fields are added. Wine-specific fields MAY be deprecated after
generic feature parity and a published migration period.

### GQ-103 Ontology metadata

The API MUST expose active build metadata, ontology summary, prefixes,
languages, semantic categories, supported formats, reasoner capabilities,
validation status, and limits.

### GQ-104 Resource inspection

The API MUST provide a generic resource lookup returning semantic metadata,
typed values, annotations, types, provenance, and capability links.

### GQ-105 Schema browsing

The API MUST expose paginated class and property search/browsing, class
hierarchy, class instances, and property metadata.

### GQ-106 Dynamic predicates

Available relationship predicates and counts MUST come from the active ontology
and repository. The frontend MUST NOT require a hardcoded predicate list.

### GQ-107 Bounded expansion

Expansion MUST support direction, predicate filters, semantic-kind filters,
asserted/inferred filters, maximum depth, node/edge/fan-out limits, and opaque
continuation cursors.

### GQ-108 Expansion preview

Before a high-degree expansion, the API MUST be able to return counts grouped by
predicate, direction, semantic kind, and provenance without returning all
neighbors.

### GQ-109 Path discovery

The API MUST expose bounded shortest-path discovery with direction, predicate,
semantic-kind, maximum-depth, visited-node, timeout, and inferred/asserted
options.

### GQ-110 Path outcomes

Path responses MUST distinguish success, no path, timeout, cancellation,
visited-node budget exhaustion, and unsupported traversal semantics.

### GQ-111 Entity comparison

The API MUST expose bounded comparison for common/unique types, annotations,
predicates, neighbors, and semantic findings.

### GQ-112 Inference explanation

The API MUST expose reasoner-generated explanation artifacts by conclusion or
explanation handle and MUST enforce proof size/depth limits.

### GQ-113 Consistency and validation

The API MUST expose build-level consistency, unsatisfiable classes, unsupported
constructs, validation summaries, and paginated findings.

### GQ-114 Session persistence

Saved-view operations SHOULD persist renderer-neutral layout, selected
resources, expansions, filters, notes, build compatibility, and schema version.

### GQ-115 Stable errors

The API MUST define stable codes including:

- `NOT_FOUND`
- `INVALID_ARGUMENT`
- `INVALID_CURSOR`
- `INVALID_PREDICATE`
- `TRAVERSAL_LIMIT`
- `PATH_BUDGET_EXHAUSTED`
- `QUERY_TOO_COMPLEX`
- `TIMEOUT`
- `CANCELLED`
- `STORE_NOT_READY`
- `ONTOLOGY_INCONSISTENT`
- `REASONER_UNAVAILABLE`
- `EXPLANATION_UNAVAILABLE`
- `UNSUPPORTED_SEMANTIC_CONSTRUCT`
- `FORBIDDEN`
- `BACKEND_UNAVAILABLE`

### GQ-116 Abuse protection

GraphQL depth, field count, alias repetition, operation cost, response size,
resolver timeout, and rate limits MUST be enforced server-side.

## 11. Search And Discovery

### SD-001 Search fields

Search MUST support preferred labels, alternate labels, compact/full IRIs, and
configured annotation properties.

### SD-002 Search filters

Search MUST support semantic kind, class/type, namespace, language, source
graph, asserted/inferred state, and active ontology build filters.

### SD-003 Result metadata

Results MUST include canonical IRI, preferred label, compact IRI, semantic kind,
primary types, matched field/value, source build, and enough context to
disambiguate similar resources.

### SD-004 Pagination

Search MUST be bounded and cursor-paginated. Result limits MUST be applied in the
query/index rather than after loading all matches.

### SD-005 Ontology navigation

The application MUST provide separate discoverable navigation for classes,
properties, and individuals, including counts and filters.

### SD-006 Command palette

The supported application SHOULD offer a keyboard command palette for finding
resources and invoking common graph/schema actions.

## 12. Graph And Semantic Exploration

### GE-001 Three-panel workspace

The supported application SHOULD provide a coordinated explorer/navigation
panel, graph canvas, and semantic inspector, with responsive alternatives on
smaller screens.

### GE-002 Progressive expansion

Users MUST expand bounded neighborhoods deliberately. Automatic expansion of an
entire ontology or high-degree resource is prohibited.

### GE-003 Expansion actions

Contextual actions MUST include applicable combinations of:

- Show incoming relationships.
- Show outgoing relationships.
- Show parents.
- Show children.
- Show instances.
- Show types.
- Show domain/range resources.
- Show equivalent/disjoint resources.
- Show supported restrictions.

### GE-004 Filters

Users MUST be able to filter by predicate, direction, semantic kind,
namespace, provenance, source graph, and depth. They SHOULD be able to hide
literals and annotations.

### GE-005 Expand and collapse

Users MUST be able to undo the latest expansion, collapse a selected expansion,
remove selected nodes safely, reset the view, and fit/focus the canvas.

### GE-006 Multi-hop traversal

The application MUST distinguish repeated one-hop exploration from bounded
multi-hop traversal and MUST display truncation/budget state for both.

### GE-007 Selection synchronization

Canvas, schema tree, search results, inspector, table, path result, and Ontodia
prototype selection MUST use the same canonical selected-resource state.

### GE-008 Whole-visible-graph table

The supported application MUST provide a filterable textual table for every
visible relationship, not only relationships adjacent to the selected node.

### GE-009 Semantic inspector

The inspector MUST display resource metadata, types, annotations, object/data
properties, provenance, semantic characteristics, restrictions, and applicable
actions.

### GE-010 Inference styling

Asserted and inferred facts MUST be distinguishable through text/icon/pattern as
well as color. Styling MUST be accompanied by provenance details.

### GE-011 Why panel

The inspector MUST provide a “Why?” action for explainable inferred facts and
render the reasoner-generated justification as a bounded, navigable proof.

### GE-012 Consistency indicators

The workspace MUST display active build consistency, warnings, unsupported
constructs, and validation status without requiring users to inspect logs.

### GE-013 Comparison mode

Users MUST be able to pin at least two resources and compare shared and unique
semantic features.

### GE-014 Query history and bookmarks

The supported application SHOULD retain a local or server-authorized history of
searches, expansions, paths, and bookmarked resources.

### GE-015 Ontology build diff

Operators and ontology engineers SHOULD be able to compare two ontology builds
for added/removed/changed resources, axioms, labels, and inferred facts.

## 13. Save, Share, And Export

### SE-001 Renderer-neutral session format

Saved sessions MUST contain canonical resources, relationships, positions,
filters, selected items, expansion history, notes, active build, and schema
version without renderer-specific runtime objects.

### SE-002 Save and restore

The supported application SHOULD save and restore sessions. The Ontodia
prototype SHOULD map Ontodia diagrams to the same canonical session envelope
where feasible.

### SE-003 Deep links

Shareable links SHOULD identify the ontology build, selected resource, active
mode, and saved session or bounded query state without embedding sensitive graph
data in the URL.

### SE-004 Data exports

The application SHOULD export the visible/bounded subgraph as JSON, CSV, and
GraphML with provenance and build metadata.

### SE-005 Image exports

The supported detail renderer SHOULD export PNG and SVG where technically
supported. Export MUST disclose that only the visible/bounded subgraph is
included.

## 14. Supported Cytoscape And Cosmos Application

### RC-001 Renderer roles

Cytoscape.js MUST render rich bounded detail neighborhoods. cosmos.gl MUST be
used only for a separately defined aggregate or sampled overview mode.

### RC-002 Detail budget

Until superseded by benchmark evidence, Cytoscape detail view MUST enforce a
hard maximum of 500 visible nodes and 1,000 visible edges.

### RC-003 Overview contract

cosmos.gl MUST consume a server-produced overview model containing bounded
clusters or samples, weights/counts, aggregate edges, provenance summary,
sampling/aggregation method, and drill-down targets. It MUST NOT consume a raw
unbounded expansion.

### RC-004 Overview limits

Every overview request MUST include server-owned node, edge, time, memory, and
response-size budgets and MUST report sampling, aggregation, and truncation.

### RC-005 Drill-down

Selecting an overview cluster or sampled resource MUST transition to a newly
requested bounded Cytoscape detail neighborhood, not silently load all members.

### RC-006 Capability detection

The supported application MUST detect required WebGL capabilities. Unsupported,
disabled, low-power, or failed GPU initialization MUST fall back to aggregate
tables and bounded Cytoscape detail.

### RC-007 Level of detail

Labels, arrows, edge labels, images, animations, and layout complexity MUST be
adapted to visible graph size and zoom. Semantic details MUST remain available
through the inspector/table when visually suppressed.

### RC-008 High-degree resources

The UI MUST show relation counts and require filtering, pagination, grouping, or
aggregation before expanding a supernode beyond the current visible budget.

### RC-009 Layout

Large overview layouts SHOULD be precomputed, incrementally maintained, or GPU
accelerated. The UI MUST remain cancellable and MUST NOT block the main thread
for an unbounded force layout.

### RC-010 Current benchmark basis

The architecture MUST retain the evidence in
[Graph Renderer Benchmark](benchmarks/renderer-benchmark.md). Renderer claims
for other devices or graph structures require additional measurement.

## 15. Ontodia Prototype Application

Ontodia is required as a separate prototype implementation, not as an equally
supported production renderer.

### RO-001 Prototype status

The Ontodia application MUST be labeled experimental/prototype in source,
documentation, builds, and UI.

### RO-002 Upstream risk disclosure

The project MUST record that the upstream `metaphacts/ontodia` repository was
archived in September 2024, is read-only, has substantially old implementation
history, uses legacy React APIs, and is licensed under LGPL-2.1-or-later.

### RO-003 Feasibility gate

Before feature implementation, a time-boxed spike MUST evaluate:

- Modern Node/Vite build compatibility.
- React version isolation or compatibility shell.
- Dependency vulnerabilities and abandoned packages.
- TypeScript compatibility.
- CSS and asset bundling.
- LGPL dynamic-linking/distribution obligations.
- Browser security policy compatibility.
- Representative ontology size and interaction behavior.

### RO-004 Separate build

Ontodia MUST be isolated in a separately deployable frontend build or package so
legacy dependencies cannot constrain the supported application.

### RO-005 GraphQL-backed data provider

The prototype MUST implement Ontodia's `DataProvider` semantics over bounded
GraphQL operations for class tree, class/property metadata, element metadata,
link types/counts, link expansion, and filtering.

### RO-006 No direct RDF/SPARQL providers

Ontodia's browser `RDFDataProvider`, arbitrary file fetch, and direct
`SparqlDataProvider` MUST NOT be used in the product architecture. The public
GraphQL boundary remains mandatory.

### RO-007 Prototype capabilities

Where feasible, the prototype SHOULD demonstrate:

- Class tree navigation.
- Class/property/individual search.
- Context-aware link navigation.
- Ontology-aware node templates.
- Property display.
- Diagram layout and persistence.
- Selected-entity synchronization.
- Bounded data retrieval.

### RO-008 Reduced guarantees

The Ontodia prototype is not required to match the supported application's
accessibility, responsive behavior, GPU overview, scale, performance, security
maintenance, or feature completeness.

### RO-009 Failure outcome

If the feasibility gate finds unacceptable security, license, build,
compatibility, or maintenance risk, the prototype phase MAY complete with a
documented spike, GraphQL-to-Ontodia provider mapping, and rejection ADR rather
than shipping an unsafe application.

### RO-010 No silent fork obligation

Production adoption MUST NOT occur without an explicit decision to own and
maintain a fork, including dependency updates, security response, React support,
license compliance, and release engineering.

## 16. Large Ontology Engineering

Large-ontology support means that the indexed backend can contain and query
millions of entities/triples while clients receive bounded views.

### LS-001 Indexed runtime

API operations MUST query an indexed persistent store and MUST NOT parse source
files or construct Python objects for every stored triple per request.

### LS-002 Immutable reasoned builds

Parsing, validation, classification, and materialization MUST occur in offline
versioned builds. API readers SHOULD use promoted read-only stores.

### LS-003 Bounded responses

Search, schema lists, instances, relationships, paths, comparisons,
explanations, findings, and overviews MUST be bounded and paginated or
explicitly truncated.

### LS-004 Query cancellation

Long-running retrieval, path, explanation, export, and overview operations MUST
support timeout and cancellation where the backend permits.

### LS-005 Batching

Multi-hop traversal and path algorithms MUST batch frontier retrieval and MUST
not issue one repository query per node at scale.

### LS-006 Precomputation

The ingestion pipeline SHOULD precompute class hierarchy indexes, predicate
statistics, semantic-kind counts, high-degree resource counts, and overview
clusters/samples required by the UI.

### LS-007 Caching

Stable ontology metadata, resource summaries, class trees, predicate metadata,
and bounded common expansions SHOULD be cacheable by ontology build ID and query
fingerprint.

### LS-008 Load shedding

The API MUST reject or degrade requests that exceed configured cost, queue,
memory, result-size, or execution-time budgets.

### LS-009 Scale tiers

Performance and reasoning validation MUST define at least:

| Tier | Approximate size | Purpose |
| --- | ---: | --- |
| S | Up to 100k triples | Unit, integration, and local development |
| M | Up to 10M triples | Representative deployment validation |
| L | Up to 100M triples | Large deployment and capacity testing |
| XL | Above 100M triples | Explicit architecture/capacity approval |

Tier boundaries MAY be revised with measurements. Full OWL 2 DL reasoning
complexity depends on axioms and expressivity, not only triple count.

### LS-010 Visible graph independence

Total ontology size MUST NOT increase the default visible detail budget. Detail
view remains bounded even when the backend contains millions of resources.

## 17. Security And Operator Controls

### SC-001 Authentication and authorization

Operator ingestion/promotion and saved/shared artifacts MUST require
authentication and authorization. Graph data authorization MUST be enforced
before retrieval results leave the service layer.

### SC-002 Upload and path containment

Ingestion MUST enforce configured roots, accepted formats, file-size limits,
archive/decompression limits, and path traversal prevention.

### SC-003 Parser hardening

RDF/XML and related parsers MUST prevent XML external entity expansion, local
file disclosure, arbitrary network fetches, and entity-expansion denial of
service.

### SC-004 Import allowlist

Imports MUST be pinned, checksummed, allowlisted, and preferably vendored. Build
logs MUST record every resolved import.

### SC-005 Reasoner isolation

External reasoners MUST run with least privilege in an isolated process or
container with bounded CPU, memory, time, disk, process count, and network
access.

### SC-006 Query abuse controls

GraphQL complexity, traversal, path, explanation, export, comparison, and
overview limits MUST be enforced independently of frontend controls.

### SC-007 Error disclosure

Public errors MUST NOT expose filesystem paths, query text, credentials,
process commands, stack traces, or internal store/reasoner details.

### SC-008 Audit trail

Ontology builds, validations, reasoner runs, promotions, rollbacks, exports,
saved-view sharing, and authorization failures MUST be auditable.

### SC-009 Data retention

Retention policies MUST define lifecycle for source packages, reasoner output,
promoted/rollback stores, saved sessions, exports, logs, and audit records.

## 18. Operations And Observability

### OR-001 Build lifecycle commands

Operators MUST have supported commands or administrative operations to list,
build, verify, back up, restore, promote, and roll back ontology store builds.

### OR-002 Readiness

Readiness MUST report backend-neutral status including active build ID, source
manifest hash, triple/resource/axiom counts, inferred count, reasoner/provider
status, reasoning profile, consistency, validation summary, and store-open
status.

### OR-003 Liveness

Liveness MUST not trigger expensive graph queries or reasoning.

### OR-004 Structured telemetry

Logs, metrics, and traces MUST record operation name, build ID, duration, result
counts, truncation, cache state, stable error code, and reasoner/build job state.
Sensitive literals and complete graph results MUST NOT be logged by default.

### OR-005 Backup and recovery

Store builds, manifests, profiles, reasoning evidence, and saved sessions MUST
have tested backup, restore, corruption detection, and rollback procedures.

### OR-006 Process model

Deployment documentation MUST define the supported single/multi-process access
model for embedded stores and prohibit undefined writer/reader combinations.

### OR-007 CI/CD

CI MUST enforce backend tests, frontend tests, lint, builds, GraphQL schema
compatibility, ingestion fixtures, reasoner conformance smoke tests, security
scans, and documentation validation.

## 19. Accessibility, Responsive Design, And Languages

### AX-001 Keyboard operation

Search, schema tree, graph actions, filters, paths, comparison, inspector,
tables, save/export, and dialogs MUST be keyboard operable with visible focus.

### AX-002 Textual equivalence

The supported application MUST provide searchable/filterable tables or trees
for the complete visible graph, class hierarchy, path, comparison, explanation,
and findings.

### AX-003 Non-color semantics

Semantic kinds, direction, asserted/inferred state, selection, warning, and
validation severity MUST use text, icons, shapes, or patterns in addition to
color.

### AX-004 Reduced motion

The application MUST respect `prefers-reduced-motion`, disable nonessential
animations, and provide manual layout controls without forced movement.

### AX-005 Screen-reader summaries

Every graph/overview state MUST expose a concise summary of visible node/edge
counts, active filters, truncation, selected resource, and available actions.

### AX-006 Responsive workflows

Search, graph/schema navigation, inspector, and textual relationship access MUST
remain usable without overlap at supported desktop, tablet, and mobile widths.

### AX-007 Multilingual labels

The UI MUST support active language selection, configured fallback order, and
display of literal language/datatype metadata.

### AX-008 Ontodia disclosure

The Ontodia prototype MUST disclose any known accessibility or responsive
limitations and MUST link to the supported application alternative.

## 20. Non-Functional Requirements

### NF-001 API latency targets

On agreed reference hardware with a warm Tier M store:

- Entity summary p95 SHOULD be below 150 ms.
- One-hop detail expansion up to 200 nodes SHOULD be below 500 ms.
- Schema hierarchy page p95 SHOULD be below 500 ms.
- Bounded path requests SHOULD complete or report budget exhaustion within 3 s.
- Explanation requests SHOULD complete, return an asynchronous job, or report a
  timeout within 5 s.

Targets MUST be measured on the custom Food ontology before release.

### NF-002 Startup

API startup against an existing promoted store SHOULD complete within 5 seconds
and MUST NOT parse or reason over source ontologies.

### NF-003 Detail interaction

The supported Cytoscape detail view SHOULD initialize a 500-node/1,000-edge
bounded view within 1 second and SHOULD maintain responsive pan/zoom on target
hardware.

### NF-004 Overview interaction

The cosmos.gl overview SHOULD initialize an approved bounded sample/aggregate
within 1 second and SHOULD maintain interactive pan/zoom on target integrated
GPUs. Exact overview limits require representative Food ontology benchmarks.

### NF-005 Browser memory

The supported application MUST enforce visible graph budgets and SHOULD keep
steady-state browser memory below an agreed target established per deployment.
Repeated expansion/collapse MUST not exhibit unbounded growth.

### NF-006 Ingestion reliability

A failed parse, validation, reasoner job, or store build MUST leave the active
build unchanged and available.

### NF-007 Reasoning budgets

Reasoning time and resource targets MUST be defined per ontology package and
scale tier. Failure to meet a configured budget MUST block promotion and retain
diagnostic evidence.

### NF-008 Bundle isolation

The normal supported frontend MUST code-split cosmos.gl and MUST NOT load
Ontodia. The Ontodia prototype MUST not add legacy dependencies to the supported
application bundle.

### NF-009 Reproducibility

Given identical source bytes, imports, profile, parser, reasoner, and
configuration, build identifiers and normalized semantic fixtures MUST be
reproducible.

### NF-010 Availability and recovery

Availability, recovery time, and recovery point targets MUST be defined before
production. At minimum, rollback to the last verified store build MUST be tested.

## 21. Testing And Conformance

### TC-001 Parser fixtures

Tests MUST cover every supported RDF/OWL serialization, multilingual and typed
literals, blank nodes, malformed sources, forbidden imports, XXE attempts,
oversized archives, and path violations.

### TC-002 OWL 2 DL conformance

The selected reasoner integration MUST run an approved OWL 2 DL conformance
corpus plus application-specific golden ontologies covering supported class and
property semantics.

### TC-003 Consistency fixtures

Tests MUST include consistent, inconsistent, unsatisfiable-class, unsupported
datatype, timeout, and resource-exhaustion cases.

### TC-004 Explanation fixtures

Golden tests MUST verify that explanations cite real supporting axioms/facts,
retain build/provider identity, remain bounded, and never fabricate unsupported
proofs.

### TC-005 Repository contracts

Every repository adapter MUST pass common entity, search, hierarchy,
relationship, count, expansion, path, comparison, provenance, and pagination
contracts.

### TC-006 GraphQL contracts

Tests MUST cover schema compatibility, authorization, stable errors, cursors,
timeouts, cancellation, complexity, aliases, response size, and backend-neutral
error text.

### TC-007 Shared frontend conformance

Both frontend applications MUST run shared tests for canonical selection,
search results, bounded retrieval, saved-session compatibility, and GraphQL
error handling where their feature sets overlap.

### TC-008 Supported renderer E2E

Browser tests MUST cover search, schema browsing, detail expansion, filters,
continuation, collapse/undo, path, comparison, explanation, tables, save/restore,
export, GPU fallback, and overview-to-detail transitions.

### TC-009 Ontodia feasibility tests

The Ontodia spike MUST produce reproducible build, dependency/security/license,
React compatibility, provider mapping, browser smoke, and representative-size
results before prototype feature work continues.

### TC-010 Accessibility

Automated and manual testing MUST cover keyboard-only operation, focus order,
screen-reader summaries/tables, contrast, non-color semantics, reduced motion,
and responsive layouts.

### TC-011 Scale and performance

Tests and benchmarks MUST cover backend scale tiers, high-degree resources,
deep hierarchies, dense axioms, repeated requests, concurrency, cold/warm
startup, ingestion/reasoning, browser memory, and renderer interaction.

### TC-012 Operational recovery

Tests MUST demonstrate failed candidate builds, backup/restore, promotion,
rollback, store corruption detection, and restart against a verified build.

## 22. Delivery Phases

### Phase A: Ontology-neutral foundation

Deliver:

- Versioned ontology profile.
- Generic semantic resource and relationship contracts.
- Dynamic prefixes, labels, categories, and predicate discovery.
- Removal of Wine assumptions from core APIs and supported frontend.
- Operator-managed ontology swap workflow.

Exit criteria:

- Wine and one structurally different ontology run without source changes.
- Supported UI legend, filters, schema tree, and inspector derive from metadata.

### Phase B: Full OWL 2 DL reasoning

Deliver:

- Reasoner selection ADR and `ReasoningProvider`.
- Isolated classification/consistency jobs.
- Materialized inferred graph and provenance.
- Unsupported/inconsistent build diagnostics.
- Explanation artifact generation where supported.

Exit criteria:

- OWL 2 DL conformance suite meets the approved provider baseline.
- Promotion gates on consistency and configured resource budgets.
- “Why?” returns real bounded justifications for golden cases.

### Phase C: Supported detail explorer

Deliver:

- Class/property/individual navigation.
- Ontology-aware inspector.
- Dynamic counts and filters.
- Path and comparison workflows.
- Complete visible-graph table.
- Arbitrary collapse and saved sessions.
- Accessibility and browser E2E coverage.

Exit criteria:

- All primary workflows pass on desktop, tablet, and mobile.
- Visible graph budgets and high-degree protections cannot be bypassed.

### Phase D: Supported GPU overview

Deliver:

- Server aggregate/sample contracts.
- cosmos.gl production adapter.
- Capability detection and fallback.
- Overview labels/hover summaries.
- Overview-to-detail transitions.

Exit criteria:

- Representative custom Food ontology overview meets approved performance,
  memory, accessibility, and fallback criteria.

### Phase E: Ontodia prototype

Deliver:

- Feasibility/license/security report.
- Isolated build if approved.
- GraphQL-backed Ontodia DataProvider.
- Class tree, search, navigation, templates, and diagram persistence spike.
- Comparison against the supported application.

Exit criteria:

- Either the bounded prototype passes its explicit gate, or a rejection ADR
  documents why production use is unsafe or unjustified.

### Phase F: Advanced research workflows

Deliver:

- Inference explanation UI.
- Entity comparison.
- Ontology build diff.
- Query history/bookmarks.
- Save/share/export.
- Validation and consistency dashboards.

Exit criteria:

- Research workflows retain provenance, bounded results, and build identity.

### Phase G: Production operations

Deliver:

- Authenticated operator controls.
- Import security.
- Store/reasoner backup, restore, promotion, rollback, and audit.
- GraphQL abuse protection.
- Telemetry, CI/CD, deployment, security/license review, and runbooks.
- Final removal or archival of GraphDB runtime code after rollback no longer
  depends on it.

Exit criteria:

- Production readiness review approves security, recovery, performance,
  accessibility, operations, and support ownership.

## 23. Acceptance Criteria

### AC-101 Ontology swap

Given two approved ontology packages with different namespaces, classes, and
predicates, an operator can build and promote either package without changing
core application code, and the supported explorer updates its metadata-driven
navigation and styles.

### AC-102 Full reasoning build

Given a valid OWL 2 DL ontology, the configured external reasoner classifies it,
reports consistency, exports/materializes queryable inferred facts, and records
provider/build provenance before promotion.

### AC-103 Inconsistent ontology

Given an inconsistent ontology, promotion is blocked by default and the
operator/user receives bounded diagnostics without replacing the active build.

### AC-104 Ontology-aware inspection

Selecting a class, individual, or property displays its canonical IRI,
multilingual labels, semantic kind, types/hierarchy, annotations, applicable
property semantics, provenance, and supported restrictions.

### AC-105 Bounded exploration

Every graph operation applies server limits, exposes truncation/continuation,
and cannot cause the supported detail view to exceed its hard visible budget.

### AC-106 Inference distinction

Asserted and inferred facts are individually distinguishable, filterable, and
traceable to build/source/provider metadata in both visual and textual views.

### AC-107 Why explanation

Selecting an explainable inferred fact returns a real bounded reasoner
justification; unavailable explanations return the stable unavailable outcome.

### AC-108 Path outcomes

Path discovery distinguishes success, no path, timeout, cancellation, and
budget exhaustion and never runs an unbounded traversal.

### AC-109 Large backend

The approved large ontology tier remains searchable and traversable through
bounded operations without loading source files or all triples into request-time
Python objects.

### AC-110 Supported renderers

Cytoscape renders bounded detail, cosmos.gl renders only approved aggregate or
sample overview data, and users can drill from overview to a fresh detail query.

### AC-111 GPU fallback

When WebGL requirements are unavailable or initialization fails, the supported
application remains usable through bounded Cytoscape detail and textual views.

### AC-112 Ontodia isolation

The Ontodia prototype builds separately, accesses graph data only through
GraphQL-backed provider operations, and does not add legacy dependencies to the
supported application.

### AC-113 Accessibility

All primary supported workflows are keyboard operable and have equivalent
textual representations with non-color asserted/inferred semantics.

### AC-114 Recovery

A failed ontology or reasoner build leaves the active store available, and an
operator can restore/promote the previous verified build using documented
procedures.

## 24. Current-State Mapping

This table reflects [Project Status 2026-09-10](project-status-2026-09-10.md).

| Capability | Current state | Required destination |
| --- | --- | --- |
| Repository abstraction | Implemented | Preserve and generalize |
| PyOxigraph runtime | Implemented/default | Production hardening |
| Content-addressed ingestion | Implemented | Imports/security/operations |
| Wine semantic profile | Partial | Full OWL 2 DL provider |
| Generic ontology profile | Not implemented | Phase A |
| Dynamic semantic kinds | Not implemented | Phase A |
| Ontology summary/schema APIs | Not implemented | Phase A/C |
| Bounded one-hop expansion | Implemented | Preserve |
| Multi-hop/path GraphQL | Partial/internal | Phase C |
| Provenance on relationships | Partial/internal graph separation | Phase B/C |
| Inference explanation | Not implemented | Phase B/F |
| Cytoscape detail renderer | Implemented | Ontology-neutral hardening |
| cosmos.gl benchmark | Implemented | Production overview in Phase D |
| Ontodia renderer | Not implemented | Prototype gate in Phase E |
| Visible graph budgets | Implemented | Preserve |
| Direction/relation/inference filters | Implemented but Wine-specific | Metadata-driven filters |
| Undo latest expansion | Implemented | Arbitrary collapse/history |
| Selected relationship table | Implemented | Complete visible graph table |
| Saved sessions/export | Not implemented | Phase C/F |
| Operator build lifecycle | Partial build/promotion | Verify/backup/restore/rollback |
| GraphQL complexity/security | Not implemented | Phase G |
| CI/deployment | Not implemented | Phase G |
| GraphDB parity adapter | Present | Remove/archive after Phase G gate |

## 25. Feature Traceability

| Requested feature/source | Requirement coverage |
| --- | --- |
| Standalone graph explorer | PG-001, PNG-001, AR-101 |
| Swap underlying ontology | PG-002, OP-001 through OP-009, AC-101 |
| Parse OWL/RDF formats | OP-002, TC-001 |
| Classes, properties, individuals | SM-001, SD-005, GE-003 |
| Ontology-aware representation | PG-001, SM-005 through SM-009 |
| Class hierarchy | SM-006, GQ-105, GE-003 |
| Domain/range and characteristics | SM-007, GE-009 |
| Restrictions and complex expressions | RS-007, SM-006 |
| Full reasoning and inference | RS-001 through RS-014, Phase B |
| Asserted/inferred styling | PG-004, SM-008, GE-010 |
| “Why?” explanations | UW-006, RS-010, GQ-112, GE-011, AC-107 |
| Consistency/error indicators | UW-007, RS-004, GQ-113, GE-012 |
| Search/filter | SD-001 through SD-006, GE-004 |
| Expand/collapse | GE-002, GE-003, GE-005 |
| Parents/children/instances | GE-003, GQ-105 |
| Incoming/outgoing relationships | GQ-107, GE-003, GE-004 |
| Hide literals/annotations | GE-004 |
| Traversal depth | GQ-107, GE-006 |
| Shortest path | UW-004, GQ-109, GQ-110, AC-108 |
| Entity comparison | UW-005, GQ-111, GE-013 |
| Three-panel interface | GE-001 |
| Inspector | GE-009, AC-104 |
| Save/load visualization | UW-008, SE-001, SE-002 |
| PNG/SVG export | SE-005 |
| JSON/CSV/GraphML export | SE-004 |
| Large ontology support | PG-003, LS-001 through LS-010 |
| Cytoscape/Cosmos version | RC-001 through RC-010, AC-110, AC-111 |
| Ontodia version | RO-001 through RO-010, AC-112 |
| Direct graph querying | PNG-003, GQ-107 through GQ-113 |
| Responsive/accessibility | AX-001 through AX-008, AC-113 |
| Query history/bookmarks | GE-014 |
| Ontology build diff | GE-015 |
| Shareable links | SE-003 |

## 26. Definition Of Done

The product specification is satisfied when:

1. All MUST requirements are implemented or superseded by an approved ADR.
2. At least two structurally different ontology packages can be installed and
   explored without core code changes.
3. The selected external reasoner passes the approved OWL 2 DL conformance,
   consistency, materialization, and explanation gates.
4. The supported Cytoscape/Cosmos application passes functional,
   accessibility, security, performance, and recovery acceptance criteria.
5. The Ontodia prototype passes its limited feasibility gate or has a documented
   rejection ADR.
6. Large ontology operation is demonstrated through indexed bounded queries,
   not unbounded browser rendering.
7. Build, promotion, rollback, backup, restore, and corruption recovery are
   documented and tested.
8. Public GraphQL abuse protection, authentication, authorization, telemetry,
   and stable errors are production-ready.
9. CI/CD enforces parser, reasoner, repository, GraphQL, frontend, accessibility,
   security, and documentation gates.
10. GraphDB runtime code is removed or formally retained only as an archived
    parity tool after operational rollback no longer depends on it.

## 27. Source Documents And Decisions

This specification incorporates and resolves requirements from:

- [Updated Food Knowledge Graph Platform Expansion](../FKG.in_User_Interface_Platform_Expansion_Updated.md)
- [LLM brainstorming notes](spec_LLM_brainstorming.md)
- [Current project status](project-status-2026-09-10.md)
- [OWL store migration analysis](owl-store-migration-analysis.md)
- [OWL store migration requirements](owl-store-migration-requirements.md)
- [OWL store migration implementation plan](owl-store-migration-implementation-plan.md)
- [GraphDB/Oxigraph parity report](benchmarks/owl-store-parity.md)
- [Renderer benchmark](benchmarks/renderer-benchmark.md)
- [Dual-renderer ADR](adr/0001-dual-graph-renderer.md)

The Ontodia requirements also account for upstream facts verified on 2026-09-10:

- `metaphacts/ontodia` was archived on 2024-09-26.
- Its latest substantive repository code is approximately six years old.
- It exposes a replaceable `DataProvider`, including class, property, element,
  link, navigation, and filter operations suitable for a GraphQL-backed adapter.
- Its bundled RDF/SPARQL providers are not permitted by this architecture.
- It uses legacy React APIs and must be isolated from the supported application.
- It is licensed under LGPL-2.1-or-later and requires distribution review.