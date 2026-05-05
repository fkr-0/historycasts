import { afterEach, describe, expect, it, vi } from "vitest";
import { loadDataset } from "./loadDataset";

describe("loadDataset", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    document.head.innerHTML = "";
  });

  it("fetches dataset.json under the document base path", async () => {
    document.head.innerHTML = '<base href="/historycasts/">';
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ podcasts: [], episodes: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await loadDataset();

    expect(fetchMock).toHaveBeenCalledWith("/historycasts/dataset.json", {
      cache: "no-store",
    });
  });
});
