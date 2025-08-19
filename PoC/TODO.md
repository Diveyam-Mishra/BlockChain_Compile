# CompliLedger PoC – TODO (Next Planned Tasks)

Last updated: 2025-08-15 02:08 IST

## High Priority
- [ ] Frontend wiring (Next.js)
  - [ ] Company portal: upload artifact → show status, CIDs, explorer links
  - [ ] Auditor portal: search by artifact hash → show on-chain status + OSCAL links
  - [ ] Controls dropdowns and recommendations via `/api/v1/controls/*`
  - [ ] Pera Wallet SDK integration (view addresses, explorer links; prep for future tx signing)
- [ ] Backend API completion (FastAPI)
  - [ ] Upload/submit endpoints for artifacts
  - [ ] Status lookup: `/api/v1/verification/status/{artifact_hash}`
  - [ ] Auditor routes finalization and request models
  - [ ] AuthN/AuthZ and OpenAPI docs

## Blockchain (Optional Hardening)
- [ ] Oracle inner call: upgrade PyTeal/SDK and redeploy oracle to pass box references in inner app call
- [ ] Keep IDs in sync across `.env` and both `contract_config.json` files after any redeploy

## Resilience & QA
- [ ] Add unit tests for AI and IPFS services (beyond current integration test)
- [ ] Improve error handling/logging around AI partial responses and IPFS retries
- [ ] Health checks for API and external dependencies

## Documentation
- [ ] Update README with frontend run instructions and new API surface
- [ ] Record new on-chain tx links and CIDs in `Test_Results.md`

## Done (Most Recent)
- [x] Direct registry update path (EOA oracle) in `contract_integration.py`
- [x] Auto-link oracle→registry and set registry oracle_address
- [x] Auto-fund registry app address and add box existence guard
- [x] Confirm IDs synced: REGISTRY_APP_ID=744263858, ORACLE_APP_ID=744263859
