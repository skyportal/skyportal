/**
 * Database statistics (admin DB Stats page).
 *
 * RTK Query conversion of the old `FETCH_DB_STATS` duck.
 */
import { skyportalApi } from "../api/skyportalApi";

export type DBStatsState = Record<string, unknown> | null;

export const dbStatsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDbStats: build.query<DBStatsState, void>({
      query: () => "api/db_stats",
      providesTags: ["DBStats"],
    }),
  }),
});

export const { useGetDbStatsQuery } = dbStatsApi;
