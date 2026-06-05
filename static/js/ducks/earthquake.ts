/**
 * Earthquakes.
 *
 * RTK Query conversion of the old `FETCH_EARTHQUAKE(S)` duck. Endpoints are
 * injected into the central `skyportalApi`. The single-earthquake detail query
 * (`getEarthquake`) provides the `Earthquake` tag; the paginated list query
 * (`getEarthquakes`) provides the `Earthquakes` tag. Mutations (create an
 * earthquake, submit a prediction, add / delete a comment) invalidate the
 * relevant tag so active queries refetch. Comment-attachment fetches are lazy
 * queries (consumers read the result via the hook rather than the store).
 *
 * The websocket `REFRESH_EARTHQUAKE` / `REFRESH_EARTHQUAKES` messages are
 * bridged to cache invalidation via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface CommentAttachment {
  commentId: number | string;
  text: string;
  attachment: string;
  attachment_name: string;
}

interface CommentAttachmentArg {
  earthquakeID: number | string;
  commentID: number | string;
}

function fileReaderPromise(
  file: File,
): Promise<{ body: string | ArrayBuffer | null; name: string }> {
  return new Promise((resolve) => {
    const filereader = new FileReader();
    filereader.readAsDataURL(file);
    filereader.onloadend = () =>
      resolve({ body: filereader.result, name: file.name });
  });
}

export const earthquakeApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getEarthquake: build.query<any, number | string>({
      query: (id) => `api/earthquake/${id}`,
      providesTags: ["Earthquake"],
    }),
    getEarthquakes: build.query<any, Record<string, unknown> | void>({
      query: (params) => {
        const search = new URLSearchParams(
          (params as Record<string, string>) ?? {},
        ).toString();
        return search ? `api/earthquake?${search}` : "api/earthquake";
      },
      providesTags: ["Earthquakes"],
    }),
    getCommentOnEarthquakeAttachment: build.query<
      CommentAttachment,
      CommentAttachmentArg
    >({
      query: ({ earthquakeID, commentID }) =>
        `api/earthquake/${earthquakeID}/comments/${commentID}/attachment`,
    }),
    getCommentOnEarthquakeTextAttachment: build.query<
      CommentAttachment,
      CommentAttachmentArg
    >({
      query: ({ earthquakeID, commentID }) =>
        `api/earthquake/${earthquakeID}/comments/${commentID}/attachment?download=false&preview=false`,
    }),
    submitEarthquake: build.mutation<unknown, any>({
      query: (run) => ({
        url: "api/earthquake",
        method: "POST",
        body: run,
      }),
      invalidatesTags: ["Earthquakes"],
    }),
    submitPrediction: build.mutation<
      unknown,
      {
        id: number | string;
        mmadetector_id: number | string;
        params?: Record<string, unknown> | undefined;
      }
    >({
      query: ({ id, mmadetector_id, params = {} }) => ({
        url: `api/earthquake/${id}/mmadetector/${mmadetector_id}/predictions`,
        method: "POST",
        body: params,
      }),
      invalidatesTags: ["Earthquake"],
    }),
    addCommentOnEarthquake: build.mutation<unknown, any>({
      queryFn: async (formData, _api, _extra, baseQuery) => {
        const body = { ...formData };
        if (body.attachment) {
          body.attachment = await fileReaderPromise(body.attachment);
        }
        const result = await baseQuery({
          url: `api/earthquake/${body.earthquake_id}/comments`,
          method: "POST",
          body,
        });
        if (result.error) {
          return { error: result.error };
        }
        return { data: result.data };
      },
      invalidatesTags: ["Earthquake"],
    }),
    deleteCommentOnEarthquake: build.mutation<
      unknown,
      { earthquakeID: number | string; commentID: number | string }
    >({
      query: ({ earthquakeID, commentID }) => ({
        url: `api/earthquake/${earthquakeID}/comments/${commentID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Earthquake"],
    }),
  }),
});

// Websocket-driven invalidation: the old handler refetched the loaded
// earthquake (REFRESH_EARTHQUAKE, gated on the loaded event_id matching the
// pushed one) or the whole list (REFRESH_EARTHQUAKES). With RTK Query, only
// active queries for the invalidated tag refetch, so invalidating `Earthquake`
// refreshes whichever earthquake detail query is currently mounted.
invalidateOnMessage("skyportal/REFRESH_EARTHQUAKE", () => ["Earthquake"]);
invalidateOnMessage("skyportal/REFRESH_EARTHQUAKES", () => ["Earthquakes"]);

export const {
  useGetEarthquakeQuery,
  useGetEarthquakesQuery,
  useGetCommentOnEarthquakeAttachmentQuery,
  useLazyGetCommentOnEarthquakeAttachmentQuery,
  useGetCommentOnEarthquakeTextAttachmentQuery,
  useLazyGetCommentOnEarthquakeTextAttachmentQuery,
  useSubmitEarthquakeMutation,
  useSubmitPredictionMutation,
  useAddCommentOnEarthquakeMutation,
  useDeleteCommentOnEarthquakeMutation,
} = earthquakeApi;
