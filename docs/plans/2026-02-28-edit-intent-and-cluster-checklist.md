# Edit Intent + Cluster Implementation Checklist

## Backend schema/export
- [x] Add dataset revision metadata
- [x] Add optional row fingerprint fields for editable entities
- [x] Add cluster stats payload
- [x] Add cluster term metrics payload
- [x] Add cluster correlations payload
- [x] Add cluster timeline histogram payload
- [x] Add cluster next-step suggestions payload

## Frontend intent queue
- [x] Add operation types and localStorage persistence
- [x] Add reconciliation engine against dataset state
- [x] Add top-right queue button with status colors
- [x] Add queue modal with cleanup/cancel/export/copy
- [x] Add operation creation entry points (episode/span/entity/cluster)

## Frontend cluster UX
- [x] Add cluster index view with sortable metrics
- [x] Add cluster detail view with term/time/map/episodes sync
- [x] Add drop-impact/lift interactions
- [x] Add relation graph and next-step cards
- [x] Add scope export and URL persistence

## Testing + verification
- [x] Python tests for export metric integrity
- [x] Frontend tests for queue state and reconciliation
- [x] Frontend tests for cluster drill-down synchronization
- [ ] Full lint/test/build pass (python + frontend)
