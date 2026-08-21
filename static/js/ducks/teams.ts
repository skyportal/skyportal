/**
 * Teams: a collaboration-level grouping over one or more Groups.
 *
 * A team is purely an organizational/presentation layer; it never widens data
 * visibility. The endpoints call the typed `skyportal-js` client and invalidate
 * the "Team" tag. The active team is a per-user preference
 * (`preferences.activeTeam`) so it follows the user across devices; the
 * `useActiveTeam` hook resolves it against the team list.
 */
import type { Team, TeamPost, TeamPut } from "skyportal-js/Teams";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";
import { useGetProfileQuery } from "./profile";

export type { Team };

export const teamsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getTeams: build.query<Team[], void>({
      queryFn: (_arg, api) => clientQuery(api, (client) => client.fetchTeams()),
      providesTags: ["Team"],
    }),
    getTeam: build.query<Team, number | string>({
      queryFn: (team_id, api) =>
        clientQuery(api, (client) => client.fetchTeam(Number(team_id))),
      providesTags: ["Team"],
    }),
    addTeam: build.mutation<{ id: number }, TeamPost>({
      queryFn: (form_data, api) =>
        clientQuery(api, (client) => client.postTeam(form_data)),
      invalidatesTags: ["Team"],
    }),
    updateTeam: build.mutation<
      unknown,
      { teamID: number | string; form_data: TeamPut }
    >({
      queryFn: ({ teamID, form_data }, api) =>
        clientQuery(api, (client) =>
          client.updateTeam(Number(teamID), form_data),
        ),
      invalidatesTags: ["Team"],
    }),
    deleteTeam: build.mutation<void, number | string>({
      queryFn: (team_id, api) =>
        clientQuery(api, (client) => client.deleteTeam(Number(team_id))),
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
