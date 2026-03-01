import { useMemo } from "react"
import type { Dataset } from "../types"
import type { IntentOperation } from "../intent/types"
import { buildEpisodeFieldUpdateOp } from "../intent/opBuilders/episodeOps"
import { buildSpanStartYearUpdateOp } from "../intent/opBuilders/spanOps"
import { buildEntityKindUpdateOp } from "../intent/opBuilders/entityOps"

export default function EpisodeDetail(props: {
  dataset: Dataset
  episodeId: number | null
  onQueueOperation?: (op: IntentOperation) => void
}) {
  const ep = useMemo(() => {
    if (props.episodeId == null) return null
    return props.dataset.episodes.find(e => e.id === props.episodeId) ?? null
  }, [props.dataset.episodes, props.episodeId])

  const spans = useMemo(() => {
    if (!ep) return []
    return props.dataset.spans
      .filter(s => s.episode_id === ep.id)
      .slice()
      .sort((a, b) => b.score - a.score)
      .slice(0, 20)
  }, [props.dataset.spans, ep])

  const places = useMemo(() => {
    if (!ep) return []
    return props.dataset.places.filter(p => p.episode_id === ep.id)
  }, [props.dataset.places, ep])

  const entities = useMemo(() => {
    if (!ep) return []
    return props.dataset.entities
      .filter(en => en.episode_id === ep.id)
      .slice()
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 40)
  }, [props.dataset.entities, ep])

  const keywords = useMemo(() => {
    if (!ep) return []
    return (props.dataset.episode_keywords[String(ep.id)] ?? []).slice(0, 30)
  }, [props.dataset.episode_keywords, ep])

  const bestSpan = spans[0] ?? null
  const spanYears = spans
    .flatMap(s => {
      const a = s.start_iso ? new Date(s.start_iso).getUTCFullYear() : Number.NaN
      const b = s.end_iso ? new Date(s.end_iso).getUTCFullYear() : Number.NaN
      return [a, b]
    })
    .filter(y => Number.isFinite(y))
  const coverage = spanYears.length ? [Math.min(...spanYears), Math.max(...spanYears)] : null
  const avgSpanScore =
    spans.length > 0 ? spans.reduce((acc, s) => acc + s.score, 0) / spans.length : 0
  const avgEntityConfidence =
    entities.length > 0 ? entities.reduce((acc, e) => acc + e.confidence, 0) / entities.length : 0
  const clusterId = props.dataset.episode_clusters[String(ep?.id ?? -1)]

  const conceptMap = useMemo(() => {
    return new Map((props.dataset.concepts ?? []).map(c => [c.id, c]))
  }, [props.dataset.concepts])

  const linkedConcepts = useMemo(() => {
    if (!ep) return []
    const ids = props.dataset.episode_concepts?.[String(ep.id)] ?? []
    return ids.map(id => conceptMap.get(id)).filter(Boolean)
  }, [props.dataset.episode_concepts, conceptMap, ep])

  const conceptClaims = useMemo(() => {
    if (!linkedConcepts.length) return []
    const ids = new Set(linkedConcepts.map(c => c?.id))
    return (props.dataset.concept_claims ?? []).filter(cl => ids.has(cl.concept_id))
  }, [linkedConcepts, props.dataset.concept_claims])

  if (!ep) {
    return (
      <div>
        <h2 className="mt-0">Episode</h2>
        <div className="text-[color:var(--muted)]">
          Click a bar in the timeline to open episode details.
        </div>
      </div>
    )
  }

  function queueKindCorrection(): void {
    if (!props.onQueueOperation) return
    const next = prompt("Set episode kind", ep.kind ?? "regular")
    if (!next) return
    props.onQueueOperation(
      buildEpisodeFieldUpdateOp({
        episodeId: ep.id,
        field: "kind",
        value: next,
        precondition: ep.kind ?? null,
      })
    )
  }

  function queueNarratorCorrection(): void {
    if (!props.onQueueOperation) return
    const next = prompt("Set narrator", ep.narrator ?? "")
    if (next == null) return
    props.onQueueOperation(
      buildEpisodeFieldUpdateOp({
        episodeId: ep.id,
        field: "narrator",
        value: next,
        precondition: ep.narrator ?? null,
      })
    )
  }

  function queueTopSpanStartYearCorrection(): void {
    if (!props.onQueueOperation || !bestSpan) return
    const old = bestSpan.start_iso ?? ""
    const year = prompt("Set top span start year (YYYY)", old.slice(0, 4))
    if (!year) return
    const nextIso = `${year}-01-01`
    props.onQueueOperation(
      buildSpanStartYearUpdateOp({
        spanId: bestSpan.id,
        startIso: nextIso,
        prevStartIso: bestSpan.start_iso ?? null,
      })
    )
  }

  function queueTopEntityKindCorrection(): void {
    if (!props.onQueueOperation || entities.length === 0) return
    const e = entities[0]
    const next = prompt(`Set kind for entity "${e.name}"`, e.kind)
    if (!next) return
    props.onQueueOperation(
      buildEntityKindUpdateOp({
        entityId: e.id,
        kind: next,
        prevKind: e.kind,
      })
    )
  }

  return (
    <div>
      <h2 className="mt-0 text-lg">{ep.title}</h2>
      <div className="text-xs text-[color:var(--muted)]">
        pub: {new Date(ep.pub_date_iso).toLocaleString()} · kind: {ep.kind ?? "?"} · narrator:{" "}
        {ep.narrator ?? "?"}
      </div>

      <div className="mt-2 flex flex-wrap gap-2">
        {props.onQueueOperation && (
          <>
            <button
              type="button"
              onClick={queueKindCorrection}
              className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
            >
              queue kind edit
            </button>
            <button
              type="button"
              onClick={queueNarratorCorrection}
              className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
            >
              queue narrator edit
            </button>
            <button
              type="button"
              onClick={queueTopSpanStartYearCorrection}
              className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
              disabled={!bestSpan}
            >
              queue top span year edit
            </button>
            <button
              type="button"
              onClick={queueTopEntityKindCorrection}
              className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
              disabled={entities.length === 0}
            >
              queue top entity kind edit
            </button>
          </>
        )}
        {ep.page_url && (
          <a
            href={ep.page_url}
            target="_blank"
            rel="noreferrer"
            className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
          >
            page
          </a>
        )}
        {ep.audio_url && (
          <a
            href={ep.audio_url}
            target="_blank"
            rel="noreferrer"
            className="rounded-md border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
          >
            audio
          </a>
        )}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-xs md:grid-cols-4">
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
          <div className="text-[color:var(--muted)]">Spans</div>
          <div className="text-base font-semibold">{spans.length}</div>
        </div>
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
          <div className="text-[color:var(--muted)]">Coverage</div>
          <div className="text-base font-semibold">
            {coverage ? `${coverage[0]} - ${coverage[1]}` : "n/a"}
          </div>
        </div>
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
          <div className="text-[color:var(--muted)]">Best score</div>
          <div className="text-base font-semibold">
            {bestSpan ? bestSpan.score.toFixed(2) : "n/a"}
          </div>
        </div>
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
          <div className="text-[color:var(--muted)]">Cluster</div>
          <div className="text-base font-semibold">{clusterId ?? "n/a"}</div>
        </div>
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
          <div className="text-[color:var(--muted)]">Places</div>
          <div className="text-base font-semibold">{places.length}</div>
        </div>
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
          <div className="text-[color:var(--muted)]">Entities</div>
          <div className="text-base font-semibold">{entities.length}</div>
        </div>
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
          <div className="text-[color:var(--muted)]">Entity conf. avg</div>
          <div className="text-base font-semibold">{avgEntityConfidence.toFixed(2)}</div>
        </div>
        <div className="rounded-lg border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2">
          <div className="text-[color:var(--muted)]">Avg span score</div>
          <div className="text-base font-semibold">{avgSpanScore.toFixed(2)}</div>
        </div>
      </div>

      <div className="mt-3">
        <h3>Time spans</h3>
        <div className="grid gap-2">
          {spans.map((s, idx) => (
            <div
              key={s.id}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2"
            >
              <div className="flex justify-between">
                <b>#{idx + 1}</b>
                <span className="text-xs text-[color:var(--muted)]">
                  score {s.score.toFixed(2)}
                </span>
              </div>
              <div className="text-xs text-[color:var(--muted)]">
                {s.start_iso ?? "?"} → {s.end_iso ?? "?"} · {s.precision}/{s.qualifier} · section{" "}
                {s.source_section}
              </div>
              <div className="mt-1.5">{s.source_text}</div>
            </div>
          ))}
          {spans.length === 0 && (
            <div className="text-[color:var(--muted)]">No extracted spans.</div>
          )}
        </div>
      </div>

      <div className="mt-3">
        <h3>Places</h3>
        <div className="grid gap-2">
          {places.map(p => (
            <div
              key={p.id}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2"
            >
              <b>{p.canonical_name}</b>{" "}
              <span className="text-xs text-[color:var(--muted)]">({p.place_kind})</span>
              <div className="text-xs text-[color:var(--muted)]">
                {p.lat != null && p.lon != null
                  ? `${p.lat.toFixed(3)}, ${p.lon.toFixed(3)} · r=${p.radius_km ?? "?"}km`
                  : "(no offline match)"}
              </div>
            </div>
          ))}
          {places.length === 0 && (
            <div className="text-[color:var(--muted)]">No extracted places.</div>
          )}
        </div>
      </div>

      <div className="mt-3">
        <h3>Entities</h3>
        <div className="flex flex-wrap gap-1.5">
          {entities.map(e => (
            <span
              key={e.id}
              className="rounded-full border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
            >
              {e.name} <span className="text-[color:var(--muted)]">({e.kind})</span>
            </span>
          ))}
          {entities.length === 0 && (
            <div className="text-[color:var(--muted)]">No extracted entities.</div>
          )}
        </div>
      </div>

      <div className="mt-3">
        <h3>Keywords</h3>
        <div className="flex flex-wrap gap-1.5">
          {keywords.map(k => (
            <span
              key={k.phrase}
              className="rounded-full border border-[color:var(--border)] bg-[color:var(--surface-2)] px-2 py-1 text-xs"
            >
              {k.phrase}
            </span>
          ))}
          {keywords.length === 0 && (
            <div className="text-[color:var(--muted)]">No extracted keywords.</div>
          )}
        </div>
      </div>

      {(props.dataset.meta.wiki_enriched || props.dataset.meta.wikidata_enriched) && (
        <div className="mt-3">
          <h3>Knowledge Graph Enrichment</h3>
          <div className="text-xs text-[color:var(--muted)]">
            wiki: {String(props.dataset.meta.wiki_enriched)} · wikidata:{" "}
            {String(props.dataset.meta.wikidata_enriched)}
          </div>
          <div className="mt-2 grid gap-2">
            {linkedConcepts.map(c =>
              c ? (
                <div
                  key={c.id}
                  className="rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-2"
                >
                  <div className="text-sm font-semibold">{c.name}</div>
                  <div className="text-xs text-[color:var(--muted)]">
                    {c.kind ?? "concept"} · {c.qid ?? "no qid"}
                  </div>
                  <div className="mt-1 text-xs">
                    {c.url ? (
                      <a href={c.url} target="_blank" rel="noreferrer">
                        {c.url}
                      </a>
                    ) : (
                      "no url"
                    )}
                  </div>
                  <div className="mt-1 text-xs text-[color:var(--muted)]">
                    claims: {conceptClaims.filter(cl => cl.concept_id === c.id).length}
                  </div>
                </div>
              ) : null
            )}
            {linkedConcepts.length === 0 && (
              <div className="text-[color:var(--muted)]">No linked concepts for this episode.</div>
            )}
          </div>
        </div>
      )}

      <div className="mt-3">
        <h3>Description</h3>
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-xl border border-[color:var(--border)] bg-[color:var(--surface-2)] p-3 text-sm">
          {ep.description_pure ?? ""}
        </pre>
      </div>
    </div>
  )
}
