import { Route, Routes } from "react-router";

import Session from "./screens/Session";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<h1>Woodshed</h1>} />
      <Route path="/sessions/:id" element={<Session />} />
    </Routes>
  );
}
