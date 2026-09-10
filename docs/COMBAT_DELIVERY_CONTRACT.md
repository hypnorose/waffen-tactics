# Combat delivery contract

`POST /game/combat` uses Server-Sent Events framing as a transport compatibility
layer for the current fetch parser, but its delivery model is `batch_replay`,
not live SSE.

The server completes preparation, simulation, result calculation, and the
idempotent player-state commit before yielding the first combat frame. The
frontend then replays the committed event batch locally at the selected combat
speed. The response advertises this contract with:

- `X-Combat-Delivery-Mode: batch_replay`
- `X-Combat-Live-Stream: false`
- `delivery_mode: "batch_replay"` on initialization and terminal frames

Retries with the same idempotency key return the cached terminal state/result
and do not commit or reward combat a second time. A terminal `end` frame is the
only completion signal and contains the committed player state. Errors are
framed as deterministic error events and do not expose a partial authoritative
state.
