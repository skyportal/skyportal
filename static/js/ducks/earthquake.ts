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
import type { CommentAttachment } from "skyportal-js/Comments";
import type {
  Earthquake,
  EarthquakePost,
  EarthquakePostResponse,
  EarthquakesPage,
  FetchEarthquakesOptions,
} from "skyportal-js/Earthquakes";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

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
    getEarthquake: build.query<Earthquake, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchEarthquake(String(id))),
      providesTags: ["Earthquake"],
    }),
    getEarthquakes: build.query<
      EarthquakesPage,
      FetchEarthquakesOptions | void
    >({
      queryFn: (params, api) =>
        clientQuery(api, (client) => client.fetchEarthquakes(params ?? {})),
      providesTags: ["Earthquakes"],
    }),
    // Downloads the attachment itself; the text form below returns JSON.
    getCommentOnEarthquakeAttachment: build.query<
      Uint8Array,
      CommentAttachmentArg
    >({
      queryFn: ({ earthquakeID, commentID }, api) =>
        clientQuery(api, (client) =>
          client.fetchCommentAttachment(earthquakeID, Number(commentID), {
            resourceType: "earthquake",
          }),
        ),
    }),
    getCommentOnEarthquakeTextAttachment: build.query<
      CommentAttachment,
      CommentAttachmentArg
    >({
      queryFn: ({ earthquakeID, commentID }, api) =>
        clientQuery(api, (client) =>
          client.fetchCommentAttachmentText(earthquakeID, Number(commentID), {
            resourceType: "earthquake",
          }),
        ),
    }),
    submitEarthquake: build.mutation<EarthquakePostResponse, EarthquakePost>({
      queryFn: (run, api) =>
        clientQuery(api, (client) => client.postEarthquake(run)),
      invalidatesTags: ["Earthquakes"],
    }),
    // The handler reads no body, so the form data the caller passes is unused.
    submitPrediction: build.mutation<
      void,
      { id: number | string; mmadetector_id: number | string }
    >({
      queryFn: ({ id, mmadetector_id }, api) =>
        clientQuery(api, (client) =>
          client.postEarthquakePrediction(String(id), Number(mmadetector_id)),
        ),
      invalidatesTags: ["Earthquake"],
    }),
    addCommentOnEarthquake: build.mutation<
      { comment_id: number },
      {
        earthquake_id: number | string;
        text: string;
        group_ids?: number[];
        attachment?: File;
      }
    >({
      queryFn: async ({ earthquake_id, text, group_ids, attachment }, api) => {
        const file = attachment
          ? await fileReaderPromise(attachment)
          : undefined;
        return clientQuery(api, (client) =>
          file
            ? client.postCommentWithAttachment(
                earthquake_id,
                text,
                file.name,
                String(file.body),
                { resourceType: "earthquake", groupIds: group_ids },
              )
            : client.postComment(earthquake_id, text, {
                resourceType: "earthquake",
                groupIds: group_ids,
              }),
        );
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
      queryFn: async ({ commentID, earthquakeID, formData }, api) => {
        const file = formData.attachment
          ? await fileReaderPromise(formData.attachment)
          : undefined;
        return clientQuery(api, (client) =>
          client.updateComment(earthquakeID, Number(commentID), {
            resourceType: "earthquake",
            text: formData.text,
            groupIds: formData.group_ids,
            ...(file
              ? { attachmentName: file.name, attachmentBody: String(file.body) }
              : {}),
          }),
        );
      },
      invalidatesTags: ["Earthquake"],
    }),
    deleteCommentOnEarthquake: build.mutation<
      void,
      { earthquakeID: number | string; commentID: number | string }
    >({
      queryFn: ({ earthquakeID, commentID }, api) =>
        clientQuery(api, (client) =>
          client.deleteComment(earthquakeID, Number(commentID), {
            resourceType: "earthquake",
          }),
        ),
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
  useEditCommentOnEarthquakeMutation,
  useDeleteCommentOnEarthquakeMutation,
} = earthquakeApi;
