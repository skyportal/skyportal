/**
 * Database/deployment info, fetched once during app hydration.
 *
 * RTK Query conversion of the old `FETCH_DB_INFO` duck. The result is currently
 * not read by any component (the boot fetch primes the cache); a future
 * consumer can call `useGetDbInfoQuery()` to read it.
 */
import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

export const dbInfoApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getDbInfo: build.query<Record<string, unknown>, void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchDbinfo()),
      providesTags: ["DBInfo"],
    }),
  }),
});

export const { useGetDbInfoQuery } = dbInfoApi;
