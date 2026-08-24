/**
 * Per-user cuts for event-to-event associations.
 *
 * Which pairs of messengers count as coincident is a science choice -- a
 * neutrino arrives within seconds of a gravitational wave, a GRB within
 * minutes -- so the rules belong to a user rather than to the site config.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface GcnAssociationRule {
  id: number;
  detector_type_1: string;
  detector_type_2: string;
  days: number;
  min_consistency: number;
}

export const gcnAssociationRuleApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGcnAssociationRules: build.query<GcnAssociationRule[], void>({
      query: () => "api/gcn_association_rules",
      providesTags: ["GcnAssociationRules"],
    }),
    saveGcnAssociationRule: build.mutation<
      { id: number },
      Omit<GcnAssociationRule, "id">
    >({
      query: (rule) => ({
        url: "api/gcn_association_rules",
        method: "POST",
        body: rule,
      }),
      invalidatesTags: ["GcnAssociationRules"],
    }),
    deleteGcnAssociationRule: build.mutation<unknown, number>({
      query: (id) => ({
        url: `api/gcn_association_rules/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["GcnAssociationRules"],
    }),
  }),
});

invalidateOnMessage("skyportal/REFRESH_GCN_ASSOCIATION_RULES", () => [
  "GcnAssociationRules",
]);

export const {
  useGetGcnAssociationRulesQuery,
  useSaveGcnAssociationRuleMutation,
  useDeleteGcnAssociationRuleMutation,
} = gcnAssociationRuleApi;
