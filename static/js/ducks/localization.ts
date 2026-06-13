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
