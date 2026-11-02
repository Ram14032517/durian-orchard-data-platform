# English interface and calmer interaction — 2 November 2026

## What changed

- The React dashboard, Classic workspace, sign-in/sign-out screens, controls, accessible labels, validation prompts and source/uncertainty explanations now have English presentation text. Dates use English formatting and CE years; Bangkok time and API date values are unchanged.
- A single click switches between **Mode: Light** and **Mode: Dark**. The label describes the actual appearance, not an unresolved “System” preference. Appearance persists across reloads and synchronizes between tabs of the same origin. Before an explicit choice, an existing system preference still follows the OS. Blocked browser storage does not prevent in-page switching.
- Page entry, sidebar resizing, buttons and colour changes use short, restrained transitions. Map navigation uses the existing cancellable motion controller, finer wheel-zoom steps and coalesced resizing. New navigation interrupts the previous flight. The redundant 1.5-second map-count poll is removed; the registry layer already updates its own filtered counts. Reduced-motion preferences disable decorative movement.
- Login shares the same appearance preference without changing authentication, sessions, CSRF or account ownership rules. The bounded deployment package includes only the specific presentation assets it needs, not the entire source/data tree.

## Language without changing evidence

`web/i18n/en.json` is the reviewed presentation catalogue. `web/i18n/english.js` provides lookup and safe text/attribute translation. The build uses `web/react/src/i18n/jsx-runtime.js` to translate before React reconciliation. Only Classic and Leaflet-owned DOM islands use a text-node observer; the React-owned body is never mutated externally.

Form values, option identities, identifiers, source URLs, coordinates, stored observations and API payload keys stay unchanged. Implicit option values are pinned before their visible labels are translated. Inputs and textareas retain user-entered values. Unknown source-specific proper names remain in their original spelling rather than being guessed, and original documents/images are not rewritten. Consequently Thai district/subdistrict/soil-series names, personal notes and original reference documents may still contain Thai. This is an English interface, not a translated replacement dataset.

Source wording problems remain explicit: ambiguous or misspelled soil-description categories are labelled as such rather than silently converted into numeric pH targets. The catalogue translates existing statements; it adds no new agronomic thresholds or disease diagnoses.

## What did not change

- IoT ingest, sensor measurements, private Supabase access and account-scoped harvest records.
- GAP registry records, spatial geometries, workbook contents and the embedded display-data snapshot.
- Production models, training inputs, saved experiment scores and audit results. No production retraining or accuracy claim is part of this update.
- Missing is still missing, measured zero stays zero, stale data stay labelled, and forecasts remain distinct from sensor readings and confirmed disease.
- Public release remains **HOLD**. Local changes are not a cloud deployment, and no additional GIS/private-data access is granted.

## Verification

- JavaScript regression suite: 113 passing tests, including production JSX translation, retained form values, safe DOM-island updates, sensor missing/zero handling, source caveats and map cleanup.
- Python regression suite: 525 cases discovered; 474 counted as run; zero failures/errors. Ten individual cases and four fixture-dependent classes are skipped (61 cases in total), as the optional private archives / live Postgres test environment are absent. This is not evidence that those unavailable integrations were tested live.
- `node tools/audit_ui_english.mjs --check` checks static interface strings, known API diagnostics and displayed phenology, soil-description and GAP-source vocabulary. It deliberately excludes original proper names, offline report text and user data; it is not an assertion that every byte in source records is English.
- Real-browser checks cover actual theme switching, reload persistence, English labels, source explanations and expanded-map layout. These checks identified and fixed a legacy input accessibility-label gap, a login theme-host selector mismatch and an animation containing-block issue affecting full-window maps. Browser checks do not certify a particular animation frame rate.
- Raw-byte comparisons against the starting Git revision confirm 27 model/training/input files unchanged. Both entry pages retain exactly the same embedded DATA payload, and the GAP workbook SHA-256 remains `ef3d25feca214050e5e190d0f6d7f1fcc6e09e704d0bdb7b0205b8cb6c39af6c`.
- This Mac still reports an unavailable local orchard snapshot; no readings or live cloud connection are fabricated to make the preview look complete.

## Rebuild / read

From the repository root:

```sh
node tools/build_orchard_react.mjs
.build/national-analysis-venv/bin/python -B tools/build_unified_orchard_map.py --reuse-bundled-data
node tools/audit_ui_english.mjs --check
node --test tests/*.js tests/*.cjs
```

The first command creates `orchard_app.js`, `orchard_app.css` and the standalone Classic/login `orchard_english.js`. The second rebuilds both entry HTML files from the **existing** display-data snapshot. Do not edit generated bundles directly.

The existing [dataflow document](../architecture/DATAFLOW_TH.md) remains the data-source reference. This update changes presentation, not that dataflow.

Delivery branch: `codex/organize-project`. A Git push publishes this update to that branch; it does not deploy the cloud website or grant additional data access.
