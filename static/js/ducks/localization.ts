/**
 * Localization (GCN skymap localizations).
 *
 * RTK Query conversion of the old `FETCH_LOCALIZATION` duck. The old duck kept
 * two slices (`analysisLoc`, `obsplanLoc`) keyed by a `type` argument; both
 * hit the same `GET /api/localization/{dateobs}/name/{name}` endpoint and only
 * differed in where the result was stored. RTK Query caches by argument, so a
 * single `getLocalization` query subsumes both: consumers pass the
 * `dateobs`/`localization_name` they need and get an independently cached
 * result.
 *
 * `deleteLocalization` and `postLocalizationFromNotice` are mutations that
 * invalidate the `Localization` tag.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

interface GetLocalizationArg {
  dateobs: string;
  localization_name: string;
}

export const localizationApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getLocalization: build.query<
      RouteData<"GET /api/localization/{dateobs}/name/{localization_name}">,
      GetLocalizationArg
    >({
      query: ({ dateobs, localization_name }) =>
        `api/localization/${dateobs}/name/${localization_name}`,
      providesTags: ["Localization"],
    }),
    deleteLocalization: build.mutation<unknown, GetLocalizationArg>({
      query: ({ dateobs, localization_name }) => ({
        url: `api/localization/${dateobs}/name/${localization_name}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Localization"],
    }),
    postLocalizationFromNotice: build.mutation<
      unknown,
      { dateobs: string; noticeID: number | string }
    >({
      query: ({ dateobs, noticeID }) => ({
        url: `api/localization/${dateobs}/notice/${noticeID}`,
        method: "POST",
      }),
      invalidatesTags: ["Localization"],
    }),
  }),
});

export const {
  useGetLocalizationQuery,
  useLazyGetLocalizationQuery,
  useDeleteLocalizationMutation,
  usePostLocalizationFromNoticeMutation,
} = localizationApi;

// The contour is generated in a background task after ingestion, so a
// localization is first fetched without one and REFRESH_GCN_EVENT signals it is
// committed. That message is also pushed for unrelated changes (a comment, an
// alias update), so only refetch the ones still waiting for their contour.
invalidateOnMessage("skyportal/REFRESH_GCN_EVENT", (payload, getState) => {
  const queries = (getState() as any)?.skyportalApi?.queries ?? {};
  const waitingForContour = Object.values(queries).some(
    (entry: any) =>
      entry?.endpointName === "getLocalization" &&
      (payload?.gcnEvent_dateobs == null ||
        entry?.originalArgs?.dateobs === payload.gcnEvent_dateobs) &&
      !entry?.data?.contour,
  );
  return waitingForContour ? ["Localization"] : null;
});
