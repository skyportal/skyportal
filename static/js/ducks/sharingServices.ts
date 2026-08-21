/**
 * Sharing services (TNS / Hermes publishing configuration + submissions).
 *
 * RTK Query conversion of the old `FETCH_SHARING_SERVICES` /
 * `FETCH_SHARING_SERVICE_SUBMISSIONS` duck. The list and submissions are
 * queries; everything that creates/edits/deletes a sharing service, its groups,
 * auto publishers, coauthors, or a submission is a mutation that invalidates the
 * relevant tag so active queries refetch.
 *
 * The old websocket handler refetched the list on `REFRESH_SHARING_SERVICES`
 * (optionally scoped to a group) and refetched submissions on
 * `REFRESH_SHARING_SERVICE_SUBMISSIONS`; both are bridged to tag invalidation
 * via `invalidateOnMessage`.
 */
import type {
  SharingService,
  SharingServicePost,
  SharingServiceSubmissionPost,
  SharingServiceSubmissionsPage,
} from "skyportal-js/SharingServices";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type SharingServiceSubmissions = SharingServiceSubmissionsPage;

/** The group flags, in the snake_case the components already use. */
interface SharingServiceGroupData {
  group_id?: number | string;
  owner?: boolean;
  auto_share_to_tns?: boolean;
  auto_share_to_hermes?: boolean;
  auto_sharing_allow_bots?: boolean;
}

interface FetchSubmissionsArg {
  sharing_service_id: number | string;
  pageNumber?: number | undefined;
  numPerPage?: number | undefined;
}

interface AddSharingServiceGroupArg {
  sharing_service_id: number | string;
  data: SharingServiceGroupData;
}

interface EditSharingServiceGroupArg {
  sharing_service_id: number | string;
  group_id: number | string;
  data: SharingServiceGroupData;
}

interface DeleteSharingServiceGroupArg {
  sharing_service_id: number | string;
  group_id: number | string;
}

interface SharingServiceGroupAutoPublishersArg {
  sharing_service_id: number | string;
  group_id: number | string;
  user_ids?: any[] | undefined;
}

interface SharingServiceCoauthorArg {
  sharing_service_id: number | string;
  user_id: number | string;
}

interface EditSharingServiceArg {
  id: number | string;
  data: SharingServicePost;
}

export const sharingServicesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // The handler takes no query parameters; the old duck passed a group_id
    // filter that the server ignored.
    getSharingServices: build.query<SharingService[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchSharingServices()),
      providesTags: ["SharingService"],
    }),
    getSharingServiceSubmissions: build.query<
      SharingServiceSubmissionsPage,
      FetchSubmissionsArg
    >({
      queryFn: ({ sharing_service_id, pageNumber, numPerPage }, api) =>
        clientQuery(api, (client) =>
          client.fetchSharingServiceSubmissions(Number(sharing_service_id), {
            pageNumber,
            numPerPage,
            includePayload: true,
          }),
        ),
      providesTags: ["SharingServiceSubmission"],
    }),
    addSharingService: build.mutation<{ id: number }, SharingServicePost>({
      queryFn: (data, api) =>
        clientQuery(api, (client) => client.postSharingService(data)),
      invalidatesTags: ["SharingService"],
    }),
    editSharingService: build.mutation<{ id: number }, EditSharingServiceArg>({
      queryFn: ({ id, data }, api) =>
        clientQuery(api, (client) =>
          client.updateSharingService(Number(id), data),
        ),
      invalidatesTags: ["SharingService"],
    }),
    deleteSharingService: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteSharingService(Number(id))),
      invalidatesTags: ["SharingService"],
    }),
    addSharingServiceGroup: build.mutation<
      { id: number },
      AddSharingServiceGroupArg
    >({
      queryFn: ({ sharing_service_id, data }, api) =>
        clientQuery(api, (client) =>
          client.updateSharingServiceGroup(
            Number(sharing_service_id),
            Number(data.group_id),
            {
              owner: data.owner,
              autoShareToTns: data.auto_share_to_tns,
              autoShareToHermes: data.auto_share_to_hermes,
              autoSharingAllowBots: data.auto_sharing_allow_bots,
            },
          ),
        ),
      invalidatesTags: ["SharingService"],
    }),
    editSharingServiceGroup: build.mutation<
      { id: number },
      EditSharingServiceGroupArg
    >({
      queryFn: ({ sharing_service_id, group_id, data }, api) =>
        clientQuery(api, (client) =>
          client.updateSharingServiceGroup(
            Number(sharing_service_id),
            Number(group_id),
            {
              owner: data.owner,
              autoShareToTns: data.auto_share_to_tns,
              autoShareToHermes: data.auto_share_to_hermes,
              autoSharingAllowBots: data.auto_sharing_allow_bots,
            },
          ),
        ),
      invalidatesTags: ["SharingService"],
    }),
    deleteSharingServiceGroup: build.mutation<
      void,
      DeleteSharingServiceGroupArg
    >({
      queryFn: ({ sharing_service_id, group_id }, api) =>
        clientQuery(api, (client) =>
          client.deleteSharingServiceGroup(
            Number(sharing_service_id),
            Number(group_id),
          ),
        ),
      invalidatesTags: ["SharingService"],
    }),
    addSharingServiceGroupAutoPublishers: build.mutation<
      { ids: number[] },
      SharingServiceGroupAutoPublishersArg
    >({
      queryFn: ({ sharing_service_id, group_id, user_ids = [] }, api) =>
        clientQuery(api, (client) =>
          client.postSharingServiceAutoPublishers(
            Number(sharing_service_id),
            Number(group_id),
            user_ids.map(Number),
          ),
        ),
      invalidatesTags: ["SharingService"],
    }),
    deleteSharingServiceGroupAutoPublishers: build.mutation<
      void,
      SharingServiceGroupAutoPublishersArg
    >({
      queryFn: ({ sharing_service_id, group_id, user_ids = [] }, api) =>
        clientQuery(api, (client) =>
          client.deleteSharingServiceAutoPublishers(
            Number(sharing_service_id),
            Number(group_id),
            user_ids.map(Number),
          ),
        ),
      invalidatesTags: ["SharingService"],
    }),
    addSharingServiceCoauthor: build.mutation<
      { id: number },
      SharingServiceCoauthorArg
    >({
      queryFn: ({ sharing_service_id, user_id }, api) =>
        clientQuery(api, (client) =>
          client.postSharingServiceCoauthor(
            Number(sharing_service_id),
            Number(user_id),
          ),
        ),
      invalidatesTags: ["SharingService"],
    }),
    deleteSharingServiceCoauthor: build.mutation<
      void,
      SharingServiceCoauthorArg
    >({
      queryFn: ({ sharing_service_id, user_id }, api) =>
        clientQuery(api, (client) =>
          client.deleteSharingServiceCoauthor(
            Number(sharing_service_id),
            Number(user_id),
          ),
        ),
      invalidatesTags: ["SharingService"],
    }),
    addSharingServiceSubmission: build.mutation<
      void,
      SharingServiceSubmissionPost
    >({
      queryFn: (formData, api) =>
        clientQuery(api, (client) =>
          client.postSharingServiceSubmission(formData),
        ),
      invalidatesTags: ["SharingServiceSubmission"],
    }),
  }),
});

// Websocket: old handler refetched the list on REFRESH_SHARING_SERVICES and
// submissions on REFRESH_SHARING_SERVICE_SUBMISSIONS. The conditional scoping
// (group_id / sharing_service_id) only narrowed *which* fetch ran; invalidating
// the tag refetches whichever query is currently active.
invalidateOnMessage("skyportal/REFRESH_SHARING_SERVICES", () => [
  "SharingService",
]);
invalidateOnMessage("skyportal/REFRESH_SHARING_SERVICE_SUBMISSIONS", () => [
  "SharingServiceSubmission",
]);

export const {
  useGetSharingServicesQuery,
  useLazyGetSharingServicesQuery,
  useGetSharingServiceSubmissionsQuery,
  useAddSharingServiceMutation,
  useEditSharingServiceMutation,
  useDeleteSharingServiceMutation,
  useAddSharingServiceGroupMutation,
  useEditSharingServiceGroupMutation,
  useDeleteSharingServiceGroupMutation,
  useAddSharingServiceGroupAutoPublishersMutation,
  useDeleteSharingServiceGroupAutoPublishersMutation,
  useAddSharingServiceCoauthorMutation,
  useDeleteSharingServiceCoauthorMutation,
  useAddSharingServiceSubmissionMutation,
} = sharingServicesApi;
