import Head from "next/head";
import PageHeader from "../components/PageHeader";
import Controls from "../components/Controls";
import IncidentFeed from "../components/IncidentFeed";
import { FAVICON } from "../lib/constants";
import { useCognitionFabric } from "../lib/store";

export default function IncidentsPage() {
  const {
    feed,
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
    runIncident,
    repeatLastIncident,
    injectChaos,
    injectAudit,
  } = useCognitionFabric();

  return (
    <>
      <Head>
        <title>Cognition Fabric &middot; Incidents</title>
        <link rel="icon" href={FAVICON} />
      </Head>

      <PageHeader
        kicker="Live Feed"
        title="Incidents"
        subtitle="Every incident, negotiated fresh or reused instantly from Fabric memory."
      />

      <Controls
        incidentTypes={incidentTypes}
        regions={regions}
        selectedType={selectedType}
        setSelectedType={setSelectedType}
        selectedRegion={selectedRegion}
        setSelectedRegion={setSelectedRegion}
        lastIncident={lastIncident}
        busy={busy}
        onRun={runIncident}
        onRepeat={repeatLastIncident}
        onChaos={injectChaos}
        onAudit={injectAudit}
      />

      <IncidentFeed feed={feed} expanded={expanded} toggleExpanded={toggleExpanded} />
    </>
  );
}
