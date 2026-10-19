/**
 * Candidates list (the scanning page).
 *
 * RTK Query conversion of the old `candidates` duck. This duck is a COMPOSITE of
 * three different concerns, handled three different ways:
 *
 *  1. Server LIST with discrete pagination (`getCandidates`). The scanning page
 *     pages through `/api/candidates`. All pages of one filter/query share a
 *     single cache entry (`serializeQueryArgs` drops `pageNumber`); `merge`
 *     replaces the list on every page (Previous/Next show one page at a time),
 *     mirroring the old `FETCH_CANDIDATES` reducer used by page navigation.
 *
 *  2. Server cache (simple): `getAnnotationsInfo` (query) and
 *     `generateSurveyThumbnail` (mutation).
 *
 *  3. Client UI state: `selectedAnnotationSortOptions` is NOT server data. It is
 *     kept in a small retained reducer (still the `candidates` slice) with a plain
 *     action creator. Consumers keep reading it from `state.candidates.*`.
 *
 * WebSocket (`REFRESH_CANDIDATE`, `REFRESH_SOURCE`): on a push for a candidate
 * currently in the active `getCandidates` cache entry, the single candidate is
 * refetched via the already-migrated `candidateApi.getCandidate` query and
 * merged into the list with `updateQueryData`, preserving the old "only if
 * loaded" guard.
 */
import messageHandler from "baselayer/MessageHandler";

import { buildQueryString, filterOutEmptyValues } from "../../API";
import { skyportalApi } from "../../api/skyportalApi";
import { candidateApi } from "./candidate";
import store from "../../store";

const SET_CANDIDATES_ANNOTATION_SORT_OPTIONS =
  "skyportal/SET_CANDIDATES_ANNOTATION_SORT_OPTIONS";

const REFRESH_CANDIDATE = "skyportal/REFRESH_CANDIDATE";
const REFRESH_SOURCE = "skyportal/REFRESH_SOURCE";

/**
 * Build the cache key for a `getCandidates` arg by dropping `pageNumber` (and
 * `queryID`, which the backend assigns on the first page and is then echoed
 * back on later pages), so all pages of one filter/query collapse onto a single
 * cache entry. Returns a stable stringification of the remaining fields.
 */
const candidatesCacheKey = (arg: Record<string, any> | undefined) => {
  const rest: Record<string, any> = { ...(arg || {}) };
  delete rest["pageNumber"];
  delete rest["queryID"];
  delete rest["_searchCount"];
  return JSON.stringify(
    Object.keys(rest)
      .sort()
      .reduce<Record<string, any>>((acc, key) => {
        acc[key] = rest[key];
        return acc;
      }, {}),
  );
};

// The arg of the currently-active `getCandidates` query, captured so the
// websocket handler can target the exact cache entry with `updateQueryData`.
let activeCandidatesArg: any = null;

export const candidatesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getCandidates: build.query({
      query: (filterParams = {}) => {
        const cleaned = { ...filterParams };
        delete cleaned["_searchCount"];
        // keep false so requireDetections=false reaches the server (it defaults
        // to true there, so dropping it made the checkbox a no-op)
        const filtered = filterOutEmptyValues(cleaned, true, false);
        const queryString = buildQueryString(filtered);
        return `api/candidates?${queryString}`;
      },
      // All pages of one filter/query share a single cache entry. The scanning
      // page is discrete pagination (Previous/Next show one page at a time), so
      // every page replaces the list rather than accumulating.
      serializeQueryArgs: ({ queryArgs }) => candidatesCacheKey(queryArgs),
      merge: (currentCacheData, newData) => {
        currentCacheData.candidates = newData.candidates;
        currentCacheData.pageNumber = newData.pageNumber;
        currentCacheData.totalMatches = newData.totalMatches;
        currentCacheData.queryID = newData.queryID;
      },
      // Refetch whenever the arg changes (page change or filter change).
      forceRefetch: ({ currentArg, previousArg }) =>
        JSON.stringify(currentArg) !== JSON.stringify(previousArg),
      transformResponse: (data) => ({
        candidates: data?.candidates ?? [],
        pageNumber: data?.pageNumber ?? 1,
        totalMatches: data?.totalMatches ?? 0,
        queryID: data?.queryID ?? null,
      }),
      // Track the active arg for the websocket handler.
      onQueryStarted: (arg) => {
        activeCandidatesArg = arg;
      },
      providesTags: ["Candidate"],
    }),
    getAnnotationsInfo: build.query({
      query: (groupIDs?: number[]) =>
        groupIDs?.length
          ? `api/internal/annotations_info?groupIDs=${groupIDs.join()}`
          : "api/internal/annotations_info",
      providesTags: ["AnnotationsInfo"],
    }),
    generateSurveyThumbnail: build.mutation({
      query: (body: { objID: string; types: string[] }) => ({
        url: "api/internal/survey_thumbnail",
        method: "POST",
        body,
      }),
    }),
  }),
});

export const {
  useGetCandidatesQuery,
  useGetAnnotationsInfoQuery,
  useGenerateSurveyThumbnailMutation,
} = candidatesApi;

// ---------------------------------------------------------------------------
// Client UI state (NOT server data): retained reducer + plain action creators.
// ---------------------------------------------------------------------------

export const setCandidatesAnnotationSortOptions = (item: any) => ({
  type: SET_CANDIDATES_ANNOTATION_SORT_OPTIONS,
  item,
});

const initialState = {
  selectedAnnotationSortOptions: null,
};

const reducer = (state = initialState, action: any) => {
  switch (action.type) {
    case SET_CANDIDATES_ANNOTATION_SORT_OPTIONS:
      return { ...state, selectedAnnotationSortOptions: action.item };
    default:
      return state;
  }
};

store.injectReducer("candidates", reducer);

// ---------------------------------------------------------------------------
// WebSocket: refresh a single candidate into the active list cache entry.
// ---------------------------------------------------------------------------

messageHandler.add((actionType: string, payload: any, dispatch: any) => {
  const refreshes = [REFRESH_CANDIDATE, REFRESH_SOURCE];
  if (!refreshes.includes(actionType) || activeCandidatesArg === null) {
    return;
  }
  const cacheEntry = candidatesApi.endpoints.getCandidates.select(
    activeCandidatesArg,
  )(store.getState());
  const loaded = cacheEntry?.data?.candidates;
  if (!loaded) {
    return;
  }
  // Preserve the old guard: only refresh if the candidate is in the loaded list.
  const objKey = payload.id ?? payload.obj_key;
  const match = loaded.find((c: any) => c.internal_key === objKey);
  if (!match) {
    return;
  }
  // Fetch the single candidate via the migrated candidate query, then merge it
  // into the active list cache entry.
  dispatch(
    candidateApi.endpoints.getCandidate.initiate(match.id, {
      subscribe: false,
      forceRefetch: true,
    }),
  ).then(({ data: fresh }: any) => {
    if (!fresh) return;
    dispatch(
      candidatesApi.util.updateQueryData(
        "getCandidates",
        activeCandidatesArg,
        (draft: any) => {
          const idx = draft.candidates.findIndex((c: any) => c.id === fresh.id);
          if (idx !== -1) {
            draft.candidates[idx] = fresh;
          }
        },
      ),
    );
  });
});
