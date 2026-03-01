import type { Dataset } from "../../types";
import { default as EpisodeDetail } from "../EpisodeDetail";

export default function EpisodeTab(props: {
  dataset: Dataset;
  episodeId: number;
}) {
  return (
    <div className="h-full overflow-auto rounded-xl border border-[color:var(--border)] bg-[color:var(--surface)]/60 p-3">
      <EpisodeDetail dataset={props.dataset} episodeId={props.episodeId} />
    </div>
  );
}
