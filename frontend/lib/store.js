import { createContext, useContext, useEffect, useRef, useState } from "react";
import { API_BASE } from "./constants";

const CognitionFabricContext = createContext(null);

// Owns the live connection (SSE + polling refreshes) and all shared state,
// mounted once in _app.js so it survives navigation between pages instead
// of reconnecting and losing accumulated feed history on every route change.
export function CognitionFabricProvider({ children }) {
  const [connected, setConnected] = useState(false);
  const [feed, setFeed] = useState([]);
  const [fabricRows, setFabricRows] = useState([]);
  const [incidentTypes, setIncidentTypes] = useState([]);
  const [regions, setRegions] = useState([]);
  const [selectedType, setSelectedType] = useState("");
  const [selectedRegion, setSelectedRegion] = useState("");
  const [lastIncident, setLastIncident] = useState(null);
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(() => new Set());
  const esRef = useRef(null);
  const idCounter = useRef(0);

  const toggleExpanded = (id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const refetchFabric = () => {
    fetch(`${API_BASE}/api/fabric`)
      .then((r) => r.json())
      .then(setFabricRows)
      .catch(() => {});
  };

  useEffect(() => {
    fetch(`${API_BASE}/api/incident-types`)
      .then((r) => r.json())
      .then((data) => {
        setIncidentTypes(data.incident_types || []);
        setRegions(data.regions || []);
      })
      .catch(() => {});

    refetchFabric();

    // Repopulate the feed from server-side history so a fresh page load
    // doesn't lose the incident narrative the Fabric table already survives.
    fetch(`${API_BASE}/api/events/history`)
      .then((r) => r.json())
      .then((history) => {
        if (!Array.isArray(history) || history.length === 0) return;
        const withIds = history.map((item) => ({ ...item, received_at: Date.now(), _id: idCounter.current++ }));
        const newestFirst = [...withIds].reverse();
        setFeed((prev) => [...prev, ...newestFirst]);
        const lastReal = newestFirst.find((item) => !item.chaos && !item.audit_demo && item.incident);
        if (lastReal) setLastIncident((prev) => prev ?? lastReal.incident);
      })
      .catch(() => {});

    const es = new EventSource(`${API_BASE}/api/events/stream`);
    esRef.current = es;
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      const _id = idCounter.current++;
      setFeed((prev) => [{ ...data, received_at: Date.now(), _id }, ...prev].slice(0, 50));
      refetchFabric();
    };

    return () => es.close();
  }, []);

  const runIncident = async (overrideType, overrideRegion) => {
    setBusy(true);
    try {
      const body = {};
      const type = overrideType ?? selectedType;
      const region = overrideRegion ?? selectedRegion;
      if (type) body.incident_type = type;
      if (type) {
        const match = incidentTypes.find((t) => t.type === type);
        if (match) body.domain = match.domain;
      }
      if (region) body.region = region;

      const res = await fetch(`${API_BASE}/api/simulate/incident`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const outcome = await res.json();
      setLastIncident(outcome.incident);
    } finally {
      setBusy(false);
    }
  };

  const repeatLastIncident = () => {
    if (!lastIncident) return;
    runIncident(lastIncident.incident_type, lastIncident.region);
  };

  const injectChaos = async () => {
    setBusy(true);
    try {
      await fetch(`${API_BASE}/api/chaos/inject`, { method: "POST" });
    } finally {
      setBusy(false);
    }
  };

  const injectAudit = async () => {
    setBusy(true);
    try {
      await fetch(`${API_BASE}/api/audit/inject`, { method: "POST" });
    } finally {
      setBusy(false);
    }
  };

  const realIncidents = feed.filter((e) => !e.chaos && !e.audit_demo);
  const fabricHits = realIncidents.filter((e) => e.fabric_hit).length;
  const verifiedCount = fabricRows.filter((r) => r.guardrail_status === "VERIFIED").length;
  const rejectedCount = fabricRows.filter((r) => r.guardrail_status === "REJECTED").length;

  const value = {
    connected,
    feed,
    fabricRows,
    incidentTypes,
    regions,
    selectedType,
    setSelectedType,
    selectedRegion,
    setSelectedRegion,
    lastIncident,
    busy,
    expanded,
    toggleExpanded,
    runIncident: () => runIncident(),
    repeatLastIncident,
    injectChaos,
    injectAudit,
    stats: {
      incidentsRun: realIncidents.length,
      fabricReuses: fabricHits,
      verifiedEntries: verifiedCount,
      blockedWrites: rejectedCount,
    },
  };

  return <CognitionFabricContext.Provider value={value}>{children}</CognitionFabricContext.Provider>;
}

export function useCognitionFabric() {
  const ctx = useContext(CognitionFabricContext);
  if (!ctx) throw new Error("useCognitionFabric must be used within CognitionFabricProvider");
  return ctx;
}
