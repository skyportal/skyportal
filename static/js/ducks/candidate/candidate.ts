/**
 * Single candidate (the "candidate" slice).
 *
 * RTK Query conversion of the old `FETCH_CANDIDATE` duck. The single-candidate
 * fetch is injected into the central `skyportalApi` as a query keyed on id and
 * tagged `Candidate`, so caching, loading and error state are handled by RTK
 * Query instead of the hand-written `candidate` reducer.
 */
import { skyportalApi } from "../../api/skyportalApi";
import type { RouteData } from "../../types/routeSchemaMap";

export const candidateApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getCandidate: build.query<
      RouteData<"GET /api/candidates/{obj_id}">,
      number | string
    >({
      query: (id) => `api/candidates/${id}?includeComments=true`,
      providesTags: ["Candidate"],
    }),
  }),
});

export const { useGetCandidateQuery } = candidateApi;
