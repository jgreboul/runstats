import { NavLink, Route, Routes } from "react-router-dom";

import "./App.css";
import { ActivitiesView, ActivityDetailView } from "./views/ActivitiesView";
import { ChatAssistantView } from "./views/ChatAssistantView";
import { DashboardView } from "./views/DashboardView";
import { HealthView } from "./views/HealthView";
import { SyncHistoryView, SyncRunDetailView } from "./views/SyncHistoryView";
import { WatchSettingsView } from "./views/WatchSettingsView";

const navigationItems = [
  { label: "Dashboard", path: "/" },
  { label: "Activities", path: "/activities" },
  { label: "Health", path: "/health" },
  { label: "Chat Assistant", path: "/chat" },
  { label: "Watch Settings", path: "/watch" },
  { label: "Sync History", path: "/sync-history" },
];

function NotFoundView() {
  return (
    <section className="state-panel state-panel-error" role="alert">
      <h2>Page not found</h2>
      <p>The requested RunStats route does not exist.</p>
    </section>
  );
}

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Main navigation">
        <div>
          <p className="brand-kicker">RunStats</p>
          <h1>Local running intelligence</h1>
        </div>
        <nav>
          {navigationItems.map((item) => (
            <NavLink
              className={({ isActive }) =>
                isActive ? "nav-link nav-link-active" : "nav-link"
              }
              end={item.path === "/"}
              key={item.path}
              to={item.path}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="content">
        <Routes>
          <Route path="/" element={<DashboardView />} />
          <Route path="/activities" element={<ActivitiesView />} />
          <Route path="/activities/:activityId" element={<ActivityDetailView />} />
          <Route path="/health" element={<HealthView />} />
          <Route path="/chat" element={<ChatAssistantView />} />
          <Route
            path="/watch"
            element={<WatchSettingsView />}
          />
          <Route path="/sync-history" element={<SyncHistoryView />} />
          <Route
            path="/sync-history/:syncRunId"
            element={<SyncRunDetailView />}
          />
          <Route path="*" element={<NotFoundView />} />
        </Routes>
      </main>
    </div>
  );
}
