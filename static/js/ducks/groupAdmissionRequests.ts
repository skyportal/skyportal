/**
 * Group admission requests.
 *
 * RTK Query conversion of the old `FETCH_GROUP_ADMISSION_REQUESTS` duck. The
 * endpoints are injected into the central `skyportalApi`. The query is keyed by
 * `groupID`; mutations (request / delete / update status) invalidate the
 * `GroupAdmissionRequest` tag so the list refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import type { RouteData } from "../types/routeSchemaMap";

export const groupAdmissionRequestsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGroupAdmissionRequests: build.query<
      RouteData<"GET /api/group_admission_requests">,
      number | string
    >({
      query: (groupID) => `api/group_admission_requests?groupID=${groupID}`,
      providesTags: ["GroupAdmissionRequest"],
    }),
    requestGroupAdmission: build.mutation<
      unknown,
      {
        userID: number | string;
        groupID: number | string;
        message?: string | undefined;
      }
    >({
      query: ({ userID, groupID, message }) => ({
        url: "api/group_admission_requests",
        method: "POST",
        body: { userID, groupID, message },
      }),
      // Also invalidate Group: an auto-accept group grants membership here, so
      // the groups list must refetch to move it into the user's groups.
      invalidatesTags: ["GroupAdmissionRequest", "Group"],
    }),
    deleteAdmissionRequest: build.mutation<unknown, number | string>({
      query: (ID) => ({
        url: `api/group_admission_requests/${ID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["GroupAdmissionRequest"],
    }),
    updateAdmissionRequestStatus: build.mutation<
      unknown,
      { requestID: number | string; status: string }
    >({
      query: ({ requestID, status }) => ({
        url: `api/group_admission_requests/${requestID}`,
        method: "PATCH",
        body: { status },
      }),
      invalidatesTags: ["GroupAdmissionRequest"],
    }),
  }),
});

export const {
  useGetGroupAdmissionRequestsQuery,
  useRequestGroupAdmissionMutation,
  useDeleteAdmissionRequestMutation,
  useUpdateAdmissionRequestStatusMutation,
} = groupAdmissionRequestsApi;
