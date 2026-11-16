import { useEffect, useState } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router";

import { api } from "./api";
import Onboarding from "./screens/Onboarding";

// A layout route, so it mounts again (and re-checks) when onboarding navigates into the app.
function RequireProfile() {
  const [onboarded, setOnboarded] = useState<boolean>();

  useEffect(() => {
    api.get("/api/profile").then((r) => setOnboarded(r.ok));
  }, []);

  if (onboarded === undefined) return null;
  return onboarded ? <Outlet /> : <Navigate to="/onboarding" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/onboarding" element={<Onboarding />} />
      <Route element={<RequireProfile />}>
        <Route path="/" element={<h1>Woodshed</h1>} />
        {/* Paths without a screen yet still go through the gate. */}
        <Route path="*" />
      </Route>
    </Routes>
  );
}
