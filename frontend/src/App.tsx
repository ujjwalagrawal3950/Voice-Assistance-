import { useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Sidebar, Navbar } from "@/components/Sidebar";
import { Dashboard } from "@/components/dashboard/Dashboard";
import { KAMWorkspace } from "@/components/kam/KAMWorkspace";
import { ProductsPage } from "@/components/products/ProductTable";
import { RecommendationsPage } from "@/components/recommendations/RecommendationList";
import { SettingsPage } from "@/components/settings/Settings";
import { VoiceFloatingBar } from "@/components/kam/VoiceFloatingBar";
import { VoiceProvider } from "@/hooks/useVoice";

export function App() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <Router>
      <VoiceProvider>
        <div className="flex h-screen bg-background text-foreground overflow-hidden">
          <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            <Navbar onMenuClick={() => setMobileOpen(true)} />
            <main className="flex-1 overflow-y-auto p-4 sm:p-6">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/kam" element={<KAMWorkspace />} />
                <Route path="/chat" element={<KAMWorkspace />} />
                <Route path="/chat/:sessionId" element={<KAMWorkspace />} />
                <Route path="/products" element={<ProductsPage />} />
                <Route path="/recommendations" element={<RecommendationsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </main>
          </div>
          <VoiceFloatingBar />
        </div>
      </VoiceProvider>
    </Router>
  );
}
