import Head from "next/head";
import PageHeader from "../components/PageHeader";
import FabricTable from "../components/FabricTable";
import { FAVICON } from "../lib/constants";
import { useCognitionFabric } from "../lib/store";

export default function FabricPage() {
  const { fabricRows } = useCognitionFabric();

  return (
    <>
      <Head>
        <title>Cognition Fabric &middot; Fabric Memory</title>
        <link rel="icon" href={FAVICON} />
      </Head>

      <PageHeader
        kicker="Persistent Memory"
        title="Fabric Memory"
        subtitle="Every verified resolution, keyed by (incident signature, domain scope). Inspect it directly with sqlite3 fabric.db."
      />

      <FabricTable fabricRows={fabricRows} />
    </>
  );
}
