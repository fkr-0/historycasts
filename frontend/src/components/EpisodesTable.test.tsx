import { fireEvent, render, screen, within } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import type { Dataset } from "../types"
import EpisodesTable from "./EpisodesTable"

function dataset(): Dataset {
  return {
    meta: { schema_version: "x", generated_at_iso: new Date().toISOString(), source_db: "x.db" },
    podcasts: [],
    episodes: [
      { id: 1, podcast_id: 1, title: "Zulu", pub_date_iso: "2021-01-01T00:00:00Z" },
      { id: 2, podcast_id: 1, title: "Alpha", pub_date_iso: "2020-01-01T00:00:00Z" },
    ],
    spans: [],
    places: [],
    entities: [],
    episode_keywords: {},
    episode_clusters: {},
    clusters: [],
  }
}

function rowTitles(): string[] {
  return screen
    .getAllByRole("row")
    .slice(1)
    .map(row => within(row).getAllByRole("cell")[0]?.textContent ?? "")
}

describe("EpisodesTable", () => {
  it("sorts by episode title and shows the sort direction", () => {
    const ds = dataset()
    render(
      <EpisodesTable
        dataset={ds}
        episodes={ds.episodes}
        selectedEpisodeId={null}
        onSelectEpisode={vi.fn()}
      />
    )

    expect(rowTitles()).toEqual(["Zulu? · ?", "Alpha? · ?"])

    fireEvent.click(screen.getByRole("button", { name: /sort by episode/i }))

    expect(rowTitles()).toEqual(["Alpha? · ?", "Zulu? · ?"])
    expect(screen.getByText("↑")).toBeInTheDocument()
  })
})
