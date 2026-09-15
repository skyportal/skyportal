/**
 * Account applications awaiting peer endorsement.
 *
 * The queue is only readable by users holding the "Endorse users" ACL; the
 * application form itself posts to the same endpoint unauthenticated, from the
 * server-rendered /apply page, so there is no submit endpoint here.
 */
import { buildQueryString as toQueryString } from "../API";
import { skyportalApi } from "../api/skyportalApi";

export interface ApplicationUser {
  id: number;
  username: string;
  first_name: string | null;
  last_name: string | null;
}

export interface UserApplication {
  id: number;
  first_name: string;
  last_name: string;
  contact_email: string;
  affiliation: string | null;
  statement: string | null;
  endorser_email: string | null;
  endorser: ApplicationUser | null;
  status: "pending" | "endorsed" | "declined";
  endorsed_by: ApplicationUser | null;
  decided_at: string | null;
  decline_reason: string | null;
  invitation_id: number | null;
  created_at: string;
}

export interface UserApplicationsParams {
  status?: "pending" | "endorsed" | "declined" | undefined;
  mine?: boolean | undefined;
  pageNumber?: number | undefined;
  numPerPage?: number | undefined;
  [key: string]: string | number | boolean | undefined;
}

export interface UserApplicationsResult {
  applications: UserApplication[];
  totalMatches: number;
}

export interface EndorsementPayload {
  status: "endorsed" | "declined";
  groupIDs?: number[] | undefined;
  role?: ("Full user" | "View only") | undefined;
  declineReason?: string | undefined;
}

export const userApplicationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getUserApplications: build.query<
      UserApplicationsResult,
      UserApplicationsParams | void
    >({
      query: (params) => {
        const qs = toQueryString(params ?? {});
        return `api/user_applications${qs ? `?${qs}` : ""}`;
      },
      providesTags: ["UserApplication"],
    }),
    decideUserApplication: build.mutation<
      unknown,
      { applicationID: number; payload: EndorsementPayload }
    >({
      query: ({ applicationID, payload }) => ({
        url: `api/user_applications/${applicationID}`,
        method: "PATCH",
        body: payload,
      }),
      invalidatesTags: ["UserApplication", "Invitations"],
    }),
    deleteUserApplication: build.mutation<unknown, number>({
      query: (applicationID) => ({
        url: `api/user_applications/${applicationID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["UserApplication"],
    }),
  }),
});

export const {
  useGetUserApplicationsQuery,
  useDecideUserApplicationMutation,
  useDeleteUserApplicationMutation,
} = userApplicationsApi;
