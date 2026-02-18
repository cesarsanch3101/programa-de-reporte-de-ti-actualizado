# SPEC.md - IT Support Reporting Application Refactor

## 1. Goal
Refactor the existing IT Support Reporting application to comply with high-level architectural standards, including SOLID principles, AI-DLC methodology, "Design-First" backend, and premium frontend aesthetics.

## 2. User Constraints (Clarified)
- **Data Preservation**: MUST preserve existing records in `soportes.db` through migration.
- **Infrastructure**: No external infrastructure. CI/CD "Smart Fail" and SBOM will be implemented as local check-scripts (Bash/Python).
- **Authentication**: Keep local in SQLite, but refactor to support better RBAC and modern security (OWASP).

## 3. Architectural Vision
- **Backend**: Move from a monolithic Flask app to a Clean Architecture or Hexagonal Architecture. Separation of Layers: Presentation (Flask), Application (Use Cases), Domain (Models), Infrastructure (SQLite/Mail).
- **Contracts**: Define OpenAPI specification for the internal endpoints.
- **Database**: Migrate from Sequential IDs to UUIDs. Implement properly indexed and normalized schema with reversible DDL migrations.
- **Frontend**: Implement a robust state management pattern (Loading, Error, Success, Data Changes) for all async actions. Modernize typography, color variables, and micro-animations.

## 4. High-Level Requirements

### Phase 1: Planning & Clarification
- [x] Generate 2-3 critical business questions.
- [ ] Define OpenAPI contracts.
- [ ] Design the new normalized schema (3NF) with UUIDs and composite indexes.
- [ ] Design the migration strategy (Legacy IDs -> UUID Mapping).

### Phase 2: Backend & Database (Design-First)
- [ ] Implement a repository pattern to decouple DB from routes.
- [ ] Create migration scripts (UP/DOWN) using custom transacted DDL.
- [ ] Apply SOLID & DRY principles.

### Phase 3: Frontend & Aesthetics
- [ ] Refactor Jinja2 templates to use a modern CSS design system.
- [ ] Implement explicit state handling for AJAX operations.
- [ ] Add micro-animations (transitions, hover effects).

### Phase 4: Quality & Security
- [ ] Implement Unit Tests (Pytest) following AAA pattern.
- [ ] Implement POM-based E2E tests (Playwright/Cypress).
- [ ] Implement local Local "Smart Fail" script for CI simulation.
- [ ] Implement SBOM generation script.

## 5. Constraint Checklist
- [x] Preserve Existing Data.
- [x] Local Infrastructure only.
- [ ] SOLID & DRY Principles.
- [ ] API Design-First (OpenAPI).
- [ ] UUIDs for Primary Keys.
- [ ] Reversible Migrations.
- [ ] Quad-State Management on Frontend.
- [ ] Pattern: Arrange, Act, Assert.
- [ ] POM for E2E.
- [ ] OWASP Guardrails.
- [ ] Smart Fail (Local Simulation).
- [ ] SBOM updates.
