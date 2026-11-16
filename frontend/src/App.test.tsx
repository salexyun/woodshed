import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it, vi } from "vitest";

import App from "./App";

vi.mock("./api", () => ({ api: { get: async () => ({ ok: true, data: {} }) } }));

describe("App", () => {
  it("renders the shell inside a router", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    await screen.findByRole("heading", { name: /woodshed/i });
  });
});
