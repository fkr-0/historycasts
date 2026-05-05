import { describe, expect, it } from "vitest"
import { resolveDocsPath } from "./DocModal"

describe("DocModal", () => {
  it("resolves docs path from the document base URI", () => {
    expect(resolveDocsPath("changelog", "https://example.com/historycasts/")).toBe(
      "/historycasts/docs/changelog.html",
    )
  })
})
