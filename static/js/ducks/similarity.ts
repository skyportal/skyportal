import { skyportalApi } from "../api/skyportalApi";
import type { components } from "../types/api";

export type SimilarSources = components["schemas"]["SimilarSourcesResponse"];
export type SimilarSource = components["schemas"]["SimilarSourceResponse"];
export type SimilarityVetting =
  components["schemas"]["SimilarityVettingResponse"];
export type MoreLikeThis = components["schemas"]["MoreLikeThisResponse"];
export type MoreLikeThisBody = components["schemas"]["MoreLikeThisPostBody"];

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
    moreLikeThis: build.mutation<MoreLikeThis, Partial<MoreLikeThisBody>>({
      query: (body) => ({
        url: "api/similarity/more_like_this",
        method: "POST",
        body,
      }),
    }),
  }),
});

export const {
  useGetSimilarSourcesQuery,
  useLazyGetSimilarityVettingQuery,
  useMoreLikeThisMutation,
} = similarityApi;
