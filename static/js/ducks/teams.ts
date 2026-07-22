/**
 * Teams: a collaboration-level grouping over one or more Groups.
 *
 * A team is purely an organizational/presentation layer; it never widens data
 * visibility. The endpoints are injected into the central `skyportalApi` and
 * invalidate the "Team" tag. The active team is a per-user preference
 * (`preferences.activeTeam`) so it follows the user across devices; the
 * `useActiveTeam` hook resolves it against the team list.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import { useGetProfileQuery } from "./profile";

export interface Team {
  id: number;
  name: string;
  nickname?: string | null;
  description?: string | null;
  primary_color?: string | null;
  secondary_color?: string | null;
  logo_url?: string | null;
  background_url?: string | null;
  groups?: { id: number; name: string; nickname?: string | null }[];
  users?: { id: number; username: string }[];
  num_members?: number;
  [key: string]: unknown;
}

interface TeamsResponse {
  teams: Team[];
}

export const teamsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getTeams: build.query<Team[], void>({
      query: () => "api/teams",
      transformResponse: (data: TeamsResponse) => data?.teams ?? [],
      providesTags: ["Team"],
    }),
    getTeam: build.query<Team, number | string>({
      query: (team_id) => `api/teams/${team_id}`,
      providesTags: ["Team"],
    }),
    addTeam: build.mutation<{ id: number }, Record<string, unknown>>({
      query: (form_data) => ({
        url: "api/teams",
        method: "POST",
        body: form_data,
      }),
      invalidatesTags: ["Team"],
    }),
    updateTeam: build.mutation<
      unknown,
      { teamID: number | string; form_data: Record<string, unknown> }
    >({
      query: ({ teamID, form_data }) => ({
        url: `api/teams/${teamID}`,
        method: "PUT",
        body: form_data,
      }),
      invalidatesTags: ["Team"],
    }),
    deleteTeam: build.mutation<unknown, number | string>({
      query: (team_id) => ({
        url: `api/teams/${team_id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Team"],
    }),
  }),
});

invalidateOnMessage("skyportal/FETCH_TEAMS", () => ["Team"]);

export const {
  useGetTeamsQuery,
  useGetTeamQuery,
  useAddTeamMutation,
  useUpdateTeamMutation,
  useDeleteTeamMutation,
} = teamsApi;

/**
 * Resolve the current user's active team (from `preferences.activeTeam`) against
 * the accessible team list. Returns the id and the full team object (or null).
 */
export const useActiveTeam = (): {
  activeTeamId: number | null;
  activeTeam: Team | null;
} => {
  const { data: profile } = useGetProfileQuery();
  const { data: teams } = useGetTeamsQuery();
  const raw = profile?.preferences?.["activeTeam"];
  const activeTeamId =
    raw === undefined || raw === null || raw === "" ? null : Number(raw);
  const activeTeam =
    (activeTeamId !== null && teams?.find((t) => t.id === activeTeamId)) ||
    null;
  return { activeTeamId, activeTeam };
};
