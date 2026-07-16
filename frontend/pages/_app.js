import "../styles/globals.css";
import { CognitionFabricProvider } from "../lib/store";
import Layout from "../components/Layout";

export default function App({ Component, pageProps }) {
  return (
    <CognitionFabricProvider>
      <Layout>
        <Component {...pageProps} />
      </Layout>
    </CognitionFabricProvider>
  );
}
