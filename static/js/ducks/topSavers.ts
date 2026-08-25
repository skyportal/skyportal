/**
 * Top savers / top scanners widget data.
 *
 * RTK Query conversion of the old `FETCH_TOP_SAVERS` duck. The backend reads
 * the requesting user's widget preferences server-side, so the query takes no
 * arguments. The old slice shape was `{ savers: [...] }`; consumers now read the
 * array directly from the query result.
 *
 * The websocket `FETCH_TOP_SAVERS` message refetched the list; here it is
 * bridged to cache invalidation of the `TopSaver` tag via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type TopSaver = Record<string, any>;

export const topSaversApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getTopSavers: build.query<TopSaver[], { teamID?: number | null } | void>({
      query: (arg) =>
        arg && arg.teamID != null
          ? `api/internal/source_savers?teamID=${arg.teamID}`
          : "api/internal/source_savers",
      providesTags: ["TopSaver"],
    }),
  }),
});

// Websocket: old handler refetched top savers on FETCH_TOP_SAVERS.
invalidateOnMessage("skyportal/FETCH_TOP_SAVERS", () => ["TopSaver"]);

export const { useGetTopSaversQuery } = topSaversApi;
