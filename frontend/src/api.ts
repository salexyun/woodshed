import type { components, paths } from "./api-schema";

type Method = "get" | "post" | "patch";
type PathsWith<M extends Method> = {
  [P in keyof paths]: paths[P] extends Record<M, object> ? P : never;
}[keyof paths];
type Operation<P extends keyof paths, M extends Method> = paths[P][M];

type Json<R> = R extends { content: { "application/json": infer T } } ? T : never;
type Data<O> = O extends { responses: infer R } ? Json<R[keyof R & (200 | 201)]> : never;
type Options<O> = (O extends { parameters: { path: infer P } } ? { path: P } : unknown) &
  (O extends { requestBody: { content: { "application/json": infer B } } } ? { body: B } : unknown);
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
  let response: Response;
  try {
    response = await fetch(url, init);
  } catch {
    return { ok: false, error: { kind: "network" } };
  }
  const json = await response.json().catch(() => undefined);
  return response.ok
    ? { ok: true, data: json }
    : { ok: false, error: { kind: "http", status: response.status, detail: json?.detail } };
}

const method =
  <M extends Method>(name: M) =>
  <P extends PathsWith<M>>(path: P, ...[options]: Args<Operation<P, M>>) =>
    request<Data<Operation<P, M>>>(name.toUpperCase(), path, options as RequestOptions);

export const api = { get: method("get"), post: method("post"), patch: method("patch") };
