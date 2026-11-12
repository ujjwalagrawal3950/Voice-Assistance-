import { Suspense, lazy, useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Sidebar, Navbar } from "@/components/Sidebar";
import { VoiceFloatingBar } from "@/components/kam/VoiceFloatingBar";
import { VoiceProvider } from "@/hooks/useVoice";

const LandingPage = lazy(() =>
  import("@/components/landing/LandingPage").then((m) => ({ default: m.LandingPage }))
);
const Dashboard = lazy(() =>
  import("@/components/dashboard/Dashboard").then((m) => ({ default: m.Dashboard }))
);
const KAMWorkspace = lazy(() =>
  import("@/components/kam/KAMWorkspace").then((m) => ({ default: m.KAMWorkspace }))
);
const ProductsPage = lazy(() =>
  import("@/components/products/ProductTable").then((m) => ({ default: m.ProductsPage }))
);
const RecommendationsPage = lazy(() =>
  import("@/components/recommendations/RecommendationList").then((m) => ({ default: m.RecommendationsPage }))
);
const SettingsPage = lazy(() =>
  import("@/components/settings/Settings").then((m) => ({ default: m.SettingsPage }))
);

function RouteSkeleton() {
  return (
    <div className="container-responsive py-8 space-y-4">
      <div className="h-24 rounded-2xl bg-card border border-border animate-pulse" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="h-36 rounded-2xl bg-card border border-border animate-pulse" />
        <div className="h-36 rounded-2xl bg-card border border-border animate-pulse" />
        <div className="h-36 rounded-2xl bg-card border border-border animate-pulse" />
      </div>
    </div>
  );
}

export function App() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <Router>
      <VoiceProvider>
        <div className="flex h-screen bg-background text-foreground overflow-hidden">
          <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <Navbar onMenuClick={() => setMobileOpen(true)} />
            <main className="flex-1 overflow-y-auto p-3 sm:p-5 scrollbar-thin">
              <Suspense fallback={<RouteSkeleton />}>
                <Routes>
                  <Route path="/" element={<LandingPage />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/kam" element={<KAMWorkspace />} />
                  <Route path="/chat" element={<KAMWorkspace />} />
                  <Route path="/chat/:sessionId" element={<KAMWorkspace />} />
                  <Route path="/products" element={<ProductsPage />} />
                  <Route path="/recommendations" element={<RecommendationsPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                </Routes>
              </Suspense>
            </main>
          </div>
          <VoiceFloatingBar />
        </div>
      </VoiceProvider>
    </Router>
  );
}
