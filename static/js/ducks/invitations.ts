/**
 * User invitations (the admin "Pending Invitations" table and invite flows).
 *
 * RTK Query conversion of the old `FETCH_INVITATIONS` duck, calling the typed
 * `skyportal-js` client. The query accepts the filter/pagination parameters as
 * its argument (the old duck stashed the results in an `invitations` slice;
 * consumers now own the `fetchParams` state and pass it in). The backend's
 * `GET /api/invitations` returns `{ invitations, totalMatches }`.
 *
 * Invite/update/delete are mutations that invalidate the `Invitations` tag so
 * the active list query refetches. This duck has no websocket refresh.
 */
import type {
  FetchInvitationsOptions,
  InvitationPost,
  InvitationsPage,
  UpdateInvitationOptions,
} from "skyportal-js/Invitations";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

export type InvitationsParams = FetchInvitationsOptions;
export type InvitationsResult = InvitationsPage;

export const invitationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getInvitations: build.query<InvitationsPage, InvitationsParams | void>({
      queryFn: (params, api) =>
        clientQuery(api, (client) => client.fetchInvitations(params ?? {})),
      providesTags: ["Invitations"],
    }),
    inviteUser: build.mutation<{ id: number }, InvitationPost>({
      queryFn: (data, api) =>
        clientQuery(api, (client) => client.postInvitation(data)),
      invalidatesTags: ["Invitations"],
    }),
    updateInvitation: build.mutation<
      void,
      { invitationID: number | string; payload: UpdateInvitationOptions }
    >({
      queryFn: ({ invitationID, payload }, api) =>
        clientQuery(api, (client) =>
          client.updateInvitation(Number(invitationID), payload),
        ),
      invalidatesTags: ["Invitations"],
    }),
    deleteInvitation: build.mutation<void, number | string>({
      queryFn: (invitationID, api) =>
        clientQuery(api, (client) =>
          client.deleteInvitation(Number(invitationID)),
        ),
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
