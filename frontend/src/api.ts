import type { components, paths } from "./api-schema";

type Method = "get" | "post" | "patch";
type PathsWith<M extends Method> = {
  [P in keyof paths]: paths[P] extends Record<M, object> ? P : never;
}[keyof paths];

type Json<R> = R extends { content: { "application/json": infer T } } ? T : never;
type Data<O> = O extends { responses: infer R } ? Json<R[keyof R & (200 | 201)]> : never;
type Options<O> = (O extends { parameters: { path: infer P } } ? { path: P } : { path?: never }) &
  (O extends { requestBody: { content: { "application/json": infer B } } }
    ? { body: B }
    : { body?: never });
// The options argument is required only when the operation has path parameters or a body.
type Args<O> = {} extends Options<O> ? [options?: Options<O>] : [options: Options<O>];

export type ApiError =
  | { kind: "http"; status: number; detail?: string | components["schemas"]["ValidationError"][] }
  | { kind: "network" };
export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: ApiError };

type RequestOptions = { path?: Record<string, string | number>; body?: unknown };

async function request<T>(
  method: string,
  path: string,
  { path: params = {}, body }: RequestOptions = {},
): Promise<ApiResult<T>> {
  const url = path.replace(/\{(\w+)\}/g, (_, key: string) => encodeURIComponent(params[key]));
  const init: RequestInit =
    body === undefined
      ? { method }
      : { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const response = await fetch(url, init).catch(() => undefined);
  if (!response) return { ok: false, error: { kind: "network" } };
  const json = await response.json().catch(() => undefined);
  // A 2xx that isn't JSON (e.g. the SPA's index.html) is a misrouted request, not data.
  if (response.ok && json !== undefined) return { ok: true, data: json };
  return { ok: false, error: { kind: "http", status: response.status, detail: json?.detail } };
}

const method =
  <M extends Method>(name: M) =>
  <P extends PathsWith<M>>(path: P, ...[options]: Args<paths[P][M]>) =>
    request<Data<paths[P][M]>>(name.toUpperCase(), path, options as RequestOptions);

export const api = { get: method("get"), post: method("post"), patch: method("patch") };
