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
 * The websocket `REFRESH_EARTHQUAKE` message is bridged to cache invalidation
 * via `invalidateOnMessage`.
 */
import { buildQueryString, fileReaderPromise } from "../API";
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

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

export const earthquakeApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getEarthquake: build.query<
      RouteData<"GET /api/earthquake/{event_id}">,
      number | string
    >({
      query: (id) => `api/earthquake/${id}`,
      providesTags: ["Earthquake"],
    }),
    getEarthquakes: build.query<
      RouteData<"GET /api/earthquake">,
      Record<string, unknown> | void
    >({
      query: (params) => {
        const search = buildQueryString(params ?? {});
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
    submitEarthquake: build.mutation<RouteData<"POST /api/earthquake">, any>({
      query: (run) => ({
        url: "api/earthquake",
        method: "POST",
        body: run,
      }),
      invalidatesTags: ["Earthquakes"],
    }),
    submitPrediction: build.mutation<
      RouteData<"POST /api/earthquake/{earthquake_id}/mmadetector/{mma_detector_id}/predictions">,
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
        // Only the comment body keys; earthquake_id is a path param.
        const body: Record<string, any> = {};
        if (formData.text !== undefined) body["text"] = formData.text;
        if (formData.group_ids !== undefined)
          body["group_ids"] = formData.group_ids;
        if (formData.attachment) {
          body["attachment"] = await fileReaderPromise(formData.attachment);
        }
        const result = await baseQuery({
          url: `api/earthquake/${formData.earthquake_id}/comments`,
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
    editCommentOnEarthquake: build.mutation<
      unknown,
      {
        commentID: number | string;
        earthquakeID: number | string;
        formData: any;
      }
    >({
      queryFn: async (
        { commentID, earthquakeID, formData },
        _api,
        _extra,
        baseQuery,
      ) => {
        const body = { ...formData };
        if (body.attachment) {
          body.attachment = await fileReaderPromise(body.attachment);
        }
        const result = await baseQuery({
          url: `api/earthquake/${earthquakeID}/comments/${commentID}`,
          method: "PUT",
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

// Websocket: only active queries refetch, so invalidating `Earthquake` on
// REFRESH_EARTHQUAKE refreshes whichever earthquake detail query is mounted.
invalidateOnMessage("skyportal/REFRESH_EARTHQUAKE", () => ["Earthquake"]);

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
  useEditCommentOnEarthquakeMutation,
  useDeleteCommentOnEarthquakeMutation,
} = earthquakeApi;
