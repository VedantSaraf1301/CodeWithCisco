import Link from "next/link";
import { useRouter } from "next/router";
import { useCognitionFabric } from "../lib/store";

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/incidents", label: "Incidents" },
  { href: "/simulator", label: "Simulator" },
  { href: "/fabric", label: "Fabric Memory" },
  { href: "/how-it-works", label: "How It Works" },
];

export default function Layout({ children }) {
  const { connected } = useCognitionFabric();
  const router = useRouter();

  return (
    <div className="app-shell">
      <nav className="nav">
        <div className="nav-inner">
          <Link href="/" className="brand">
            <div className="brand-mark">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="6" cy="6" r="2.2" fill="white" />
                <circle cx="18" cy="6" r="2.2" fill="white" />
                <circle cx="12" cy="18" r="2.2" fill="white" />
                <path d="M6 6L12 18M18 6L12 18M6 6L18 6" stroke="white" strokeWidth="1.4" strokeLinecap="round" />
              </svg>
            </div>
            <span className="brand-name">Cognition Fabric</span>
          </Link>

          <div className="nav-links">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-link ${router.pathname === item.href ? "active" : ""}`}
              >
                {item.label}
              </Link>
            ))}
          </div>

          <div className="status-pill">
            <span className={`status-dot ${connected ? "connected" : "disconnected"}`} />
            {connected ? "Stream connected" : "Stream disconnected"}
          </div>
        </div>
      </nav>

      <div className="container">
        {children}
        <div className="page-footer">
          <strong>Cognition Fabric</strong> &middot; Phase 2 &middot; IPv6 &middot; CSP negotiation protocol
        </div>
      </div>
    </div>
  );
}
