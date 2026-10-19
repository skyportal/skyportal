import { skyportalApi } from "../api/skyportalApi";

export interface InvitationsResult {
  invitations: any[];
  totalMatches: number;
}

export const invitationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getInvitations: build.query<InvitationsResult, void>({
      query: () => "api/invitations",
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
