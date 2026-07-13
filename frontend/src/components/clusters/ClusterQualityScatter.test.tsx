import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import ClusterQualityScatter from "./ClusterQualityScatter"

describe("ClusterQualityScatter", () => {
  it("opens a cluster from mouse and keyboard interaction", () => {
    const onSelect = vi.fn()
    render(
      <ClusterQualityScatter
        points={[
          {
            id: 7,
            label: "Industrialisation",
            nMembers: 18,
            cohesion: 0.72,
            distinctiveness: 0.64,
            spread: 84,
            historicalYear: 1880,
          },
        ]}
        onSelectCluster={onSelect}
      />
    )

    const point = screen.getByRole("button", {
      name: /inspect cluster #7 in comparison chart/i,
    })
    fireEvent.click(point)
    fireEvent.keyDown(point, { key: "Enter" })

    expect(onSelect).toHaveBeenNthCalledWith(1, 7)
    expect(onSelect).toHaveBeenNthCalledWith(2, 7)
    expect(screen.getByText(/better-defined clusters sit toward the upper left/i)).toBeTruthy()
    expect(screen.getByLabelText("Cohesion reference")).toBeTruthy()
  })
})
