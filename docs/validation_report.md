# EcoAdvisor validation report

## Scope

Validation covers data loading, API schema validation, compatibility gating, TOPSIS ordering, score bounds, recommendation persistence, history retrieval, route-manifest serving, and the Random Forest training workflow.

## Case studies

The application is seeded for Tomato, Milk, Apple, Bread, and Juice scenarios. Results should be described as computationally consistent with the current assumptions unless compared against a cited literature practice. The report must record agreement, difference, and possible reasons for each case study.

## Model boundary

The training script reports MAE, RMSE, and R² on a held-out split of synthetic rows. These metrics demonstrate the computational workflow only; they do not establish external validity or experimental accuracy.

## Acceptance checks

- All score outputs remain in documented ranges.
- Invalid temperatures and missing/unknown food IDs return clear errors.
- Ineligible packaging does not outrank eligible packaging through sustainability alone.
- Repeated identical requests produce deterministic ranking for the same data and code version.
- Every important dataset record carries a provenance status.
