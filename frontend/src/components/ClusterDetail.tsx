import { useEffect, useMemo, useState } from "react";
import type { Dataset } from "../types";
import GraphIntervalSlider from "./GraphIntervalSlider";
import EpisodesTable from "./EpisodesTable";

function yearFromIso(iso?: string): number | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.getUTCFullYear();
}

export default function ClusterDetail(props: {
  dataset: Dataset;
  clusterId: number;
  selectedEpisodeId: number | null;
  onSelectEpisode: (episodeId: number) => void;
  onSelectCluster: (clusterId: number) => void;
  initialTerm?: string;
  initialYearRange?: [number, number];
  onScopeChange?: (scope: { term: string; yearRange: [number, number] }) => void;
}) {
  const cluster = useMemo(
    () => props.dataset.clusters.find((c) => c.cluster.id === props.clusterId) ?? null,
    [props.dataset.clusters, props.clusterId],
  );

  const memberEpisodeIds = useMemo(() => {
    const ids = new Set<number>();
    for (const [episodeId, cid] of Object.entries(props.dataset.episode_clusters)) {
      if (cid === props.clusterId) ids.add(Number(episodeId));
    }
    return ids;
  }, [props.dataset.episode_clusters, props.clusterId]);

  const episodes = useMemo(
    () => props.dataset.episodes.filter((e) => memberEpisodeIds.has(e.id)),
    [props.dataset.episodes, memberEpisodeIds],
  );

  const spans = useMemo(
    () => props.dataset.spans.filter((s) => memberEpisodeIds.has(s.episode_id)),
    [props.dataset.spans, memberEpisodeIds],
  );

  const yearBounds = useMemo<[number, number]>(() => {
    const years: number[] = [];
    for (const s of spans) {
      const a = yearFromIso(s.start_iso);
      const b = yearFromIso(s.end_iso);
      if (a != null) years.push(a);
      if (b != null) years.push(b);
    }
    for (const e of episodes) {
      const y = yearFromIso(e.pub_date_iso);
      if (y != null) years.push(y);
    }
    if (years.length === 0) return [-500, new Date().getUTCFullYear()];
    return [Math.min(...years), Math.max(...years)];
  }, [episodes, spans]);

  const [yearRange, setYearRange] = useState<[number, number]>(
    props.initialYearRange ?? yearBounds,
  );
  const [activeTerm, setActiveTerm] = useState<string>(props.initialTerm ?? "");
  const [termSort, setTermSort] = useState<"tfidf" | "lift" | "dropImpact">("tfidf");
  const [entitySort, setEntitySort] = useState<"lift" | "count">("lift");
  const [placeSort, setPlaceSort] = useState<"lift" | "count">("lift");

  useEffect(() => {
    if (props.initialYearRange) setYearRange(props.initialYearRange);
    else setYearRange(yearBounds);
    setActiveTerm(props.initialTerm ?? "");
  }, [props.clusterId, yearBounds, props.initialTerm, props.initialYearRange]);

  useEffect(() => {
    props.onScopeChange?.({
      term: activeTerm,
      yearRange,
    });
  }, [activeTerm, yearRange, props.onScopeChange]);

  const termMetrics = useMemo(() => {
    return (props.dataset.cluster_term_metrics ?? [])
      .filter((m) => m.cluster_id === props.clusterId)
      .slice()
      .sort((a, b) => b.tfidf - a.tfidf)
      .slice(0, 40);
  }, [props.dataset.cluster_term_metrics, props.clusterId]);

  const terms = useMemo(() => {
    if (termMetrics.length > 0) {
      return termMetrics.map((m) => ({
        phrase: m.term,
        weight: m.tfidf,
        support: m.support,
        lift: m.lift,
        dropImpact: m.drop_impact,
      }));
    }
    return (cluster?.top_keywords ?? []).map((k) => ({
      phrase: k.phrase,
      weight: k.score,
      support: 0,
      lift: 0,
      dropImpact: 0,
    }));
  }, [cluster?.top_keywords, termMetrics]);

  const sortedTerms = useMemo(() => {
    const rows = terms.slice();
    rows.sort((a, b) => {
      if (termSort === "lift") return b.lift - a.lift || b.weight - a.weight;
      if (termSort === "dropImpact") return b.dropImpact - a.dropImpact || b.weight - a.weight;
      return b.weight - a.weight || b.lift - a.lift;
    });
    return rows;
  }, [termSort, terms]);

  const clusterStats = useMemo(
    () => (props.dataset.cluster_stats ?? []).find((s) => s.cluster_id === props.clusterId) ?? null,
    [props.dataset.cluster_stats, props.clusterId],
  );

  const correlations = useMemo(() => {
    const rows = (props.dataset.cluster_correlations ?? []).filter(
      (r) => r.cluster_a === props.clusterId || r.cluster_b === props.clusterId,
    );
    return rows
      .map((r) => ({ ...r, otherClusterId: r.cluster_a === props.clusterId ? r.cluster_b : r.cluster_a }))
      .sort((a, b) => b.jaccard_episode_overlap - a.jaccard_episode_overlap)
      .slice(0, 10);
  }, [props.dataset.cluster_correlations, props.clusterId]);

  const nextSteps = useMemo(
    () => (props.dataset.cluster_next_steps ?? []).filter((s) => s.cluster_id === props.clusterId),
    [props.dataset.cluster_next_steps, props.clusterId],
  );

  const timelineBins = useMemo(() => {
    return (props.dataset.cluster_timeline_histogram ?? [])
      .filter((b) => b.cluster_id === props.clusterId)
      .slice()
      .sort((a, b) => a.start_year - b.start_year);
  }, [props.dataset.cluster_timeline_histogram, props.clusterId]);

  const entityStats = useMemo(() => {
    const rows = (props.dataset.cluster_entity_stats ?? []).filter(
      (row) => row.cluster_id === props.clusterId,
    );
    rows.sort((a, b) =>
      entitySort === "lift" ? b.lift - a.lift || b.count - a.count : b.count - a.count || b.lift - a.lift,
    );
    return rows.slice(0, 24);
  }, [entitySort, props.dataset.cluster_entity_stats, props.clusterId]);

  const placeStats = useMemo(() => {
    const rows = (props.dataset.cluster_place_stats ?? []).filter(
      (row) => row.cluster_id === props.clusterId,
    );
    rows.sort((a, b) =>
      placeSort === "lift" ? b.lift - a.lift || b.count - a.count : b.count - a.count || b.lift - a.lift,
    );
    return rows.slice(0, 24);
  }, [placeSort, props.dataset.cluster_place_stats, props.clusterId]);

  const termLower = activeTerm.trim().toLowerCase();

  const episodesById = useMemo(() => {
    const map = new Map<number, Dataset["episodes"][number]>();
    for (const e of episodes) map.set(e.id, e);
    return map;
  }, [episodes]);

  const spansByEpisode = useMemo(() => {
    const map = new Map<number, Dataset["spans"]>();
    for (const s of spans) {
      const arr = map.get(s.episode_id) ?? [];
      arr.push(s);
      map.set(s.episode_id, arr);
    }
    return map;
  }, [spans]);

  const entitiesByEpisode = useMemo(() => {
    const map = new Map<number, string[]>();
    for (const e of props.dataset.entities) {
      if (!memberEpisodeIds.has(e.episode_id)) continue;
      const arr = map.get(e.episode_id) ?? [];
      arr.push(e.name);
      map.set(e.episode_id, arr);
    }
    return map;
  }, [props.dataset.entities, memberEpisodeIds]);

  const filteredEpisodes = useMemo(() => {
    return episodes.filter((e) => {
      const es = spansByEpisode.get(e.id) ?? [];
      const hasYearMatch =
        es.length > 0
          ? es.some((s) => {
              const a = yearFromIso(s.start_iso);
              const b = yearFromIso(s.end_iso);
              if (a == null && b == null) return false;
              const lo = Math.min(a ?? b ?? yearRange[0], b ?? a ?? yearRange[1]);
              const hi = Math.max(a ?? b ?? yearRange[0], b ?? a ?? yearRange[1]);
              return hi >= yearRange[0] && lo <= yearRange[1];
            })
          : (() => {
              const y = yearFromIso(e.pub_date_iso);
              return y != null && y >= yearRange[0] && y <= yearRange[1];
            })();
      if (!hasYearMatch) return false;

      if (!termLower) return true;
      const inKeywords = (props.dataset.episode_keywords[String(e.id)] ?? []).some((k) =>
        k.phrase.toLowerCase().includes(termLower),
      );
      const inEntities = (entitiesByEpisode.get(e.id) ?? []).some((name) =>
        name.toLowerCase().includes(termLower),
      );
      const inText =
        e.title.toLowerCase().includes(termLower) ||
        (e.description_pure ?? "").toLowerCase().includes(termLower);
      return inKeywords || inEntities || inText;
    });
  }, [
    entitiesByEpisode,
    episodes,
    props.dataset.episode_keywords,
    spansByEpisode,
    termLower,
    yearRange,
  ]);

  const wordMin = useMemo(() => Math.min(...terms.map((t) => t.weight), 0), [terms]);
  const wordMax = useMemo(() => Math.max(...terms.map((t) => t.weight), 1), [terms]);

  const termGraph = useMemo(() => {
    const nodes = sortedTerms.slice(0, 10).map((term, idx) => ({
      ...term,
      idx,
      key: term.phrase.toLowerCase(),
    }));
    const nodeSet = new Set(nodes.map((n) => n.key));
    const edgeCounts = new Map<string, number>();
    for (const episode of episodes) {
      const keywordTerms = (props.dataset.episode_keywords[String(episode.id)] ?? [])
        .map((k) => k.phrase.toLowerCase())
        .filter((k) => nodeSet.has(k));
      const uniq = Array.from(new Set(keywordTerms)).slice(0, 8);
      for (let i = 0; i < uniq.length; i += 1) {
        for (let j = i + 1; j < uniq.length; j += 1) {
          const a = uniq[i] < uniq[j] ? uniq[i] : uniq[j];
          const b = uniq[i] < uniq[j] ? uniq[j] : uniq[i];
          const key = `${a}::${b}`;
          edgeCounts.set(key, (edgeCounts.get(key) ?? 0) + 1);
        }
      }
    }
    const edges = Array.from(edgeCounts.entries())
      .map(([key, weight]) => {
        const [a, b] = key.split("::");
        return { a, b, weight };
      })
      .sort((x, y) => y.weight - x.weight)
      .slice(0, 20);
    return { nodes, edges };
  }, [episodes, props.dataset.episode_keywords, sortedTerms]);

  const scopeQuery = useMemo(() => {
    const p = new URLSearchParams();
    p.set("cluster", String(props.clusterId));
    if (activeTerm.trim()) p.set("clusterTerm", activeTerm.trim());
    p.set("clusterYearMin", String(yearRange[0]));
    p.set("clusterYearMax", String(yearRange[1]));
    return `?${p.toString()}`;
  }, [activeTerm, props.clusterId, yearRange]);

  if (!cluster) {
    return (
      <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
        <h2 className="m-0 text-lg">Cluster #{props.clusterId}</h2>
        <div className="mt-2 text-sm text-[color:var(--muted)]">Cluster not found in dataset.</div>
      </div>
    );
  }

  return (
    <div className="grid h-full min-h-0 gap-3 overflow-auto">
      <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="m-0 text-lg">Cluster #{cluster.cluster.id}</h2>
            <div className="text-xs text-[color:var(--muted)]">
              {cluster.cluster.label || "(unlabeled)"} · {cluster.cluster.n_members} members · podcast {cluster.cluster.podcast_id}
            </div>
          </div>
          <div className="text-xs text-[color:var(--muted)]">
            centroid: {cluster.cluster.centroid_mid_year.toFixed(0)} · {cluster.cluster.centroid_lat.toFixed(1)}, {" "}
            {cluster.cluster.centroid_lon.toFixed(1)}
          </div>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-2 text-xs md:grid-cols-5">
          <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
            <div className="text-[color:var(--muted)]">Episodes</div>
            <div className="text-base font-semibold">{episodes.length}</div>
          </div>
          <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
            <div className="text-[color:var(--muted)]">Podcasts</div>
            <div className="text-base font-semibold">{clusterStats?.unique_podcast_count ?? 1}</div>
          </div>
          <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
            <div className="text-[color:var(--muted)]">Temporal Span</div>
            <div className="text-base font-semibold">{clusterStats?.temporal_span_years?.toFixed(1) ?? "n/a"}</div>
          </div>
          <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
            <div className="text-[color:var(--muted)]">Cohesion</div>
            <div className="text-base font-semibold">{clusterStats?.cohesion_proxy?.toFixed(3) ?? "n/a"}</div>
          </div>
          <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
            <div className="text-[color:var(--muted)]">Geo Dispersion</div>
            <div className="text-base font-semibold">{clusterStats?.geo_dispersion?.toFixed(1) ?? "n/a"}</div>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="m-0">Scope export</h3>
          <button
            type="button"
            className="rounded border border-[color:var(--border)] px-2 py-1 text-xs"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(scopeQuery);
              } catch {
                // no-op
              }
            }}
          >
            copy
          </button>
        </div>
        <input
          readOnly
          className="w-full rounded border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
          value={scopeQuery}
          aria-label="Cluster scope query"
        />
      </section>

      <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="m-0">Terms</h3>
          <div className="text-xs text-[color:var(--muted)]">
            click term to filter episodes {activeTerm ? `· active: ${activeTerm}` : ""}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {sortedTerms.slice(0, 30).map((t) => {
            const normalized = wordMax > wordMin ? (t.weight - wordMin) / (wordMax - wordMin) : 0.5;
            const fontSize = 11 + normalized * 16;
            const active = activeTerm.toLowerCase() === t.phrase.toLowerCase();
            return (
              <button
                type="button"
                key={t.phrase}
                className={
                  "rounded-full border px-2 py-1 text-left transition " +
                  (active
                    ? "border-[color:var(--accent)] bg-[color:var(--accent)]/20"
                    : "border-[color:var(--border)] bg-[color:var(--surface-2)] hover:bg-[color:var(--surface)]")
                }
                style={{ fontSize }}
                onClick={() => setActiveTerm((prev) => (prev.toLowerCase() === t.phrase.toLowerCase() ? "" : t.phrase))}
                title={`support ${t.support} · lift ${t.lift.toFixed(2)} · drop-impact ${t.dropImpact.toFixed(2)}`}
              >
                {t.phrase}
              </button>
            );
          })}
          {terms.length === 0 && <div className="text-sm text-[color:var(--muted)]">No terms available.</div>}
        </div>
        {termMetrics.length > 0 && (
          <div className="mt-3">
            <div className="mb-1 flex items-center gap-1 text-xs">
              <button
                type="button"
                className={
                  "rounded border px-2 py-1 " +
                  (termSort === "tfidf"
                    ? "border-[color:var(--accent)] bg-[color:var(--accent)]/20"
                    : "border-[color:var(--border)]")
                }
                onClick={() => setTermSort("tfidf")}
              >
                rank: tfidf
              </button>
              <button
                type="button"
                className={
                  "rounded border px-2 py-1 " +
                  (termSort === "lift"
                    ? "border-[color:var(--accent)] bg-[color:var(--accent)]/20"
                    : "border-[color:var(--border)]")
                }
                onClick={() => setTermSort("lift")}
              >
                rank: lift
              </button>
              <button
                type="button"
                className={
                  "rounded border px-2 py-1 " +
                  (termSort === "dropImpact"
                    ? "border-[color:var(--accent)] bg-[color:var(--accent)]/20"
                    : "border-[color:var(--border)]")
                }
                onClick={() => setTermSort("dropImpact")}
              >
                rank: drop-impact
              </button>
            </div>
            <div className="max-h-48 overflow-auto rounded-lg border border-[color:var(--border)]">
              <table className="w-full text-sm">
                <thead className="bg-[color:var(--surface-2)] text-xs text-[color:var(--muted)]">
                  <tr>
                    <th className="px-2 py-1 text-left">Term</th>
                    <th className="px-2 py-1 text-right">TF-IDF</th>
                    <th className="px-2 py-1 text-right">Lift</th>
                    <th className="px-2 py-1 text-right">Drop-impact</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedTerms.slice(0, 20).map((row) => (
                    <tr
                      key={row.phrase}
                      className="cursor-pointer border-t border-[color:var(--border)]/70 hover:bg-[color:var(--surface-2)]/80"
                      onClick={() =>
                        setActiveTerm((prev) =>
                          prev.toLowerCase() === row.phrase.toLowerCase() ? "" : row.phrase,
                        )
                      }
                    >
                      <td className="px-2 py-1">{row.phrase}</td>
                      <td className="px-2 py-1 text-right">{row.weight.toFixed(2)}</td>
                      <td className="px-2 py-1 text-right">{row.lift.toFixed(2)}</td>
                      <td className="px-2 py-1 text-right">{row.dropImpact.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      {termGraph.nodes.length > 0 && (
        <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="m-0">Term graph</h3>
            <div className="text-xs text-[color:var(--muted)]">co-occurrence among top terms</div>
          </div>
          <svg
            viewBox="0 0 460 220"
            className="h-[220px] w-full rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)]"
            role="img"
            aria-label="term cooccurrence graph"
          >
            {termGraph.edges.map((edge) => {
              const ai = termGraph.nodes.findIndex((n) => n.key === edge.a);
              const bi = termGraph.nodes.findIndex((n) => n.key === edge.b);
              if (ai < 0 || bi < 0) return null;
              const angleA = (Math.PI * 2 * ai) / Math.max(1, termGraph.nodes.length);
              const angleB = (Math.PI * 2 * bi) / Math.max(1, termGraph.nodes.length);
              const ax = 230 + Math.cos(angleA) * 86;
              const ay = 110 + Math.sin(angleA) * 80;
              const bx = 230 + Math.cos(angleB) * 86;
              const by = 110 + Math.sin(angleB) * 80;
              return (
                <line
                  key={`${edge.a}-${edge.b}`}
                  x1={ax}
                  y1={ay}
                  x2={bx}
                  y2={by}
                  stroke="rgba(160,180,220,0.32)"
                  strokeWidth={Math.min(4, 1 + edge.weight)}
                />
              );
            })}
            {termGraph.nodes.map((node, idx) => {
              const angle = (Math.PI * 2 * idx) / Math.max(1, termGraph.nodes.length);
              const cx = 230 + Math.cos(angle) * 86;
              const cy = 110 + Math.sin(angle) * 80;
              const active = activeTerm.toLowerCase() === node.phrase.toLowerCase();
              return (
                <g key={node.phrase} transform={`translate(${cx},${cy})`}>
                  <circle
                    r={active ? 16 : 13}
                    fill={active ? "rgba(96,165,250,0.35)" : "rgba(148,163,184,0.35)"}
                    stroke={active ? "rgba(96,165,250,0.9)" : "rgba(148,163,184,0.85)"}
                    strokeWidth={1.4}
                  />
                  <text
                    x={0}
                    y={4}
                    textAnchor="middle"
                    fontSize={10}
                    fill="var(--text)"
                    className="pointer-events-none select-none"
                  >
                    {node.phrase.slice(0, 10)}
                  </text>
                </g>
              );
            })}
          </svg>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {termGraph.nodes.map((node) => (
              <button
                key={node.phrase}
                type="button"
                aria-label={`term node ${node.phrase}`}
                className="rounded border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs hover:bg-[color:var(--surface)]"
                onClick={() =>
                  setActiveTerm((prev) =>
                    prev.toLowerCase() === node.phrase.toLowerCase() ? "" : node.phrase,
                  )
                }
              >
                {node.phrase}
              </button>
            ))}
          </div>
        </section>
      )}

      <GraphIntervalSlider
        spans={spans}
        minYear={yearBounds[0]}
        maxYear={yearBounds[1]}
        value={yearRange}
        onChange={setYearRange}
      />

      {timelineBins.length > 0 && (
        <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
          <h3 className="m-0">Timeline density bins</h3>
          <div className="mt-2 grid gap-1">
            {timelineBins.slice(0, 36).map((bin) => {
              const isActive = yearRange[0] === bin.start_year && yearRange[1] === bin.end_year;
              return (
                <button
                  type="button"
                  key={`${bin.start_year}-${bin.end_year}`}
                  className={
                    "flex items-center justify-between rounded-md border px-2 py-1 text-xs " +
                    (isActive
                      ? "border-[color:var(--accent)] bg-[color:var(--accent)]/20"
                      : "border-[color:var(--border)] bg-[color:var(--surface-2)]")
                  }
                  onClick={() => setYearRange([bin.start_year, bin.end_year])}
                >
                  <span>
                    {bin.start_year} - {bin.end_year}
                  </span>
                  <b>{bin.count}</b>
                </button>
              );
            })}
          </div>
        </section>
      )}

      <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="m-0">Cluster Episodes</h3>
          <div className="text-xs text-[color:var(--muted)]">
            {filteredEpisodes.length} / {episodes.length} in view
          </div>
        </div>
        <EpisodesTable
          dataset={props.dataset}
          episodes={filteredEpisodes}
          selectedEpisodeId={props.selectedEpisodeId}
          onSelectEpisode={props.onSelectEpisode}
        />
      </section>

      <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="m-0">Entity lift</h3>
          <div className="flex items-center gap-1 text-xs">
            <button
              type="button"
              className={
                "rounded border px-2 py-1 " +
                (entitySort === "lift"
                  ? "border-[color:var(--accent)] bg-[color:var(--accent)]/20"
                  : "border-[color:var(--border)]")
              }
              onClick={() => setEntitySort("lift")}
            >
              sort: lift
            </button>
            <button
              type="button"
              className={
                "rounded border px-2 py-1 " +
                (entitySort === "count"
                  ? "border-[color:var(--accent)] bg-[color:var(--accent)]/20"
                  : "border-[color:var(--border)]")
              }
              onClick={() => setEntitySort("count")}
            >
              sort: count
            </button>
          </div>
        </div>
        <div className="max-h-48 overflow-auto rounded-lg border border-[color:var(--border)]">
          <table className="w-full text-sm">
            <thead className="bg-[color:var(--surface-2)] text-xs text-[color:var(--muted)]">
              <tr>
                <th className="px-2 py-1 text-left">Name</th>
                <th className="px-2 py-1 text-left">Kind</th>
                <th className="px-2 py-1 text-right">Count</th>
                <th className="px-2 py-1 text-right">Lift</th>
              </tr>
            </thead>
            <tbody>
              {entityStats.map((row) => (
                <tr key={`${row.name}-${row.kind}`} className="border-t border-[color:var(--border)]/70">
                  <td className="px-2 py-1">{row.name}</td>
                  <td className="px-2 py-1 text-[color:var(--muted)]">{row.kind}</td>
                  <td className="px-2 py-1 text-right">{row.count}</td>
                  <td className="px-2 py-1 text-right">{row.lift.toFixed(2)}</td>
                </tr>
              ))}
              {entityStats.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-2 py-2 text-xs text-[color:var(--muted)]">
                    No entity stats available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="m-0">Place lift</h3>
          <div className="flex items-center gap-1 text-xs">
            <button
              type="button"
              className={
                "rounded border px-2 py-1 " +
                (placeSort === "lift"
                  ? "border-[color:var(--accent)] bg-[color:var(--accent)]/20"
                  : "border-[color:var(--border)]")
              }
              onClick={() => setPlaceSort("lift")}
            >
              sort: lift
            </button>
            <button
              type="button"
              className={
                "rounded border px-2 py-1 " +
                (placeSort === "count"
                  ? "border-[color:var(--accent)] bg-[color:var(--accent)]/20"
                  : "border-[color:var(--border)]")
              }
              onClick={() => setPlaceSort("count")}
            >
              sort: count
            </button>
          </div>
        </div>
        <div className="max-h-48 overflow-auto rounded-lg border border-[color:var(--border)]">
          <table className="w-full text-sm">
            <thead className="bg-[color:var(--surface-2)] text-xs text-[color:var(--muted)]">
              <tr>
                <th className="px-2 py-1 text-left">Place</th>
                <th className="px-2 py-1 text-right">Count</th>
                <th className="px-2 py-1 text-right">Lift</th>
              </tr>
            </thead>
            <tbody>
              {placeStats.map((row) => (
                <tr key={row.canonical_name} className="border-t border-[color:var(--border)]/70">
                  <td className="px-2 py-1">{row.canonical_name}</td>
                  <td className="px-2 py-1 text-right">{row.count}</td>
                  <td className="px-2 py-1 text-right">{row.lift.toFixed(2)}</td>
                </tr>
              ))}
              {placeStats.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-2 py-2 text-xs text-[color:var(--muted)]">
                    No place stats available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {correlations.length > 0 && (
        <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
          <h3 className="m-0">Related clusters</h3>
          <div className="mt-2 grid gap-2">
            {correlations.map((row) => (
              <button
                key={`${row.cluster_a}-${row.cluster_b}`}
                type="button"
                className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2 text-left"
                onClick={() => props.onSelectCluster(row.otherClusterId)}
              >
                <div className="flex items-center justify-between text-sm">
                  <b>Cluster #{row.otherClusterId}</b>
                  <span className="text-xs text-[color:var(--muted)]">jaccard {row.jaccard_episode_overlap.toFixed(2)}</span>
                </div>
                <div className="text-xs text-[color:var(--muted)]">
                  cosine {row.cosine_term_similarity.toFixed(2)} · bridge: {row.bridge_terms.slice(0, 4).join(", ") || "n/a"}
                </div>
              </button>
            ))}
          </div>
        </section>
      )}

      {nextSteps.length > 0 && (
        <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
          <h3 className="m-0">What to explore next</h3>
          <div className="mt-2 grid gap-2">
            {nextSteps.map((step, idx) => {
              const payloadCluster = Number(step.action_payload?.cluster_id);
              const canJump = step.action_type === "open_cluster" && Number.isFinite(payloadCluster);
              return (
                <div key={`${step.title}-${idx}`} className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
                  <div className="text-sm font-semibold">{step.title}</div>
                  <div className="text-xs text-[color:var(--muted)]">{step.rationale}</div>
                  {canJump && (
                    <button
                      type="button"
                      className="mt-2 rounded border border-[color:var(--border)] px-2 py-1 text-xs"
                      onClick={() => props.onSelectCluster(payloadCluster)}
                    >
                      open cluster #{payloadCluster}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {episodesById.size === 0 && (
        <section className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3 text-sm text-[color:var(--muted)]">
          No episodes currently assigned to this cluster.
        </section>
      )}
    </div>
  );
}
