/**
 * System/deployment info (git log + running version).
 *
 * Reference RTK Query conversion of the old `FETCH_SYSINFO` duck. The endpoint
 * is injected into the central `skyportalApi`, so caching, loading and error
 * state are handled by RTK Query instead of a hand-written reducer.
 *
 * `version` is a sibling of `data` on the response envelope (see
 * `skyportalApi`), so `transformResponse` merges it back onto the payload to
 * preserve the old slice shape (`{ ...data, version }`).
 */
import { skyportalApi } from "../api/skyportalApi";
import type { SkyportalMeta } from "../api/skyportalApi";

export interface GitlogEntry {
  description: string;
  time: string;
  sha: string;
  [key: string]: unknown;
}

export interface SysInfo {
  gitlog: GitlogEntry[];
  version?: string | undefined;
}

export const sysInfoApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSysInfo: build.query<SysInfo, void>({
      query: () => "api/sysinfo",
      transformResponse: (data: unknown, meta: SkyportalMeta | undefined) => ({
        ...(data as Omit<SysInfo, "version">),
        version: meta?.version,
      }),
      providesTags: ["SysInfo"],
    }),
  }),
});

export const { useGetSysInfoQuery } = sysInfoApi;
