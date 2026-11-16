import { Route, Routes } from "react-router";

import PickASong from "./screens/PickASong";
import Progress from "./screens/Progress";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<h1>Woodshed</h1>} />
      <Route path="/pick-a-song" element={<PickASong />} />
      <Route path="/progress" element={<Progress />} />
    </Routes>
  );
}
