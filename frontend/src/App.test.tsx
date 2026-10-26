import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, it } from "vitest";

import App from "./App";

describe("App", () => {
  it("renders the shell inside a router", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>,
    );
    screen.getByRole("heading", { name: /woodshed/i });
  });
});
