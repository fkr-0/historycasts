import "@testing-library/jest-dom/vitest"

if (!("ResizeObserver" in globalThis)) {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  // @ts-expect-error test-only shim
  globalThis.ResizeObserver = ResizeObserverMock
}
