/**
 * Group admission requests.
 *
 * RTK Query conversion of the old `FETCH_GROUP_ADMISSION_REQUESTS` duck. The
 * endpoints are injected into the central `skyportalApi`. The query is keyed by
 * `groupID`; mutations (request / delete / update status) invalidate the
 * `GroupAdmissionRequest` tag so the list refetches.
 *
 * The websocket `FETCH_GROUP_ADMISSION_REQUESTS` message is bridged to cache
 * invalidation via `invalidateOnMessage`.
 */
import type {
  GroupAdmissionRequest,
  GroupAdmissionRequestStatus,
} from "skyportal-js/GroupAdmissionRequests";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const groupAdmissionRequestsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGroupAdmissionRequests: build.query<
      GroupAdmissionRequest[],
      number | string
    >({
      queryFn: (groupID, api) =>
        clientQuery(api, (client) =>
          client.fetchGroupAdmissionRequests({ groupId: Number(groupID) }),
        ),
      providesTags: ["GroupAdmissionRequest"],
    }),
    requestGroupAdmission: build.mutation<
      { id: number },
      { userID: number | string; groupID: number | string }
    >({
      queryFn: ({ userID, groupID }, api) =>
        clientQuery(api, (client) =>
          client.postGroupAdmissionRequest(Number(groupID), Number(userID)),
        ),
      // Also invalidate Group: an auto-accept group grants membership here, so
      // the groups list must refetch to move it into the user's groups.
      invalidatesTags: ["GroupAdmissionRequest", "Group"],
    }),
    deleteAdmissionRequest: build.mutation<void, number | string>({
      queryFn: (ID, api) =>
        clientQuery(api, (client) =>
          client.deleteGroupAdmissionRequest(Number(ID)),
        ),
      invalidatesTags: ["GroupAdmissionRequest"],
    }),
    updateAdmissionRequestStatus: build.mutation<
      void,
      { requestID: number | string; status: GroupAdmissionRequestStatus }
    >({
      queryFn: ({ requestID, status }, api) =>
        clientQuery(api, (client) =>
          client.updateGroupAdmissionRequest(Number(requestID), status),
        ),
      invalidatesTags: ["GroupAdmissionRequest"],
    }),
  }),
});

// Websocket-driven invalidation: refresh admission requests on push.
invalidateOnMessage("skyportal/FETCH_GROUP_ADMISSION_REQUESTS", () => [
  "GroupAdmissionRequest",
]);

export const {
  useGetGroupAdmissionRequestsQuery,
  useRequestGroupAdmissionMutation,
  useDeleteAdmissionRequestMutation,
  useUpdateAdmissionRequestStatusMutation,
} = groupAdmissionRequestsApi;
