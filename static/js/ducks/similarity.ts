import { skyportalApi } from "../api/skyportalApi";
import type { components } from "../types/api";

export type SimilarSources = components["schemas"]["SimilarSourcesResponse"];
export type SimilarSource = components["schemas"]["SimilarSourceResponse"];
export type SimilarityVetting =
  components["schemas"]["SimilarityVettingResponse"];

export const similarityApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getSimilarSources: build.query<
      SimilarSources,
      { objId: string; topK?: number }
    >({
      query: ({ objId, topK = 10 }) =>
        `api/sources/${encodeURIComponent(objId)}/similar?topK=${topK}`,
    }),
    getSimilarityVetting: build.query<
      SimilarityVetting,
      { days: number; groupIds?: number[] }
    >({
      query: ({ days, groupIds }) =>
        `api/similarity/vetting?days=${days}${
          groupIds?.length ? `&groupIds=${groupIds.join(",")}` : ""
        }`,
    }),
  }),
});

export const { useGetSimilarSourcesQuery, useLazyGetSimilarityVettingQuery } =
  similarityApi;
