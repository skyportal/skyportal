/**
 * Events proposed as the same physical event as this one.
 *
 * The crossmatch service measures the sky-map overlap for every candidate pair;
 * these endpoints read what it found, cut to the reader's own rules, and record
 * a human verdict on it.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface GcnEventAssociation {
  id: number;
  dateobs: string;
  trigger_id: string | null;
  aliases: string[];
  tags: string[];
  detectors: string[];
  overlap: number;
  consistency: number | null;
  dt_days: number;
  status: string;
  explanation: string | null;
}

export const gcnEventAssociationApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getGcnEventAssociations: build.query<
      GcnEventAssociation[],
      { dateobs: string; includeRejected?: boolean }
    >({
      query: ({ dateobs, includeRejected }) =>
        `api/gcn_event/${dateobs}/associations${
          includeRejected ? "?includeRejected=true" : ""
        }`,
      providesTags: ["GcnEventAssociations"],
    }),
    vetGcnEventAssociation: build.mutation<
      unknown,
      {
        dateobs: string;
        association_id: number;
        status: string;
        explanation?: string | null;
      }
    >({
      query: ({ dateobs, association_id, status, explanation }) => ({
        url: `api/gcn_event/${dateobs}/associations/${association_id}`,
        method: "PATCH",
        body: { status, explanation },
      }),
      invalidatesTags: ["GcnEventAssociations"],
    }),
  }),
});

invalidateOnMessage("skyportal/REFRESH_GCNEVENT", () => [
  "GcnEventAssociations",
]);

export const {
  useGetGcnEventAssociationsQuery,
  useVetGcnEventAssociationMutation,
} = gcnEventAssociationApi;
