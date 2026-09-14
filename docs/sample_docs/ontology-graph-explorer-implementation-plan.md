# Ontology and Knowledge Graph Explorer: Complete Implementation Plan

- **Document type:** Delivery and implementation plan
- **Status:** Draft for execution
- **Version:** 1.0.0
- **Last updated:** 2026-09-10
- **Requirements baseline:** [Ontology and Knowledge Graph Explorer Specification](ontology-graph-explorer-requirements.md)
- **Current-state baseline:** [Project Status 2026-09-10](project-status-2026-09-10.md)

## 1. Purpose

This document translates the product specification into four dependency-gated
development sprints:

1. **Sprint 1:** Core platform and semantic requirements required by both
   frontend implementations.
2. **Sprint 2:** Supported Cytoscape detail and cosmos.gl overview application.
3. **Sprint 3:** Separately deployed Ontodia prototype and accept/reject gate.
4. **Sprint 4:** Nice-to-have research workflows and measured non-functional
   optimization.

These sprints are delivery stages, not assumed equal calendar timeboxes. Sprint
1 is intentionally large because reasoning, ontology neutrality, security,
bounded execution, recovery, and shared contracts cannot safely be postponed
until after renderer implementation.

## 2. Planning Principles

### IP-001 Requirement-driven delivery

Every story MUST reference requirement IDs from the product specification.
Changing a MUST requirement requires an approved ADR or specification revision.

### IP-002 Vertical validation

Each sprint MUST end with executable validation from source ingestion through
GraphQL and the relevant frontend rather than isolated component completion.

### IP-003 Ontology neutrality

Wine remains a conformance fixture. At least one structurally different
ontology MUST be used before Sprint 1 can close.

### IP-004 Bounded-by-default behavior

No sprint may introduce an unbounded graph, schema, path, explanation, export,
or renderer operation.

### IP-005 Supported versus experimental products

Sprint 2 produces the supported application. Sprint 3 produces an explicitly
experimental Ontodia prototype or a documented rejection. Ontodia MUST NOT
delay the supported application or leak legacy dependencies into it.

### IP-006 Security is not polish

Authentication boundaries, parser/import hardening, reasoner isolation,
GraphQL abuse controls, promotion safety, provenance, and rollback belong in
Sprint 1. They MUST NOT be deferred to Sprint 4 as “non-functional” work.

### IP-007 Accessibility is functional

Keyboard workflows, textual graph equivalents, non-color semantics, focus
management, reduced motion, and GPU fallback are acceptance requirements for
Sprint 2, not optional Sprint 4 polish.

## 3. Current Starting Point

Reusable implementation already present:

- PyOxigraph is the default indexed runtime.
- RDF/XML and Turtle sources build into content-addressed stores.
- Store builds are atomic and preserve failed-build rollback.
- `GraphRepository` isolates storage concerns.
- `GraphService` and Strawberry GraphQL provide bounded one-hop expansion.
- Opaque cursors and traversal budgets are implemented.
- A Wine-specific materialization profile provides selected class, inverse, and
  symmetric semantics.
- GraphDB parity has zero unresolved differences for configured fixtures.
- Cytoscape detail rendering, graph-state limits, direction/relation filters,
  cursor continuation, undo, and a selected-node relationship table exist.
- cosmos.gl has benchmark-only integration and an accepted dual-renderer ADR.
- Backend and frontend automated tests currently pass.

Key constraints at the start:

- Core semantic models, repository maps, GraphQL concrete types, and frontend
  branding remain Wine-specific.
- Full OWL 2 DL reasoning and explanations do not exist.
- Ontology imports are disabled.
- Ontology metadata and schema browsing APIs do not exist.
- Store backup/restore/verification and GraphQL abuse protection are incomplete.
- cosmos.gl is not a production overview.
- Ontodia is absent and upstream is archived.

## 4. Shared Definition Of Ready

A story is ready for implementation only when:

- Requirement IDs and expected behavior are identified.
- Public API and data migration impact are known.
- Security, boundedness, provenance, and accessibility impact are considered.
- Test fixtures and acceptance checks are defined.
- Dependencies on earlier stories are satisfied.
- Any reasoner, renderer, or third-party license implications are recorded.

## 5. Shared Definition Of Done

A story is complete only when:

- Code and migrations are implemented with database/renderer boundaries intact.
- Unit, contract, integration, and applicable browser tests pass.
- Public errors and telemetry contain no sensitive implementation details.
- Documentation, configuration examples, and runbooks are updated.
- Performance-sensitive behavior is measured where required.
- `git diff --check`, backend tests, frontend tests, lint, and builds pass.
- Core implementation files use focused Conventional Commits.

## 6. Sprint 1: Core Platform And Semantic Foundation

### 6.1 Sprint Goal

Deliver an ontology-neutral, bounded, secure, reasoned, recoverable backend and
shared application contract that both frontend implementations can consume.

### 6.2 Requirement Coverage

Primary requirement groups:

- Goals: `PG-001` through `PG-006`
- Architecture: `AR-101` through `AR-107`
- Ontology packages: `OP-001` through `OP-009`
- Reasoning: `RS-001` through `RS-014`
- Semantic model: `SM-001` through `SM-009`
- GraphQL core: `GQ-101` through `GQ-113`, `GQ-115`, `GQ-116`
- Discovery core: `SD-001` through `SD-005`
- Large ontology backend: `LS-001` through `LS-010`
- Security: `SC-001` through `SC-009`
- Operations: `OR-001` through `OR-007`
- Critical non-functional requirements: `NF-002`, `NF-006` through `NF-010`
- Tests: `TC-001` through `TC-007`, `TC-012`
- Acceptance: `AC-101` through `AC-109`, `AC-114`

### 6.3 Entry Criteria

- Current migration branch tests and builds pass.
- Current RDF store can be recreated from committed Wine sources.
- Existing GraphQL schema is recorded for compatibility testing.
- One non-Wine ontology fixture is selected and legally usable.
- Reasoner evaluation hardware and deployment constraints are known.

### 6.4 Workstream 1: Ontology-Neutral Profiles

#### S1-EP1-ST1 Define the ontology package schema

Requirements: `OP-001`, `OP-002`, `OP-005`, `NF-009`

Implement a versioned manifest/profile with:

- Package ID, version, title, description, and ontology IRIs.
- Source files, explicit formats, named graphs, and SHA-256 checksums.
- Base IRI, prefixes, imports, preferred languages, and label fallbacks.
- Label, alternate-label, description, image, and identifier predicates.
- Searchable resource scopes.
- Traversable, hidden, sensitive, and display-only predicates.
- Semantic category and visual-style mappings.
- Validation and reasoning configuration.
- Store, query, path, explanation, and renderer limits.
- Compatibility and minimum application version.

Deliverables:

- Pydantic manifest/profile models.
- JSON Schema or equivalent generated schema.
- Wine package profile.
- Second non-Wine package profile.
- Validation and migration tests.

#### S1-EP1-ST2 Remove Wine assumptions from core contracts

Requirements: `PG-002`, `OP-003`, `OP-004`, `SM-001`, `GQ-101`

Tasks:

- Replace fixed Wine entity kinds with generic semantic resource kinds.
- Preserve Wine-specific compatibility fields behind deprecation markers.
- Replace fixed namespace/type/predicate maps in the Oxigraph adapter.
- Replace hardcoded relation options, legend entries, branding, and colors with
  profile metadata.
- Move domain helpers such as Wines-by-Grape outside the generic repository
  port or mark them compatibility-only.
- Ensure core tests run with both ontology fixtures.

Deliverables:

- Generic semantic types and profile resolver.
- Dynamic repository query policies.
- Dynamic frontend metadata models.
- Compatibility/deprecation plan.

#### S1-EP1-ST3 Expose active profile metadata

Requirements: `OP-008`, `GQ-103`, `SD-005`

Add backend-neutral GraphQL types and queries for:

- Active ontology package and store build.
- Prefixes and language policy.
- Semantic categories and display tokens.
- Available predicates and capabilities.
- Configured limits.
- Reasoner and validation state.

Acceptance:

- Switching between Wine and the second ontology updates search scopes,
  filters, legends, and labels without code changes.

### 6.5 Workstream 2: Secure Imports And Parsing

#### S1-EP2-ST1 Vendor and resolve ontology imports

Requirements: `OP-007`, `SC-004`, `TC-001`

Tasks:

- Vendor the Food ontology imported by the Wine fixture.
- Define manifest mappings from import IRI to local artifact.
- Verify import checksum and expected ontology IRI.
- Recursively resolve imports with cycle detection.
- Load imported content into a dedicated named graph.
- Record the import graph in build metadata.
- Reject undeclared, missing, changed, or network-only imports.

#### S1-EP2-ST2 Harden source ingestion

Requirements: `SC-002`, `SC-003`, `NF-006`

Tasks:

- Enforce configured source roots and prevent path traversal.
- Enforce accepted formats and per-file/package size limits.
- Add compressed input limits before optional archive support.
- Verify RDF/XML parser behavior against XXE and entity-expansion fixtures.
- Prohibit network/file access initiated by parsers.
- Run parser operations in bounded worker processes when needed.
- Retain failed-build diagnostics without exposing local paths publicly.

#### S1-EP2-ST3 Extend supported serialization tests

Requirements: `OP-002`, `TC-001`

Add fixtures for RDF/XML, Turtle, JSON-LD, N-Triples, N-Quads, TriG, OWL/XML
if selected, multilingual literals, typed values, blank nodes, malformed input,
and hostile parser cases.

### 6.6 Workstream 3: Full OWL 2 DL Reasoning

#### S1-EP3-ST1 Select the reasoner

Requirements: `RS-001`, `RS-002`, `RS-013`

Time-box and compare maintained candidates for:

- OWL 2 DL conformance.
- Classification and realization.
- Object/data property inference.
- Consistency and unsatisfiable-class reporting.
- Explanation/justification support.
- Incremental or batch operation.
- License and distribution terms.
- Java/native/runtime requirements.
- Resource limits and process isolation.
- Determinism and export formats.

Deliverable: reasoner selection ADR. No reasoner becomes production-default
without this ADR.

#### S1-EP3-ST2 Define `ReasoningProvider`

Requirements: `AR-104`, `RS-001`, `AR-107`

Define provider operations for:

- Validate input/profile compatibility.
- Classify ontology.
- Check consistency.
- List unsatisfiable classes.
- Materialize/export inferred facts.
- Produce explanation artifacts where supported.
- Report unsupported constructs and provider capabilities.
- Return bounded job metrics and diagnostics.

Provider types MUST not leak into public GraphQL or repository models.

#### S1-EP3-ST3 Implement isolated reasoning jobs

Requirements: `RS-003`, `RS-004`, `SC-005`, `NF-007`

Tasks:

- Run reasoner in a least-privilege process/container.
- Enforce CPU, memory, elapsed-time, disk, process, and network limits.
- Capture stdout/stderr as protected build diagnostics.
- Cancel and terminate over-budget jobs.
- Block promotion on inconsistency or provider failure by default.
- Support a clearly marked quarantined build only by explicit policy.

#### S1-EP3-ST4 Materialize OWL semantics and provenance

Requirements: `RS-005` through `RS-009`, `SM-008`

Materialize/queryably preserve:

- Class hierarchy and individual type inferences.
- Equivalent/disjoint class semantics.
- Union, intersection, complement, enumeration, and restrictions.
- Subproperty, equivalent, inverse, symmetric, transitive, and property-chain
  consequences.
- Same-as, different-from, domain/range, and negative assertions.
- Provider/build/source provenance for every inferred fact.

The existing `rdfs-wine-parity` profile remains a separate fast development
profile and MUST not be labeled full OWL 2 DL.

#### S1-EP3-ST5 Implement explanation artifacts

Requirements: `RS-010`, `RS-011`, `GQ-112`, `UW-006`

Tasks:

- Define conclusion, axiom/fact, proof-step, source, and provider models.
- Bound explanation depth, nodes, alternatives, and serialized size.
- Store explanation artifacts by build and stable handle.
- Return `EXPLANATION_UNAVAILABLE` when unsupported.
- Add golden “Why?” fixtures grounded in real axioms.

### 6.7 Workstream 4: Generic Semantic Domain And Repository

#### S1-EP4-ST1 Implement semantic resource and typed-value models

Requirements: `SM-001` through `SM-005`

Add models for classes, individuals, object/datatype/annotation properties,
generic RDF properties, literals, anonymous expressions, annotations,
multilingual labels, compact IRIs, source graphs, and build identity.

#### S1-EP4-ST2 Implement class and property models

Requirements: `SM-006`, `SM-007`, `RS-007`, `RS-008`

Add repository operations for:

- Direct/all parents and children.
- Equivalent/disjoint classes.
- Paginated instances and counts.
- Restrictions and complex class expressions.
- Property domain/range, hierarchy, inverse/equivalent properties, and
  characteristics.
- Predicate usage counts and labels.

#### S1-EP4-ST3 Add relationship provenance

Requirements: `SM-008`, `PG-004`, `GQ-104`

Extend relationships with stable build-scoped ID, full predicate IRI, compact
IRI, preferred label, source/target, canonical direction, asserted/inferred
provenance, source graph, and explanation handle.

#### S1-EP4-ST4 Add dynamic search and discovery

Requirements: `SD-001` through `SD-005`, `GQ-105`, `GQ-106`

Implement bounded cursor search over configured labels, aliases, IRIs, kinds,
classes, namespaces, language, source graph, and provenance. Apply limits in the
store query or search index.

#### S1-EP4-ST5 Add expansion preview and high-degree counts

Requirements: `GQ-108`, `LS-006`, `GE-002`

Return counts grouped by predicate, direction, semantic kind, and provenance
before neighbor hydration. Precompute or index high-degree counts during
ingestion where justified.

### 6.8 Workstream 5: Paths, Comparison, And Bounded Operations

#### S1-EP5-ST1 Implement repository-native path traversal

Requirements: `GQ-109`, `GQ-110`, `LS-004`, `LS-005`, `AC-108`

Tasks:

- Move path traversal behind the repository port.
- Batch frontier lookup.
- Enforce direction, predicate, semantic-kind, depth, visited-node, time, and
  cancellation budgets.
- Preserve canonical predicates and provenance.
- Distinguish success, no path, timeout, cancellation, budget exhaustion, and
  unsupported semantics.

#### S1-EP5-ST2 Implement bounded comparison

Requirements: `GQ-111`, `UW-005`

Return paginated common/unique types, annotations, properties, predicates, and
neighbors with build/provenance metadata.

#### S1-EP5-ST3 Standardize errors

Requirements: `GQ-115`, `SC-007`

Implement the complete stable error-code set and verify that public errors do
not contain paths, internal query text, process commands, or stack traces.

### 6.9 Workstream 6: GraphQL Safety And Access Control

#### S1-EP6-ST1 Add complexity and response controls

Requirements: `GQ-116`, `SC-006`, `LS-008`

Enforce depth, field count, alias repetition, operation cost, response-size,
resolver timeout, concurrent-operation, and rate limits. Add tests proving
aliases and fragments cannot bypass traversal budgets.

#### S1-EP6-ST2 Add cancellation and timeouts

Requirements: `LS-004`, `NF-001`

Propagate cancellation and deadlines through GraphQL, service, repository,
reasoner jobs, paths, explanations, comparisons, exports, and overview queries.

#### S1-EP6-ST3 Define authentication and authorization boundary

Requirements: `SC-001`, `SC-006`

Implement or provide integration ports for authenticated users/operators and
authorization checks before graph data or administrative operations leave the
service layer. Add a development identity provider only if clearly isolated.

### 6.10 Workstream 7: Store Operations And Observability

#### S1-EP7-ST1 Complete store lifecycle operations

Requirements: `OR-001`, `OR-005`, `AC-114`

Add commands/APIs to list, verify, back up, restore, promote, roll back,
quarantine, and remove store builds. Test interrupted builds and corruption.

#### S1-EP7-ST2 Add readiness and build metadata

Requirements: `OR-002`, `OR-003`, `NF-002`

Readiness MUST report active build, manifest hash, ontology IDs, triple/resource
and inferred counts, semantic profile, reasoner status, consistency, validation
summary, and store-open state. Liveness remains inexpensive.

#### S1-EP7-ST3 Add structured telemetry and audit

Requirements: `OR-004`, `SC-008`, `SC-009`

Record operation, build, duration, counts, truncation, cache state, stable error,
reasoner/build state, promotion/rollback, export/session actions, and auth
failures. Define retention without logging complete sensitive results.

#### S1-EP7-ST4 Define process and deployment model

Requirements: `OR-006`, `NF-010`

Document supported readers/writers, store ownership, Windows/Linux behavior,
restart/swap rules, recovery objectives, and deployment topology.

### 6.11 Workstream 8: Shared Frontend Contracts

#### S1-EP8-ST1 Create shared packages

Requirements: `AR-105`, `AR-106`, `TC-007`, `NF-008`

Extract separately versioned/shared modules for:

- GraphQL client and generated types.
- Ontology/profile models.
- Canonical selection state.
- Renderer-neutral graph/session state.
- Stable error handling.
- Accessibility summaries.
- Design tokens and reusable controls.

Define separate supported-app and Ontodia-app entry points and dependency
boundaries.

#### S1-EP8-ST2 Define renderer and provider contracts

Define:

- `DetailGraphRenderer` for bounded rich neighborhoods.
- `OverviewGraphRenderer` for aggregate/sample graphs.
- `OntologyDataProvider` for class/property/individual metadata and bounded
  navigation.
- Session and selection synchronization contracts shared across frontends.

### 6.12 Workstream 9: Testing And CI Foundation

#### S1-EP9-ST1 Expand conformance fixtures

Requirements: `TC-001` through `TC-006`, `TC-012`

Add:

- Two ontology packages.
- OWL 2 DL conformance subset.
- Consistent/inconsistent/unsatisfiable ontologies.
- Unsupported datatype/construct fixtures.
- Explanation goldens.
- High-degree, deep hierarchy, dense axiom, and large generated fixtures.
- Repository and GraphQL contract suites.
- Security and recovery fixtures.

#### S1-EP9-ST2 Add CI gates

Requirements: `OR-007`

CI MUST run backend tests, frontend shared tests, lint/build, GraphQL schema
compatibility, ingestion and reasoning smoke tests, security scans, license
checks, and documentation/link/requirement-ID validation.

### 6.13 Sprint 1 Deliverables

- Generic versioned ontology package/profile.
- Wine and non-Wine conformance packages.
- Secure, import-aware ingestion.
- Reasoner ADR and isolated full OWL 2 DL provider.
- Reasoned immutable store with consistency and provenance.
- Generic ontology-aware repository and domain model.
- Dynamic profile, schema, metadata, search, count, path, comparison,
  explanation, validation, and bounded graph APIs.
- Complete stable errors and GraphQL abuse protection.
- Store operations, readiness, telemetry, audit, backup, and rollback.
- Shared frontend packages and renderer/provider interfaces.
- Enforced CI and conformance suites.

### 6.14 Sprint 1 Exit Gate

Sprint 1 is complete only when:

1. Wine and a structurally different ontology build and run without core code
   changes (`AC-101`).
2. The selected reasoner passes the approved OWL 2 DL baseline and consistency
   gates (`AC-102`, `AC-103`).
3. Real explanation fixtures return bounded provider-generated justifications
   (`AC-107`).
4. All repository and GraphQL operations are bounded, cancellable, authorized,
   and return stable outcomes (`AC-105`, `AC-108`, `AC-109`).
5. Failed parse/reasoner/store candidates cannot replace the active build, and
   backup/restore/rollback are demonstrated (`AC-114`).
6. Profile/schema metadata is sufficient for both Sprint 2 and Sprint 3
   frontend providers.
7. CI passes all Sprint 1 conformance, security, recovery, and compatibility
   checks.

### 6.15 Sprint 1 Risks

| Risk | Mitigation |
| --- | --- |
| Reasoner does not provide explanations | Evaluate before selection; return explicit unavailable capability |
| Full DL reasoning exceeds resources | Isolated quotas, package-specific budgets, asynchronous builds, no request-time reasoning |
| Blank-node identifiers change | Canonicalize or scope IDs to build and validate saved-session compatibility |
| Generic APIs become too broad | Deliver vertical resource/class/property fixtures and contract tests incrementally |
| Security work is underestimated | Treat ingestion, reasoner, GraphQL, and operator threat models as exit gates |
| Embedded store process contention | Explicit single-writer/read-only-reader topology and integration tests |

### 6.16 Sprint 1 Suggested Pull Requests

1. Ontology package/profile and second fixture.
2. Secure imports and parser hardening.
3. Reasoner ADR and provider spike.
4. Isolated full reasoning and provenance pipeline.
5. Generic semantic repository/domain models.
6. Dynamic schema/search/count APIs.
7. Paths, comparison, explanations, validation APIs.
8. GraphQL protection and authorization boundary.
9. Store lifecycle/readiness/telemetry.
10. Shared frontend contracts and CI.

## 7. Sprint 2: Supported Cytoscape And Cosmos Application

### 7.1 Sprint Goal

Deliver the production-supported ontology explorer using Cytoscape for bounded
detail and cosmos.gl for bounded aggregate/sample overview, with complete
semantic workflows and accessible alternatives.

### 7.2 Requirement Coverage

- User workflows: `UW-001` through `UW-008`
- Session API: `GQ-114`
- Discovery UI: `SD-005`, `SD-006`
- Exploration: `GE-001` through `GE-013`
- Save/restore core: `SE-001`, `SE-002`
- Renderer: `RC-001` through `RC-010`
- Accessibility: `AX-001` through `AX-007`
- Performance: `NF-001`, `NF-003` through `NF-005`, `NF-008`
- Tests: `TC-008`, `TC-010`, `TC-011`
- Acceptance: `AC-104` through `AC-111`, `AC-113`

### 7.3 Entry Criteria

- Sprint 1 exits successfully.
- Shared frontend packages and GraphQL client are published locally.
- Ontology metadata, dynamic predicates, preview counts, path, comparison,
  explanation, session, and overview contracts are stable.
- Supported target browsers/devices and Food ontology fixture are available.

### 7.4 Workstream 1: Application Shell And Discovery

#### S2-EP1-ST1 Build metadata-driven navigation

Requirements: `UW-001`, `SD-001` through `SD-005`, `GE-001`

Implement:

- Ontology/build selector and summary.
- Separate Classes, Properties, and Individuals navigation tabs/tree.
- Paginated search and filters for kind, class, namespace, language, source, and
  provenance.
- Dynamic semantic legend and available predicate filters.
- Loading, empty, truncated, unauthorized, and failure states.

#### S2-EP1-ST2 Add language and namespace controls

Requirements: `SM-003`, `AX-007`, `SD-002`

Users can select label language/fallback, view compact/full IRIs, copy canonical
IRIs, and inspect namespace/prefix definitions.

#### S2-EP1-ST3 Add command palette

Requirements: `SD-006`

Provide keyboard actions for resource search, focus, expansion, filters, path,
comparison, explanation, save/export, and view switching.

### 7.5 Workstream 2: Semantic Inspector

#### S2-EP2-ST1 Implement generic resource inspection

Requirements: `SM-005`, `GE-009`, `AC-104`

Display canonical/compact IRI, kinds, multilingual labels, descriptions,
images, typed values, annotations, asserted/inferred types, source graphs,
active build, and applicable actions.

#### S2-EP2-ST2 Implement class inspection

Requirements: `SM-006`, `UW-003`, `GE-003`

Display parents, children, equivalents, disjoints, counts, instances, class
expressions, restrictions, and navigation actions.

#### S2-EP2-ST3 Implement property inspection

Requirements: `SM-007`, `UW-003`

Display property kind, hierarchy, domain, range, inverse/equivalent properties,
characteristics, annotations, counts, and example usage.

#### S2-EP2-ST4 Add consistency and provenance panels

Requirements: `UW-007`, `GE-010`, `GE-012`

Show build consistency, validation findings, unsupported constructs, fact
provenance, reasoner/provider, and non-color asserted/inferred markers.

### 7.6 Workstream 3: Cytoscape Detail Exploration

#### S2-EP3-ST1 Generalize the current detail renderer

Requirements: `RC-001`, `RC-002`, `RC-007`

Replace Wine-specific styles with profile-driven semantic kinds, labels,
icons/shapes, relation styles, and provenance patterns while preserving the
500-node/1,000-edge hard budget.

#### S2-EP3-ST2 Add expansion previews and supernode handling

Requirements: `GQ-108`, `RC-008`, `GE-002`

Before high-degree expansion, show grouped counts and require users to choose
predicate, direction, kind, provenance, page, or aggregation. Never add rejected
nodes or dangling edges.

#### S2-EP3-ST3 Complete expand/collapse history

Requirements: `GE-005`, `SE-001`

Support undo/redo, collapse selected expansion, remove selected node/subgraph,
preserve shared dependencies, and retain renderer-neutral history.

#### S2-EP3-ST4 Add multi-hop and layout controls

Requirements: `GE-003`, `GE-004`, `GE-006`

Add one-hop versus bounded multi-hop modes, depth and semantic filters,
cancellation, layout choice, focus, fit, pinning, and reduced-motion behavior.

### 7.7 Workstream 4: Textual And Accessible Views

#### S2-EP4-ST1 Implement whole-visible-graph table

Requirements: `GE-008`, `AX-002`, `AX-005`

Provide a sortable/filterable/paginated table for every visible relationship,
with source, predicate, target, direction, provenance, source graph, and actions.

#### S2-EP4-ST2 Implement hierarchy and findings trees/tables

Requirements: `AX-001` through `AX-005`

Provide keyboard-accessible alternatives for class hierarchy, paths,
comparison, proof steps, consistency, and validation findings.

#### S2-EP4-ST3 Complete accessibility behavior

Requirements: `AX-001` through `AX-007`, `AC-113`

Implement focus management, announcements, graph summaries, non-color semantic
cues, reduced motion, contrast, keyboard shortcuts, responsive panel
alternatives, and multilingual literal metadata.

### 7.8 Workstream 5: Paths, Comparison, And Explanation UI

#### S2-EP5-ST1 Path builder and results

Requirements: `UW-004`, `GQ-109`, `GQ-110`, `AC-108`

Allow users to choose endpoints, direction, predicates, kinds, depth, and
inference. Display success, no path, timeout, cancellation, and budget
exhaustion distinctly and add successful paths to the bounded detail view.

#### S2-EP5-ST2 Entity comparison

Requirements: `UW-005`, `GE-013`

Pin at least two resources and show bounded shared/unique types, annotations,
properties, predicates, and neighbors with provenance.

#### S2-EP5-ST3 Why explanation panel

Requirements: `UW-006`, `GE-011`, `AC-107`

Display conclusion, proof/justification graph and ordered textual steps,
supporting axioms/facts, source, reasoner/build identity, alternatives,
truncation, and unavailable-explanation outcomes.

### 7.9 Workstream 6: Sessions And Restore

#### S2-EP6-ST1 Implement renderer-neutral sessions

Requirements: `SE-001`, `SE-002`, `GQ-114`, `OP-009`

Persist visible resources/relationships, positions, expansions, filters,
selection, notes, active build, language, view mode, and schema version.

#### S2-EP6-ST2 Restore with compatibility checks

Report missing resources/predicates, incompatible build/profile changes, and
recoverable partial sessions. Never silently map missing IRIs.

### 7.10 Workstream 7: cosmos.gl Overview

#### S2-EP7-ST1 Implement overview GraphQL consumption

Requirements: `RC-003`, `RC-004`, `LS-003`

Consume only server-produced clusters/samples with weights, counts, aggregate
edges, provenance summary, method, truncation, and drill-down targets.

#### S2-EP7-ST2 Build production cosmos renderer adapter

Requirements: `RC-001`, `RC-007`, `RC-009`

Implement React lifecycle, typed-array conversion, GPU initialization,
selection, hover summaries, camera controls, cluster highlighting, level of
detail, cancellation, and cleanup.

#### S2-EP7-ST3 Add capability detection and fallback

Requirements: `RC-006`, `AC-111`

Detect WebGL 2/extensions, initialization failure, low-power policy, and device
limits. Fall back to aggregate table and bounded Cytoscape detail.

#### S2-EP7-ST4 Overview-to-detail transition

Requirements: `RC-005`, `AC-110`

Selecting a cluster/sample opens a fresh bounded GraphQL detail query and
preserves navigation context. It MUST NOT load all cluster members.

### 7.11 Workstream 8: Supported-App Testing

Requirements: `TC-008`, `TC-010`, `TC-011`

Add Playwright browser tests for every primary workflow, GPU fallback,
continuation, high-degree protection, collapse/history, session compatibility,
responsive layouts, and accessibility. Add repeated expansion/collapse memory
tests and Food ontology Tier M benchmarks.

### 7.12 Sprint 2 Deliverables

- Supported ontology explorer application.
- Metadata-driven discovery and semantic inspector.
- Production Cytoscape detail renderer.
- Production cosmos.gl overview renderer and fallback.
- Paths, comparison, explanations, consistency, and validation views.
- Complete visible-graph textual view.
- Session save/restore.
- Automated browser, accessibility, memory, and performance evidence.

### 7.13 Sprint 2 Exit Gate

Sprint 2 closes only when:

1. `AC-104` through `AC-111` and `AC-113` pass.
2. The 500-node/1,000-edge detail limit cannot be bypassed.
3. cosmos.gl receives only bounded aggregate/sample data.
4. GPU failure preserves search, schema browsing, textual access, and detail
   exploration.
5. Every visible relationship is represented in the textual table.
6. Desktop, tablet, mobile, keyboard, screen-reader, and reduced-motion flows
   pass the supported matrix.
7. The custom Food ontology meets approved API, browser, and memory targets.

### 7.14 Sprint 2 Risks

| Risk | Mitigation |
| --- | --- |
| cosmos overview is fast but not useful | User-test cluster/sample semantics and drill-down before visual polish |
| Main-thread Cytoscape layouts stall | Preserve hard budgets, precompute layouts, disable animation, support cancellation |
| GPU variability | Capability detection, target-device testing, textual and Cytoscape fallback |
| Session breaks after ontology swap | Build/profile/schema compatibility checks and explicit partial restore |
| Canvas excludes keyboard/screen readers | Textual equivalence and canonical application-owned selection |

### 7.15 Sprint 2 Suggested Pull Requests

1. Metadata navigation and profile-driven UI.
2. Semantic inspector and provenance.
3. Cytoscape expansion previews and collapse/history.
4. Whole-graph tables and accessibility.
5. Path, comparison, and explanation workflows.
6. Sessions and compatibility restore.
7. cosmos overview adapter and fallback.
8. E2E/accessibility/performance evidence.

## 8. Sprint 3: Ontodia Prototype

### 8.1 Sprint Goal

Produce an evidence-based Ontodia accept/reject decision and, only if safe,
demonstrate a separately deployed, bounded, GraphQL-backed ontology diagramming
prototype.

### 8.2 Requirement Coverage

- Renderer separation: `AR-105`, `AR-106`
- Ontodia: `RO-001` through `RO-010`
- Prototype disclosure: `AX-008`
- Shared session mapping where feasible: `SE-002`
- Shared/frontend feasibility tests: `TC-007`, `TC-009`
- Acceptance: `AC-112`

### 8.3 Entry Criteria

- Sprint 1 shared GraphQL and ontology metadata contracts are stable.
- Supported app dependencies remain isolated.
- LGPL review owner is identified.
- A fixed timebox and explicit rejection criteria are approved.
- Representative small and medium ontology fixtures are available.

Sprint 2 is not a strict implementation dependency, but its shared selection,
session, and conformance packages SHOULD be reused if stable.

### 8.4 Workstream 1: Mandatory Feasibility Gate

#### S3-EP1-ST1 Reproduce and audit upstream

Requirements: `RO-001` through `RO-003`, `TC-009`

Record:

- Upstream archive state and last maintained release/source.
- npm/source installation reproducibility.
- Node, TypeScript, bundler, CSS, asset, and browser requirements.
- React version expectations and legacy lifecycle/DOM APIs.
- Dependency vulnerability and transitive-license inventory.
- LGPL-2.1-or-later dynamic-linking/distribution obligations.
- Known browser/security policy limitations.

#### S3-EP1-ST2 Build compatibility spike

Tasks:

- Create an isolated workspace/package.
- Attempt a production build without modifying the supported app.
- Evaluate React compatibility through isolation, compatibility shell, iframe,
  or separate legacy root.
- Run a minimal static provider example.
- Measure bundle size, initialization, navigation, and memory on representative
  fixtures.
- Record required forks or patches.

#### S3-EP1-ST3 Publish go/no-go ADR

The ADR MUST choose one outcome:

1. Continue with bounded prototype using unmodified package.
2. Continue with an explicitly owned compatibility fork.
3. Reject implementation due to security, licensing, compatibility,
   maintenance, or cost.

No feature work proceeds before this decision.

### 8.5 Workstream 2: Isolated Prototype Build

This workstream executes only after a positive feasibility decision.

#### S3-EP2-ST1 Create separate deployable application

Requirements: `RO-004`, `NF-008`

Create an Ontodia-specific entry point/build with isolated dependencies,
security policy, styles, and release artifact. The normal supported bundle MUST
not import Ontodia.

#### S3-EP2-ST2 Add prototype status and limitations

Requirements: `RO-001`, `RO-002`, `AX-008`

The app MUST visibly disclose experimental status, archived upstream,
accessibility/responsive/scale limitations, supported ontology build, and link
to the supported Cytoscape/Cosmos application.

### 8.6 Workstream 3: GraphQL-Backed Ontodia DataProvider

#### S3-EP3-ST1 Map schema operations

Requirements: `RO-005`, `RO-006`

Implement Ontodia provider operations for:

- `classTree`
- `classInfo`
- `propertyInfo`
- `linkTypes`
- `linkTypesInfo`

All operations use bounded GraphQL. Browser RDF and direct SPARQL providers are
prohibited.

#### S3-EP3-ST2 Map element and navigation operations

Implement:

- `elementInfo`
- `linksInfo`
- `linkTypesOf` with counts
- `linkElements` with direction/filter/cursor limits
- `filter` using paginated GraphQL search

Map multilingual labels, types, typed properties, provenance, images, and
semantic metadata into Ontodia models without losing canonical IRIs.

#### S3-EP3-ST3 Bound and cancel provider requests

Apply server-owned page/fan-out limits, request cancellation, timeout handling,
stable errors, and explicit truncation. Ontodia MUST not trigger uncontrolled
schema or instance downloads during initialization.

### 8.7 Workstream 4: Prototype Features

#### S3-EP4-ST1 Class tree and search

Requirements: `RO-007`

Demonstrate class tree navigation, class/property/individual search, selection,
and adding bounded results to the diagram.

#### S3-EP4-ST2 Context-aware navigation

Demonstrate available link counts, incoming/outgoing relationship choices,
predicate filters, and bounded neighbor expansion.

#### S3-EP4-ST3 Ontology-aware templates

Display semantic kinds, labels, primary types, selected properties,
asserted/inferred state, and prototype limitation cues using Ontodia templates.

#### S3-EP4-ST4 Diagram persistence

Map Ontodia layout export/import into the shared session envelope where
feasible. Reject incompatible builds/entities explicitly.

#### S3-EP4-ST5 Selection synchronization

Synchronize diagram, search, class tree, and inspector selection through
canonical resource IRIs.

### 8.8 Workstream 5: Prototype Verification

Requirements: `TC-007`, `TC-009`, `AC-112`

Verify:

- Reproducible isolated build.
- No Ontodia dependency in supported app bundles.
- No direct RDF/SPARQL access.
- All provider requests bounded.
- Small and medium fixture behavior.
- Shared canonical selection/session compatibility where implemented.
- Known accessibility, responsive, performance, and security limitations.
- LGPL notices/source relinking obligations where applicable.

### 8.9 Sprint 3 Deliverables

Mandatory regardless of go/no-go:

- Feasibility, security, maintenance, and license dossier.
- Reproducible compatibility spike.
- GraphQL-to-Ontodia `DataProvider` mapping design.
- Go/no-go ADR.

After a positive decision:

- Separate prototype build.
- Bounded GraphQL-backed provider.
- Class tree, search, navigation, templates, selection, and diagram persistence
  demonstration.
- Representative-size and shared-conformance evidence.

### 8.10 Sprint 3 Exit Gate

Sprint 3 closes when either:

1. `AC-112` passes for an isolated bounded prototype, or
2. `RO-009` is satisfied by a rejection ADR with reproducible evidence and
   provider mapping.

Production adoption is explicitly outside this sprint and requires a separate
fork ownership, security response, accessibility, licensing, and release
decision (`RO-010`).

### 8.11 Sprint 3 Risks

| Risk | Mitigation |
| --- | --- |
| Archived upstream and legacy React | Separate build, strict timebox, reject if isolation is unsafe |
| Vulnerable abandoned dependencies | Audit before feature work; no exceptions hidden in supported app |
| LGPL obligations conflict with distribution | Legal/license review and relinkable separation |
| DataProvider initialization is unbounded | Implement GraphQL metadata/count pages and instrument every call |
| Prototype mistaken for supported product | Persistent experimental labeling and supported-app link |
| Fork becomes accidental permanent burden | Require explicit ownership ADR before any production claim |

### 8.12 Sprint 3 Suggested Pull Requests

1. Feasibility, dependency, security, and license report.
2. Isolated build spike and ADR.
3. GraphQL-backed DataProvider schema operations.
4. Element/navigation/filter provider operations.
5. Prototype templates, selection, and persistence.
6. Conformance evidence and limitation disclosure.

## 9. Sprint 4: Nice-To-Have And Non-Functional Enhancements

### 9.1 Sprint Goal

Add optional research productivity features and optimize measured quality
targets after the core and renderer implementations are safe, testable, and
operational.

Sprint 4 MUST NOT become a destination for unfinished Sprint 1 security,
reasoning, boundedness, rollback, or correctness requirements.

### 9.2 Requirement Coverage

Primary optional/optimization requirements:

- Command palette if deferred: `SD-006`
- Productivity: `GE-014`, `GE-015`
- Sharing/export: `SE-003` through `SE-005`
- Precomputation/caching: `LS-006`, `LS-007`
- Determinism refinement: `RS-013`
- Performance target tuning: `NF-001`, `NF-003` through `NF-005`, `NF-009`,
  `NF-010`
- Remaining SHOULD requirements in `OP`, `RC`, `OR`, `AX`, and `TC-011`

### 9.3 Entry Criteria

- Sprint 1 production-safety gates pass.
- Sprint 2 supported application is complete.
- Sprint 3 has an accepted prototype or rejection ADR.
- Production telemetry and benchmark harnesses exist.
- Custom Food ontology and target deployment hardware are available.

### 9.4 Workstream 1: Research Productivity

#### S4-EP1-ST1 Query history and bookmarks

Requirements: `GE-014`

Add authorized history and bookmarks for searches, resources, expansions,
paths, comparisons, explanations, and saved filters. Define retention and
privacy behavior.

#### S4-EP1-ST2 Command palette refinements

Requirements: `SD-006`

Add searchable commands, recent items, shortcuts, ontology navigation, and
context-aware actions if not fully delivered in Sprint 2.

#### S4-EP1-ST3 Ontology build diff

Requirements: `GE-015`

Compare resources, axioms, labels, annotations, types, relationships,
validation findings, and inferred facts between two builds with bounded,
paginated summaries.

### 9.5 Workstream 2: Share And Export

#### S4-EP2-ST1 Shareable deep links

Requirements: `SE-003`

Add authorized links to ontology build, selected resource, view mode, and saved
session without placing sensitive graph content in the URL.

#### S4-EP2-ST2 Data export

Requirements: `SE-004`

Export bounded visible/session subgraphs as JSON, CSV, and GraphML with build,
profile, provenance, filter, truncation, and authorization metadata.

#### S4-EP2-ST3 Image export

Requirements: `SE-005`

Export supported detail views as PNG/SVG where technically possible. Clearly
state visible-only scope and handle oversized exports asynchronously or reject
them.

### 9.6 Workstream 3: Caching And Precomputation

#### S4-EP3-ST1 Add build-keyed caches

Requirements: `LS-007`

Cache profile metadata, resource summaries, class trees, predicate metadata,
counts, common bounded expansions, and explanations by build plus query
fingerprint. Invalidate by immutable build identity.

#### S4-EP3-ST2 Add ingestion-time indexes/statistics

Requirements: `LS-006`

Precompute hierarchy indexes, predicate statistics, semantic-kind counts,
high-degree resource counts, and overview cluster/sample artifacts where
benchmarks justify them.

#### S4-EP3-ST3 Optimize frontend data loading

Reduce initial bundle size, preserve renderer code splitting, prefetch bounded
metadata, virtualize long trees/tables, and eliminate redundant graph-state
conversion.

### 9.7 Workstream 4: Capacity And Reliability Tuning

#### S4-EP4-ST1 Establish statistical performance baselines

Requirements: `NF-001`, `NF-003`, `NF-004`, `TC-011`

Run repeated cold/warm API, concurrency, ingestion, reasoning, renderer, memory,
and sustained-interaction benchmarks on S/M/L tiers and target hardware.

#### S4-EP4-ST2 Tune custom Food ontology performance

Measure real class/axiom complexity, high-degree nodes, text search,
explanations, paths, overview clustering, and store growth. Adjust caches,
indexes, limits, and asynchronous job thresholds only from evidence.

#### S4-EP4-ST3 Define service objectives

Requirements: `NF-005`, `NF-007`, `NF-010`

Finalize API latency, ingestion/reasoning budgets, browser-memory ceiling,
availability, recovery time, recovery point, retention, and capacity targets.

#### S4-EP4-ST4 Soak and leak testing

Run repeated expansion/collapse, ontology switching, path/explanation jobs,
session restore, export, GPU fallback, and long-lived API/frontend tests. Verify
no unbounded memory, handle, process, or disk growth.

### 9.8 Workstream 5: Final Maintenance And Migration Cleanup

#### S4-EP5-ST1 Dependency and license maintenance review

Recheck reasoner, PyOxigraph, Cytoscape, cosmos.gl, Ontodia prototype, parsers,
and export libraries. Document upgrade ownership and security response.

#### S4-EP5-ST2 Final GraphDB archival

If GraphDB could not be removed earlier, remove runtime construction and HTTPX
dependencies after store-version rollback and soak gates pass. Archive parity
fixtures, endpoint schemas, and migration evidence.

#### S4-EP5-ST3 Documentation and training

Finalize operator, ontology package author, researcher, accessibility,
troubleshooting, backup/recovery, and incident runbooks.

### 9.9 Sprint 4 Deliverables

- Query history, bookmarks, and command refinements.
- Ontology build diff.
- Authorized deep links.
- Bounded data/image exports.
- Build-keyed caching and precomputation.
- Custom Food ontology capacity report.
- Finalized SLO, reasoning, memory, availability, and recovery targets.
- Soak/leak evidence.
- Dependency/license ownership and final migration archive.

### 9.10 Sprint 4 Exit Gate

Sprint 4 closes when:

1. Optional features do not bypass authorization, auditing, response limits, or
   ontology build compatibility.
2. Exports cannot disclose unauthorized data or imply whole-ontology coverage
   when only a bounded view is exported.
3. Caching does not alter semantic results and is invalidated by build identity.
4. Repeated workflows show no unbounded browser, API, reasoner, or disk growth.
5. S/M/L benchmarks and target Food ontology results are documented.
6. Availability, RTO/RPO, memory, latency, and reasoning targets are approved.
7. Remaining migration-only dependencies are removed or formally retained with
   ownership.

### 9.11 Sprint 4 Risks

| Risk | Mitigation |
| --- | --- |
| Cache returns stale ontology data | Immutable build-keyed cache namespace |
| Export amplifies data access | Server-side authorization, limits, async jobs, audit, retention |
| Deep links leak graph data | Store references/session IDs, not sensitive payloads, in URLs |
| Premature optimization | Require benchmark evidence before indexes or architecture changes |
| Local hardware misrepresents deployment | Repeat on target integrated/discrete GPU and server hardware |
| Nice-to-have work hides incomplete core | Sprint 1/2 exit checklist remains mandatory and separately audited |

### 9.12 Sprint 4 Suggested Pull Requests

1. History, bookmarks, and command palette.
2. Ontology build diff.
3. Deep links and bounded exports.
4. Build-keyed caches and ingestion statistics.
5. Capacity and soak benchmark suite.
6. SLO/recovery and final migration documentation.

## 10. Cross-Sprint Dependency Map

```text
Ontology profile + secure ingestion
              |
Reasoner provider + provenance + consistency
              |
Generic repository/domain/GraphQL contracts
              |
GraphQL limits + auth + operations + shared frontend contracts
              |
      Sprint 1 Exit Gate
          /          \
Supported app       Ontodia feasibility
Sprint 2            Sprint 3
          \          /
       Stable telemetry and product workflows
                      |
         Sprint 4 optimization and extras
```

Key dependencies:

- Full reasoning depends on pinned imports and ontology package identity.
- Explanation UI depends on reasoner-generated proof artifacts and provenance.
- Dynamic frontend navigation depends on profile/schema GraphQL metadata.
- Ontodia `DataProvider` depends on class/property/element/link APIs from Sprint
  1, not on direct SPARQL.
- cosmos overview depends on server-side aggregate/sample contracts.
- Exports, sharing, and caches depend on Sprint 1 authorization, audit, limits,
  and immutable build identity.

## 11. Requirements Allocation Summary

| Requirement area | Sprint 1 | Sprint 2 | Sprint 3 | Sprint 4 |
| --- | --- | --- | --- | --- |
| Architecture and ontology profiles | Primary | Consume | Consume | Refine |
| Full OWL 2 DL reasoning | Primary | Explain/display | Consume where needed | Tune/diff |
| Generic GraphQL/repository APIs | Primary | Consume | Adapt to Ontodia | Extend optional APIs |
| Security and operational safety | Primary | Enforce in UI | Enforce in prototype | Tune/maintain |
| Cytoscape detail | Contracts only | Primary | None | Optimize |
| cosmos overview | API contract | Primary | None | Optimize |
| Ontodia | Provider contract | None | Primary prototype | Maintenance decision |
| Accessibility foundations | Shared contracts | Primary supported app | Disclose/test subset | Refine |
| Save/restore | Contract and auth | Primary | Map if feasible | Extend sharing/export |
| History, build diff, exports | Foundations only | Optional baseline | None | Primary |
| Performance/capacity | Safety baselines | Supported renderer gates | Prototype evidence | Statistical tuning |

## 12. Work That Must Not Move To Sprint 4

The following are prerequisites or correctness requirements, not polish:

- Authentication and authorization boundaries.
- GraphQL complexity, timeout, cancellation, and rate controls.
- Server-side traversal/path/explanation/response limits.
- Import allowlists and parser/path/archive hardening.
- Reasoner isolation and consistency promotion gates.
- Asserted/inferred provenance.
- Stable errors.
- Atomic promotion, backup, restore, and rollback.
- Audit and retention policy foundations.
- Readiness and process model.
- Renderer-neutral identity and state.
- Separate frontend build isolation.
- Visible graph budgets and GPU fallback.
- Keyboard/textual equivalents for supported workflows.

Sprint 4 may tune targets or add optional features, but it MUST NOT be used to
defer release-safety obligations.

## 13. Testing Matrix By Sprint

| Test class | Sprint 1 | Sprint 2 | Sprint 3 | Sprint 4 |
| --- | --- | --- | --- | --- |
| Unit | Profiles, terms, reasoner adapters, limits, errors | UI state, render adapters, sessions | Provider mappings | Caches, exports, diffs |
| Contract | Repository, reasoner, GraphQL, auth | Renderer and shared frontend | Ontodia DataProvider | Export/cache contracts |
| Integration | Ingestion, imports, reasoning, recovery | GraphQL plus both supported renderers | Isolated Ontodia build/provider | Backup, export, capacity jobs |
| E2E | Operator build/promote/rollback | All supported user workflows | Prototype smoke | Sharing/export/long-run workflows |
| Security | Parser, imports, reasoner, GraphQL | Client auth/error/fallback | Dependency and browser audit | Export/deep-link/retention review |
| Accessibility | Shared models/contracts | Full supported matrix | Known-limit audit | Regression and polish |
| Performance | Backend/reasoner safety baselines | Detail/overview gates | Representative prototype size | Statistical S/M/L capacity |

## 14. Release And Branch Strategy

Recommended delivery structure:

- Keep `feat/owl-store-migration` as the integration branch until Sprint 1
  migration foundations are complete.
- Create short-lived child branches per epic using conventional names, for
  example `feat/ontology-profile`, `feat/reasoning-provider`, and
  `feat/cosmos-overview`.
- Merge focused PRs into the integration branch after their local exit gate.
- Tag internal milestones after each sprint exit gate.
- Do not merge Ontodia dependencies into the supported frontend package.
- Do not remove GraphDB parity/rollback code until Sprint 1 operational rollback
  no longer relies on it and soak criteria pass.

Each PR MUST include:

- Requirement IDs.
- Behavioral and schema changes.
- Data/store migration impact.
- Security and boundedness analysis.
- Tests and benchmark evidence.
- Rollback instructions.
- Documentation updates.

## 15. Sprint Review Checklist

At each sprint review, verify:

- Requirement traceability is current.
- All sprint exit criteria pass.
- No unbounded operation was introduced.
- No backend or renderer-specific type leaked across its port.
- Ontology build identity and provenance remain visible.
- Public compatibility changes are documented.
- Security, accessibility, and recovery evidence exists where required.
- Generated stores, secrets, and local environment artifacts are not committed.
- Unrelated worktree files are not staged.

## 16. Final Product Completion

After Sprint 4, the product is complete only if the Definition of Done in the
[product specification](ontology-graph-explorer-requirements.md#26-definition-of-done)
passes. Sprint completion alone does not override unresolved MUST requirements,
security findings, reasoner conformance gaps, or production readiness review.