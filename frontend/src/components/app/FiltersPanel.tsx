import ClusterPanel from "../ClusterPanel";
import type { Dataset } from "../../types";
import type { Filters } from "../../urlState";
import type { IntentOperation } from "../../intent/types";

export default function FiltersPanel(props: {
  dataset: Dataset;
  filters: Filters;
  onChange: (next: Filters) => void;
  onSelectCluster?: (clusterId: number) => void;
  collapsed: boolean;
  onUncollapse: () => void;
  matchingCount: number;
  onQueueOperation?: (op: IntentOperation) => void;
}) {
  const { dataset, filters } = props;
  const podcasts = dataset.podcasts ?? [];

  if (props.collapsed) {
    return (
      <button type="button" onClick={props.onUncollapse} className="text-xs">
        →
      </button>
    );
  }

  return (
    <>
      <div className="flex items-center justify-between">
        <h2 className="m-0 text-xl font-semibold text-[color:var(--text)]">
          Podcast Explorer
        </h2>
      </div>
      <div className="mt-1 text-xs text-[color:var(--muted)]">
        schema {dataset.meta.schema_version} · generated{" "}
        {new Date(dataset.meta.generated_at_iso).toLocaleString()}
      </div>

      <div className="mt-4 grid gap-3">
        <label>
          Podcast
          <select
            value={String(filters.podcastId)}
            onChange={(e) =>
              props.onChange({
                ...filters,
                podcastId: e.target.value === "all" ? "all" : Number(e.target.value),
              })
            }
            className="mt-1 w-full"
          >
            <option value="all">All</option>
            {podcasts.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
        </label>

        <label>
          Search title (fast filter)
          <input
            value={filters.q}
            onChange={(e) => props.onChange({ ...filters, q: e.target.value })}
            className="mt-1 w-full"
          />
        </label>

        <label>
          Kind
          <select
            value={filters.kind}
            onChange={(e) => props.onChange({ ...filters, kind: e.target.value })}
            className="mt-1 w-full"
          >
            <option value="all">All</option>
            <option value="regular">regular</option>
            <option value="book">book</option>
            <option value="meta">meta</option>
            <option value="special">special</option>
          </select>
        </label>

        <label>
          Narrator contains
          <input
            value={filters.narrator}
            onChange={(e) =>
              props.onChange({ ...filters, narrator: e.target.value })
            }
            className="mt-1 w-full"
          />
        </label>

        <label>
          Timeline spans per episode (top-N)
          <input
            type="range"
            min={1}
            max={6}
            value={filters.topN}
            onChange={(e) =>
              props.onChange({ ...filters, topN: Number(e.target.value) })
            }
            className="mt-1 w-full"
          />
          <div className="text-xs text-[color:var(--muted)]">{filters.topN}</div>
        </label>

        <label>
          Axis density factor (k)
          <input
            type="range"
            min={0.4}
            max={2.5}
            step={0.1}
            value={filters.axisK}
            onChange={(e) =>
              props.onChange({ ...filters, axisK: Number(e.target.value) })
            }
            className="mt-1 w-full"
          />
          <div className="text-xs text-[color:var(--muted)]">
            k = {filters.axisK.toFixed(1)}
          </div>
        </label>

        <label>
          Time scrubber year
          <input
            type="number"
            value={filters.year ?? ""}
            placeholder="e.g. 1776"
            onChange={(e) =>
              props.onChange({
                ...filters,
                year: e.target.value ? Number(e.target.value) : undefined,
              })
            }
            className="mt-1 w-full"
          />
        </label>
      </div>

      <div className="mt-4">
        <ClusterPanel
          dataset={dataset}
          filters={filters}
          onSelectCluster={(cid) => {
            props.onChange({ ...filters, clusterId: cid });
            props.onSelectCluster?.(cid);
          }}
          onClearCluster={() => props.onChange({ ...filters, clusterId: undefined })}
          onQueueOperation={props.onQueueOperation}
        />
      </div>

      <div className="mt-4 text-xs text-[color:var(--muted)]">
        Matching episodes: <b>{props.matchingCount}</b>
      </div>
    </>
  );
}
