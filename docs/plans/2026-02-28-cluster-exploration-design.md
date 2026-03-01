# Cluster Exploration Enhancement Design

Date: 2026-02-28
Status: Draft for implementation

## 1. Goal
Turn clustering into a primary exploration workflow, not just a label list. Users should move from cluster overview -> cluster detail -> insight discovery through interactive visuals, term controls, and guided next-step links.

## 2. Current Gap
Current cluster representation is mostly:
- cluster id
- top terms
- linked episodes

This is insufficient for discovery because it lacks context, comparison, explainability, and playful interaction.

## 3. Two-Axis Delivery
## Axis A (pragmatic, immediate value)
Make existing clusters useful with concrete detail pages and actionable interactions.

## Axis B (vision)
Add exploration mechanics that create "what to inspect next" behavior and non-trivial insight pathways.

## 4. Backend/Export Requirements (sqlite -> dataset)
Required precomputed structures:
1. `cluster_stats` per cluster:
- episode_count
- unique_podcast_count
- dominant_podcast_share
- median_pub_year
- temporal_span_years
- mean_span_confidence
- geo_dispersion (if places exist)

2. `cluster_term_metrics`:
- term tf-idf in cluster
- global support
- lift vs global
- "drop-impact" score (change in cluster coherence if term removed)

3. `cluster_correlations`:
- pairwise cluster similarity (Jaccard on episodes, cosine on term vectors)
- top bridge terms between clusters

4. `cluster_entity_stats` and `cluster_place_stats`:
- top entities/places with lift and confidence-weighted counts.

5. `cluster_timeline_histogram`:
- year bins of mention density.

6. `cluster_next_steps` candidates:
- machine-generated suggestions from strongest anomalies/correlations.

Python impact:
- Extend export models in `src/podcast_atlas/models.py`.
- Extend exporter in `src/podcast_atlas/static_export.py`.
- Add computation helpers under `src/podcast_atlas/export/`.

## 5. UX Information Architecture
## 5.1 New pages/views
1. `Cluster Index` view
- cards/table of all clusters
- sortable by size, cohesion proxy, novelty, temporal spread
- mini-sparkline and top terms

2. `Cluster Detail` view
- hero summary + confidence badge
- terms word cloud + ranked table
- timeline distribution chart
- geography mini-map
- episodes table linked to episode detail tabs
- "next investigations" panel

3. `Cluster Compare` drawer (optional phase 2)
- side-by-side stats and differential terms.

## 5.2 Interaction rules
- Every major chart element is clickable and updates filters.
- Breadcrumb always shows active scope.
- Clear reset controls at each drill-down layer.
- Avoid dead-end views: each panel must offer at least one "next action".

## 6. Completion Properties (must hold)
1. User can open any cluster and understand in <30s:
- what it is about
- how broad/narrow it is
- what makes it distinct.
2. Clicking a term visibly re-scopes episodes and updates charts.
3. Cluster detail provides at least 3 distinct visual modalities (term, time, relation/map).
4. At least one guided suggestion is generated and navigable for every cluster with >= 10 episodes.
5. Story-driven interactions (section 8) can all be executed without hidden admin controls.

## 7. Guarantee Matrix
- If `cluster_term_metrics` includes lift + drop-impact and UI renders both, then users can evaluate term importance beyond raw frequency.
- If timeline + geo + episode table are synchronized by shared filters, then drill-down remains coherent and intuitive.
- If `cluster_next_steps` are precomputed from anomalies and links are first-class UI elements, then exploration pathing is explicit rather than accidental.

## 8. Vision Stories (8)

## Story 1: "Why is this cluster huge?"
Narrative:
User clicks the 3rd-largest cluster to verify whether size is thematic coherence or noisy aggregation.

Required UI/features:
- cluster index sortable table
- size vs cohesion scatter
- detail hero with cohesion proxy + dominant terms

Page implications:
- cluster index must show comparative metrics, not only term snippets.

TODO:
1. compute cohesion proxy from term concentration.
2. precompute cluster size + cohesion in export.
3. render scatter with clickable points.

## Story 2: "Term click narrows meaning"
Narrative:
In word cloud, user clicks a medium-sized term and sees episode list drop from 120 to 22, revealing a specific historical sub-theme.

Required UI/features:
- clickable word cloud
- active term pills
- synchronized episodes table + timeline

Page implications:
- local cluster filter state and shared data pipeline.

TODO:
1. expose per-term episode membership index.
2. wire term-click to scoped selectors.
3. add clear/reset controls.

## Story 3: "Temporal anomaly hunt"
Narrative:
User notices a spike in 1918 bin and explores only spike episodes; discovers narrators and entities shift sharply.

Required UI/features:
- timeline histogram with brush
- side stats delta panel (selected bin vs cluster baseline)

Page implications:
- timeline brush state must update all subpanels.

TODO:
1. precompute year-bin counts per cluster.
2. implement brush-driven filtering.
3. compute delta metrics in client selector.

## Story 4: "Geography as explanation"
Narrative:
User sees cluster map points concentrated in two regions; selecting one region shows terms diverge.

Required UI/features:
- cluster map with lasso/region click
- region-aware term table and episode subset

Page implications:
- map interaction must emit place-scope filter shared by term/timeline panels.

TODO:
1. precompute cluster place stats with coordinates.
2. add map filter channel.
3. compute term lift within selected region.

## Story 5: "Drop-impact sanity check"
Narrative:
User toggles "simulate removing term" for top terms and sees one term barely changes coherence while another collapses it.

Required UI/features:
- term table with drop-impact column
- simulation toggle
- coherence gauge update

Page implications:
- needs deterministic lightweight simulation from precomputed values.

TODO:
1. export drop-impact scores.
2. build coherence gauge component.
3. implement simulated ranking reorder.

## Story 6: "Cross-cluster bridge discovery"
Narrative:
User opens link graph from cluster detail and finds a bridge to a smaller adjacent cluster via 2 entities.

Required UI/features:
- nodes/edges graph chart
- edge tooltip with shared episodes/entities
- click-through to neighbor cluster

Page implications:
- relation graph should be embedded under "what next".

TODO:
1. precompute cluster correlation edges.
2. add graph component and lazy loading.
3. deep link to target cluster detail.

## Story 7: "Guided exploration suggestions"
Narrative:
User follows "Investigate temporal outlier term X" suggestion and lands in a pre-filtered state that exposes non-trivial contrast.

Required UI/features:
- suggested actions list (cards)
- one-click apply of compound filters

Page implications:
- saved filter state serialization in URL/app state.

TODO:
1. generate next-step templates in exporter.
2. encode suggested filter payload.
3. implement apply + breadcrumb trail.

## Story 8: "From cluster to publishable insight"
Narrative:
User builds a scoped view (terms + time window + region), then exports a snapshot table/chart showing a specific correlation.

Required UI/features:
- export current view config
- table/chart download button
- visible query spec summary

Page implications:
- cluster detail must retain explicit query specification.

TODO:
1. add state serializer for cluster scopes.
2. add CSV + PNG export actions.
3. render query-spec badge with reproducible parameters.

## 9. UX Cleanliness Enforcement
- One primary action per panel header.
- Every filter has visible state and reset affordance.
- No hidden keyboard-only critical controls.
- Color semantics fixed:
  - neutral for baseline
  - accent for active selection
  - caution for narrowing filters.
- Empty states must suggest a next action (never blank dead-ends).

## 10. Delivery Checklist
1. Export schema extended with cluster stats, term metrics, correlations, next-steps.
2. Cluster index + detail views implemented.
3. Clickable term cloud + synchronized table/timeline/map filters.
4. Drop-impact and lift displayed and sortable.
5. Cluster relation graph and guided next-step links implemented.
6. URL/state persistence for cluster drill-down.
7. Tests:
- export metric integrity tests (python)
- selector sync tests (frontend)
- interaction integration tests (frontend).
