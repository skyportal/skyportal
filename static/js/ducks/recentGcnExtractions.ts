/**
 * Recent structured extractions from GCN circulars, for the home-page widget.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type RecentGcnExtraction = {
  id: number;
  origin: string;
  circular_id: number | null;
  created_at: string;
  dateobs: string;
  event_aliases: string[];
  summary: {
    event_name: string | null;
    n_photometry: number;
    n_detections: number;
    bandpasses: string[];
    redshift: number | null;
    classification: string | null;
    ra: number | null;
    dec: number | null;
  };
};

export const recentGcnExtractionsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getRecentGcnExtractions: build.query<RecentGcnExtraction[], void>({
      query: () => "api/internal/recent_gcn_extractions",
      providesTags: ["RecentGcnExtraction"],
    }),
  }),
});

invalidateOnMessage("skyportal/REFRESH_GCNEVENT", () => [
  "RecentGcnExtraction",
]);

export const { useGetRecentGcnExtractionsQuery } = recentGcnExtractionsApi;
