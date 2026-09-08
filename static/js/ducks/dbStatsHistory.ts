import { skyportalApi } from "../api/skyportalApi";
import type { paths } from "../types/api";

type DBStatsHistoryRoute = paths["/api/db_stats/history"]["get"];

export type DBStatsInterval = NonNullable<
  NonNullable<DBStatsHistoryRoute["parameters"]["query"]>["interval"]
>;

export type DBStatsHistory = Required<
  NonNullable<
    DBStatsHistoryRoute["responses"][200]["content"]["application/json"]["data"]
  >
>;

type DBStatsHistoryArgs = NonNullable<
  DBStatsHistoryRoute["parameters"]["query"]
>;

export const dbStatsHistoryApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDbStatsHistory: build.query<DBStatsHistory, DBStatsHistoryArgs>({
      query: (params) => ({ url: "api/db_stats/history", params }),
      providesTags: ["DBStats"],
    }),
  }),
});

export const { useGetDbStatsHistoryQuery } = dbStatsHistoryApi;
