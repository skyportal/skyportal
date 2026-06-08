/**
 * Single candidate (the "candidate" slice).
 *
 * RTK Query conversion of the old `FETCH_CANDIDATE` duck. The single-candidate
 * fetch is injected into the central `skyportalApi` as a query keyed on id and
 * tagged `Candidate`, so caching, loading and error state are handled by RTK
 * Query instead of the hand-written `candidate` reducer.
 *
 * `fetchCandidate` is retained as a plain action creator because the candidates
 * *list* duck (`candidates.js`) dispatches it with a custom `how`
 * (`FETCH_CANDIDATE_AND_MERGE`) to refetch one candidate and merge it into the
 * list on the `REFRESH_CANDIDATE` websocket message. That merge is the list
 * duck's concern, so the thunk stays here for it to import.
 */
import * as API from "../../API";
import { skyportalApi } from "../../api/skyportalApi";

const FETCH_CANDIDATE = "skyportal/FETCH_CANDIDATE";

export interface Candidate {
  id: string;
  comments?: unknown[] | undefined;
  [key: string]: any;
}

/**
 * Plain action creator kept for the candidates *list* duck, which dispatches
 * it with a custom `how` to merge a refreshed candidate into the list. Not used
 * by the migrated `candidate` slice itself.
 */
export const fetchCandidate = (id: number | string, how = FETCH_CANDIDATE) =>
  API.GET(`/api/candidates/${id}`, how);

export const candidateApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getCandidate: build.query<Candidate, number | string>({
      query: (id) => `api/candidates/${id}`,
      providesTags: ["Candidate"],
    }),
  }),
});

export const { useGetCandidateQuery } = candidateApi;
