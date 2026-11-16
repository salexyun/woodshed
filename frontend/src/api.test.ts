import { afterEach, beforeEach, describe, expect, expectTypeOf, it, vi } from "vitest";

import { api, type ApiResult } from "./api";
import type { components } from "./api-schema";

type Profile = components["schemas"]["Profile"];

const profile: Profile = {
  years_playing: 3,
  stuck_on: "same_material",
  cue: "after coffee",
  weekly_goal_days: 4,
  timezone: "Asia/Seoul",
};

const fetchMock = vi.fn<typeof fetch>();
const respond = (status: number, body: unknown) =>
  fetchMock.mockResolvedValue(Response.json(body, { status }));
const lastCall = () => {
  const [url, init] = fetchMock.mock.lastCall!;
  return { url, method: init?.method ?? "GET", init };
};

beforeEach(() => vi.stubGlobal("fetch", fetchMock));
afterEach(() => {
  vi.unstubAllGlobals();
  fetchMock.mockReset();
});

describe("successful calls", () => {
  it("returns the parsed body as typed data", async () => {
    respond(200, profile);
    const result = await api.get("/api/profile");
    expect(result).toEqual({ ok: true, data: profile });
    expectTypeOf(result).toEqualTypeOf<ApiResult<Profile>>();
  });

  it("gets the path without a body", async () => {
    respond(200, profile);
    await api.get("/api/profile");
    const { url, method, init } = lastCall();
    expect([url, method, init?.body]).toEqual(["/api/profile", "GET", undefined]);
  });

  it("sends the body as JSON", async () => {
    respond(200, profile);
    await api.patch("/api/profile", { body: { cue: "after coffee" } });
    const { url, method, init } = lastCall();
    expect([url, method]).toEqual(["/api/profile", "PATCH"]);
    expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json");
    expect(JSON.parse(init?.body as string)).toEqual({ cue: "after coffee" });
  });

  it("posts the body to the filled path", async () => {
    respond(200, {});
    const result = await api.post("/api/sessions/{id}/ratings", {
      path: { id: 7 },
      body: { item_id: "major:E", rating: "easy" },
    });
    const { url, method, init } = lastCall();
    expect([url, method]).toEqual(["/api/sessions/7/ratings", "POST"]);
    expect(JSON.parse(init?.body as string)).toEqual({ item_id: "major:E", rating: "easy" });
    expectTypeOf(result).toEqualTypeOf<ApiResult<components["schemas"]["ProgressItem"]>>();
  });

  it("rejects options the operation doesn't take", () => {
    // Never called: only tsc checks it.
    const misuse = () => [
      // @ts-expect-error GET /api/profile takes no body
      api.get("/api/profile", { body: { cue: "x" } }),
      // @ts-expect-error GET /api/home takes no path parameters
      api.get("/api/home", { path: { id: 1 } }),
    ];
    expectTypeOf(misuse).toBeFunction();
  });

  it("fills path parameters", async () => {
    respond(200, {});
    await api.get("/api/lessons/{quality}", { path: { quality: "minor" } });
    expect(lastCall().url).toBe("/api/lessons/minor");
  });
});

describe("API errors", () => {
  it.each([
    [404, "unknown lesson"],
    [409, "already onboarded"],
    [503, "database unreachable"],
  ])("surfaces a %i with its detail", async (status, detail) => {
    respond(status, { detail });
    expect(await api.get("/api/profile")).toEqual({
      ok: false,
      error: { kind: "http", status, detail },
    });
  });

  it("surfaces validation errors with their detail list", async () => {
    const detail = [{ loc: ["body", "cue"], msg: "too short", type: "string_too_short" }];
    respond(422, { detail });
    expect(await api.patch("/api/profile", { body: { cue: "" } })).toEqual({
      ok: false,
      error: { kind: "http", status: 422, detail },
    });
  });

  it("surfaces a 500 without a JSON body", async () => {
    fetchMock.mockResolvedValue(new Response("Internal Server Error", { status: 500 }));
    const result = await api.get("/api/profile");
    expect(result).toMatchObject({ ok: false, error: { kind: "http", status: 500 } });
  });

  it("surfaces a 2xx without a JSON body as an error", async () => {
    fetchMock.mockResolvedValue(new Response("<!doctype html>", { status: 200 }));
    expect(await api.get("/api/profile")).toEqual({ ok: false, error: { kind: "http", status: 200 } });
  });

  it("surfaces a network failure instead of throwing", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    expect(await api.get("/api/profile")).toEqual({ ok: false, error: { kind: "network" } });
  });
});
