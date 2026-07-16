import Head from "next/head";
import PageHeader from "../components/PageHeader";
import StatTiles from "../components/StatTiles";
import ChartsRow from "../components/ChartsRow";
import Controls from "../components/Controls";
import IncidentFeed from "../components/IncidentFeed";
import { Icon } from "../lib/icons";
import { FAVICON } from "../lib/constants";
import { useCognitionFabric } from "../lib/store";

export default function Overview() {
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
    stats,
  } = useCognitionFabric();

  return (
    <>
      <Head>
        <title>Cognition Fabric &middot; Overview</title>
        <link rel="icon" href={FAVICON} />
      </Head>

      <PageHeader
        kicker="Phase 2 · CSP Negotiation Protocol"
        title="Cognition Fabric"
        subtitle="Two agents negotiate. Verified outcomes get remembered."
      />

      <StatTiles
        incidentsRun={stats.incidentsRun}
        fabricReuses={stats.fabricReuses}
        verifiedEntries={stats.verifiedEntries}
        blockedWrites={stats.blockedWrites}
        icons={Icon}
      />

      <ChartsRow feed={feed} />

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

      <IncidentFeed
        feed={feed}
        expanded={expanded}
        toggleExpanded={toggleExpanded}
        limit={5}
        viewAllHref="/incidents"
        title="Recent Activity"
      />
    </>
  );
}
