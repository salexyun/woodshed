import { Route, Routes } from "react-router";

import Home from "./screens/Home";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
    </Routes>
  );
}
