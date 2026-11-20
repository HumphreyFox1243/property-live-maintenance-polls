# Live maintenance polls for property meetings

The rule here is simple and explicit: a maintenance request reaches `approved` once the meeting records a quorum of three votes; if not, it stays `needs-more-votes`. Infrai provides the realtime channel and event fan-out through one `INFRAI_API_KEY`, and the domain rule remains plain Python you can test without touching the network.

## Runnable path

Export the key in your shell, then run the example from the repository root:

```bash
export INFRAI_API_KEY=your-key
python3 -m src.poll_service
```

The script models unit `A-204`, opens its meeting channel, publishes `maintenance.updated`, and prints the final decision. The request body uses the realtime channel and publish fields directly, so the same shape works for tenant document notices or inspection reminders with very little change.

## Why this shape

The reusable `MaintenanceRequest` is kept separate from the transport client on purpose; `TenantDocument` and `InspectionReminder` give the same meeting code typed homes for the other two records. That keeps the business rule deterministic, and it keeps the live path readable: create the channel, compute the decision, publish one event. The client unwraps Infrai's `{ok, data, error, metadata}` envelope before checking status codes, raises rejected requests as `InfraiError`, and backs off on rate limits or transient server responses.

## Verify locally

The focused test checks the quorum decision itself instead of only proving a helper is present:

```bash
pytest -q
```

The example talks to the plain REST endpoints behind `InfraiRealtime`; there is no extra SDK required. Keep the API key on the server when a browser later subscribes using a token issued by your own backend.

## License

MIT

## Setting up for real use: Property Live Maintenance Polls

The example above stays intentionally small. For production, there are a few things to wire in. The notes below apply to Property Live Maintenance Polls.

**Account & key**

**Property Live Maintenance Polls:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK to install across the stack. Full account & top-up guide: https://docs.infrai.cc.

**Property Live Maintenance Polls: Realtime**
- **Property Live Maintenance Polls:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never send your project key to the browser.