# EcoAdvisor methodology

## Shelf-life model

The project contains a reproducible Random Forest Regressor pipeline. Because the initial project does not have a sufficiently large measured food–package shelf-life dataset, the first training set is generated from curated profiles and documented rules. It is labelled synthetic. The fallback estimate in the live service is intentionally transparent and returns a warning.

## Compatibility

Barrier fit is calculated by comparing the food requirement with the packaging performance on a normalized 0–100 scale. Oxygen, moisture, light, mechanical, acidity, moisture, oil, liquid, and temperature considerations contribute to the eligibility score. Severe incompatibilities are excluded before multi-criteria ranking.

## TOPSIS

Eligible alternatives form a decision matrix. Columns are vector-normalized, multiplied by preference weights, compared with positive and negative ideal solutions, and scored by closeness to the positive ideal. Benefits include shelf-life suitability, barrier fit, recycling, biodegradability, and circularity; burdens such as relative cost are inverted as cost criteria.

## Sustainability Score

The EcoAdvisor Sustainability Score is a transparent comparative indicator composed of environmental-impact proxy, carbon-burden proxy, recyclability, biodegradability, compostability, and end-of-life suitability. It must not be called a certified carbon score or a complete LCA.

## Circularity Score

The Circularity Score combines recycled content, recyclability, reusability, material recovery potential, material circularity, and compostability. The score is infrastructure-dependent and cannot establish that a package will be recycled or composted in a particular location.

## Research integrity

Numerical values have data-status labels. Synthetic rows are never described as experiments. Literature-derived values must preserve source, unit, condition, and confidence. The system uses phrases such as “aims to support sustainable decision-making” and “comparative assessment” rather than claiming environmental or food-waste reductions.
