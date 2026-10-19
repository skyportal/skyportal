import { skyportalApi } from "../api/skyportalApi";

export interface TrackEpoch {
  candid: string;
  jd: number;
  ra: number;
  dec: number;
  mag: number | null;
  band: string | null;
  ssnamenr?: string | null;
  snr?: number;
  centroid_offset_px?: number;
  peak?: number;
  png?: string | null;
}

export interface TrackLookup {
  id: string;
  n_detections: number | null;
  n_nights: number | null;
  arc_days: number | null;
  designation: string | null;
  detections: TrackEpoch[];
  members_withheld: number;
}

/** An epoch whose pixels were measured. Geometry-only results have neither. */
export interface MeasuredEpoch extends TrackEpoch {
  snr: number;
  centroid_offset_px: number;
}

export interface KnownObjectMatch {
  name: string;
  identified: boolean;
  nearest_arcsec: number;
  offset_drift_arcsec: number;
  rate_difference_arcsec_per_hour: number | null;
  motion_agrees: boolean;
  epochs: number;
  reason: string;
}

/**
 * Three states, never two: `known` true is a recovery, false is a clean
 * negative the control vouched for, and null means the check did not run.
 */
export interface KnownObjectVerdict {
  known: boolean | null;
  verified: boolean;
  matches: KnownObjectMatch[];
  nearby: KnownObjectMatch[];
  errors: string[];
  reason: string;
}

export interface TrackAnalysis {
  detections: TrackEpoch[];
  failures: { candid: string; error: string }[];
  position_angles: number[];
  motion: {
    rms_arcsec: number;
    degree: number;
    n_points: number;
    arc_days: number;
  } | null;
  band_flux: { jd: number; bands: [string, string]; agrees: boolean }[];
  arc_days: number;
  n_detections: number;
  n_object_ids: number;
  known_object?: KnownObjectVerdict | null;
}

/** The same, once the cutouts have been measured. */
export interface TrackMeasurement extends TrackAnalysis {
  detections: MeasuredEpoch[];
}

export const movingObjectTrackApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getMovingObjectTrack: build.query<
      TrackLookup,
      { trackId: string; brokerId?: number; survey?: string }
    >({
      query: ({ trackId, brokerId, survey }) => ({
        url: `api/moving_object/track/${encodeURIComponent(trackId)}`,
        params: {
          ...(brokerId != null ? { broker_id: brokerId } : {}),
          ...(survey ? { survey } : {}),
        },
      }),
    }),
    // Geometry only: no cutouts fetched, so it is cheap enough for a scanning
    // page. Measuring is the expensive half and is asked for separately.
    measureTrackGeometry: build.mutation<
      TrackAnalysis,
      { detections: TrackEpoch[]; broker_id: number; survey?: string }
    >({
      query: (body) => ({
        url: "api/moving_object/track",
        method: "POST",
        body: { ...body, measure_cutouts: false, include_images: false },
      }),
    }),
    measureTrackCutouts: build.mutation<
      TrackMeasurement,
      { detections: TrackEpoch[]; broker_id: number; survey?: string }
    >({
      query: (body) => ({
        url: "api/moving_object/track",
        method: "POST",
        // Vetting is exactly when the known-object check is worth its
        // JPL round trips.
        body: {
          ...body,
          measure_cutouts: true,
          include_images: true,
          check_known: true,
        },
      }),
    }),
  }),
});

export const {
  useGetMovingObjectTrackQuery,
  useMeasureTrackGeometryMutation,
  useMeasureTrackCutoutsMutation,
} = movingObjectTrackApi;
