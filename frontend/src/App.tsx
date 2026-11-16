import { useEffect, useState } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router";

import { api, type ApiResult } from "./api";
import type { components } from "./api-schema";
import Home from "./screens/Home";
import Onboarding from "./screens/Onboarding";

// A layout route, so it mounts again (and re-checks) when onboarding navigates into the app.
function RequireProfile() {
  const [profile, setProfile] = useState<ApiResult<components["schemas"]["Profile"]>>();

  useEffect(() => {
    api.get("/api/profile").then(setProfile);
  }, []);

  if (!profile) return null;
  if (profile.ok) return <Outlet />;
  // Only a 404 means "not onboarded"; anything else must not send an onboarded player back.
  const { error } = profile;
  if (error.kind === "http" && error.status === 404) return <Navigate to="/onboarding" replace />;
  return <p role="alert">Couldn't reach Woodshed. Reload to try again.</p>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/onboarding" element={<Onboarding />} />
      <Route element={<RequireProfile />}>
        <Route path="/" element={<Home />} />
        {/* Paths without a screen yet still go through the gate. */}
        <Route path="*" element={null} />
      </Route>
    </Routes>
  );
}
