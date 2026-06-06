/**
 * User invitations (the admin "Pending Invitations" table and invite flows).
 *
 * RTK Query conversion of the old `FETCH_INVITATIONS` duck. The query accepts
 * the filter/pagination parameters as its argument (the old duck stashed the
 * results in an `invitations` slice; consumers now own the `fetchParams` state
 * and pass it in). The backend's `GET /api/invitations` returns
 * `{ invitations, totalMatches }`.
 *
 * Invite/update/delete are mutations that invalidate the `Invitations` tag so
 * the active list query refetches. This duck has no websocket refresh.
 */
import { skyportalApi } from "../api/skyportalApi";

export interface InvitationsParams {
  pageNumber?: number | undefined;
  numPerPage?: number | undefined;
  email?: string | undefined;
  group?: string | undefined;
  stream?: string | undefined;
  invitedBy?: string | undefined;
  [key: string]: string | number | boolean | undefined;
}

export interface InvitationsResult {
  invitations: any[];
  totalMatches: number;
}

const buildQueryString = (params: InvitationsParams): string => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.append(key, String(value));
    }
  });
  const qs = search.toString();
  return qs ? `?${qs}` : "";
};

export const invitationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getInvitations: build.query<InvitationsResult, InvitationsParams | void>({
      query: (params) => `api/invitations${buildQueryString(params ?? {})}`,
      providesTags: ["Invitations"],
    }),
    inviteUser: build.mutation<unknown, any>({
      query: (data) => ({
        url: "api/invitations",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Invitations"],
    }),
    updateInvitation: build.mutation<
      unknown,
      { invitationID: number | string; payload: any }
    >({
      query: ({ invitationID, payload }) => ({
        url: `api/invitations/${invitationID}`,
        method: "PATCH",
        body: payload,
      }),
      invalidatesTags: ["Invitations"],
    }),
    deleteInvitation: build.mutation<unknown, number | string>({
      query: (invitationID) => ({
        url: `api/invitations/${invitationID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Invitations"],
    }),
  }),
});

export const {
  useGetInvitationsQuery,
  useInviteUserMutation,
  useUpdateInvitationMutation,
  useDeleteInvitationMutation,
} = invitationsApi;
