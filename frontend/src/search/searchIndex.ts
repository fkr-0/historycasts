import MiniSearch from "minisearch";
import type { Dataset } from "../types";
import type { SearchDoc } from "../types.search";

export type SearchHit = {
  id: string;
  score: number;
  terms: string[];
  match: Record<string, string[]>;
  doc: SearchDoc;
};

export type SearchIndex = {
  mini: MiniSearch<SearchDoc>;
  docsById: Map<string, SearchDoc>;
};

function safe(s: unknown): string {
  return typeof s === "string" ? s : "";
}

export function buildSearchDocs(dataset: Dataset): SearchDoc[] {
  const docs: SearchDoc[] = [];

  // Episodes (title + description)
  for (const ep of dataset.episodes) {
    docs.push({
      id: `ep:${ep.id}`,
      type: "episode",
      episodeId: ep.id,
      title: ep.title,
      text: [ep.title, safe(ep.description_pure)].filter(Boolean).join("\n\n"),
      fields: {
        narrator: safe(ep.narrator),
        kind: safe(ep.kind),
        pub: safe(ep.pub_date_iso),
      },
    });
  }

  // Spans (chapter markers / extracted)
  for (const sp of dataset.spans) {
    docs.push({
      id: `sp:${sp.id}`,
      type: "span",
      episodeId: sp.episode_id,
      text: [safe(sp.source_text), safe(sp.start_iso), safe(sp.end_iso)]
        .filter(Boolean)
        .join(" "),
      fields: { section: safe(sp.source_section) },
    });
  }

  // Places
  for (const pl of dataset.places) {
    docs.push({
      id: `pl:${pl.id}`,
      type: "place",
      episodeId: pl.episode_id,
      text: [
        pl.canonical_name,
        pl.place_kind,
        String(pl.lat ?? ""),
        String(pl.lon ?? ""),
      ].join(" "),
      fields: { kind: pl.place_kind },
    });
  }

  // Entities
  for (const en of dataset.entities) {
    docs.push({
      id: `en:${en.id}`,
      type: "entity",
      episodeId: en.episode_id,
      text: [en.name, en.kind].join(" "),
      fields: { kind: en.kind },
    });
  }

  // Episode keywords
  for (const [episodeIdStr, kws] of Object.entries(dataset.episode_keywords)) {
    const episodeId = Number(episodeIdStr);
    for (const kw of kws) {
      docs.push({
        id: `kw:${episodeId}:${kw.phrase}`,
        type: "keyword",
        episodeId,
        text: kw.phrase,
      });
    }
  }

  // Cluster keywords/entities (so search can hit clusters too)
  for (const c of dataset.clusters) {
    const cid = c.cluster.id;
    for (const kw of c.top_keywords) {
      docs.push({
        id: `ckw:${cid}:${kw.phrase}`,
        type: "cluster_keyword",
        clusterId: cid,
        text: kw.phrase,
      });
    }
    for (const ent of c.top_entities) {
      docs.push({
        id: `cen:${cid}:${ent.name}`,
        type: "cluster_entity",
        clusterId: cid,
        text: `${ent.name} ${ent.kind}`,
      });
    }
  }

  return docs;
}

export function buildSearchIndex(dataset: Dataset): SearchIndex {
  const docs = buildSearchDocs(dataset);
  const docsById = new Map<string, SearchDoc>();
  for (const d of docs) docsById.set(d.id, d);

  const mini = new MiniSearch<SearchDoc>({
    fields: ["text", "title"],
    storeFields: [
      "id",
      "type",
      "episodeId",
      "clusterId",
      "title",
      "text",
      "fields",
    ],
    searchOptions: {
      boost: { title: 3 },
      fuzzy: 0.2,
      prefix: true,
    },
  });

  mini.addAll(docs);
  return { mini, docsById };
}

export function search(
  index: SearchIndex,
  query: string,
  limit = 50,
): SearchHit[] {
  const q = query.trim();
  if (!q) return [];

  const results = index.mini.search(q, { combineWith: "AND" }).slice(0, limit);
  return results.map((r) => ({
    id: r.id,
    score: r.score,
    terms: r.terms,
    match: r.match,
    doc: r as unknown as SearchDoc,
  }));
}
