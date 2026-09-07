import { skyportalApi } from "../api/skyportalApi";

export type DBStatsInterval = "hour" | "day" | "week" | "month";

export interface DBStatsHistory {
  interval: DBStatsInterval;
  startDate: string;
  endDate: string;
  bins: string[];
  tables: string[];
  counts: Record<string, number[]>;
}

interface DBStatsHistoryArgs {
  tables: string;
  interval: DBStatsInterval;
  startDate: string;
}

export const dbStatsHistoryApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDbStatsHistory: build.query<DBStatsHistory, DBStatsHistoryArgs>({
      query: (params) => ({ url: "api/db_stats/history", params }),
      providesTags: ["DBStats"],
    }),
  }),
});

export const { useGetDbStatsHistoryQuery } = dbStatsHistoryApi;
