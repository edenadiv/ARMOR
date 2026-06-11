# CDMAS Dashboard (frontend)

React + D3.js + Recharts visualization, fed by the simulator's FastAPI + WebSocket
backend. Built in the **Dashboard** phase (see `docs/superpowers/plans/`).

Three pages (SDD section 6.2):

1. **Dashboard** — network topology, agent message-flow & coalition overlay, live alert
   feed, live performance metrics vs. their targets, resource-allocation panel.
2. **Agent Inspector** — live BDI state of a selected agent: current intention, belief
   base with confidence values, ranked desires, and the live strategy trace.
3. **Validator** — deterministic replay with the constraint checker asserting every
   functional requirement from the spec, validation summary, and selected incident chain.

```bash
npm install
npm run dev      # http://localhost:5173
```
