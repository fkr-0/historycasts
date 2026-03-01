import type { IntentOperation, IntentQueueMeta } from "./types"

export const INTENT_QUEUE_KEY = "historycasts.intentQueue.v1"
export const INTENT_META_KEY = "historycasts.intentMeta.v1"

export function loadIntentQueue(): IntentOperation[] {
  try {
    const raw = localStorage.getItem(INTENT_QUEUE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as IntentOperation[]) : []
  } catch {
    return []
  }
}

export function saveIntentQueue(ops: IntentOperation[]): void {
  localStorage.setItem(INTENT_QUEUE_KEY, JSON.stringify(ops))
}

export function loadIntentMeta(): IntentQueueMeta {
  try {
    const raw = localStorage.getItem(INTENT_META_KEY)
    if (!raw) return { version: 1 }
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === "object" && parsed.version === 1) {
      return parsed as IntentQueueMeta
    }
    return { version: 1 }
  } catch {
    return { version: 1 }
  }
}

export function saveIntentMeta(meta: IntentQueueMeta): void {
  localStorage.setItem(INTENT_META_KEY, JSON.stringify(meta))
}
