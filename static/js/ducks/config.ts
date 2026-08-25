/**
 * Frontend configuration (the `/api/config` payload).
 *
 * RTK Query conversion of the old `FETCH_CONFIG` duck. The endpoint is injected
 * into the central `skyportalApi`. `version` is a sibling of `data` on the
 * response envelope (see `skyportalApi`), so `transformResponse` merges it back
 * onto the payload to preserve the old slice shape (`{ ...data, version }`).
 *
 * The config is fetched once during hydration (no websocket refresh), so there
 * is no `invalidateOnMessage` here.
 */
import { skyportalApi } from "../api/skyportalApi";
import type { SkyportalMeta } from "../api/skyportalApi";

export interface Config {
  version?: string | undefined;
  [key: string]: unknown;
}

export const configApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getConfig: build.query<Config, void>({
      query: () => "api/config",
      transformResponse: (data: unknown, meta: SkyportalMeta | undefined) => ({
        ...(data as Omit<Config, "version">),
        version: meta?.version,
      }),
      providesTags: ["Config"],
    }),
  }),
});

export const { useGetConfigQuery } = configApi;
