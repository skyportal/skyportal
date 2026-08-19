/**
 * Database statistics (admin DB Stats page).
 *
 * RTK Query conversion of the old `FETCH_DB_STATS` duck.
 */
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

export type DBStatsState = Record<string, unknown> | null;

export const dbStatsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDbStats: build.query<DBStatsState, void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchDbStats()),
      providesTags: ["DBStats"],
    }),
  }),
});

export const { useGetDbStatsQuery } = dbStatsApi;
