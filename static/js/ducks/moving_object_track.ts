import messageHandler from "baselayer/MessageHandler";

import { skyportalApi } from "../api/skyportalApi";

const TRACK_KNOWN_OBJECT = "skyportal/TRACK_KNOWN_OBJECT";

export interface TrackEpoch {
  candid: string;
  jd: number;
  ra: number;
  dec: number;
  mag: number | null;
  band: string | null;
  obs_jd?: number | null;
  ssnamenr?: string | null;
  objectId?: string | null;
  residual_ra?: number | null;
  residual_dec?: number | null;
  fwhm_ratio?: number | null;
  classtar?: number | null;
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
  kind: string | null;
  flags: string[];
  rms_ratio: number | null;
  near_planet: string | null;
  neo_score: number | null;
  orbit: {
    epoch_jd: number | null;
    e: number;
    q: number;
    a: number | null;
    incl: number | null;
    node: number | null;
    peri: number | null;
    mean_anomaly: number | null;
    tp: number | null;
    rms_arcsec: number | null;
    n_fitted: number | null;
    expected_rms_arcsec: number | null;
  } | null;
  activity: {
    fwhm_ratio: number;
    classtar: number | null;
    n_detections: number;
    possible_comet: boolean;
  } | null;
  detections: TrackEpoch[];
  members_withheld: number;
}

export interface TrackMPCSubmission {
  id: number;
  sharing_service_id: number;
  username: string;
  submitter: string | null;
  mpc_status: string | null;
  mpc_submission_id: string | null;
  created_at: string;
}

export interface TrackMPCPreview {
  submissions: TrackMPCSubmission[];
  psv?: string;
  submitter?: string;
  submitters?: string[];
  members_withheld?: number;
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
    getTrackMPC: build.query<
      TrackMPCPreview,
      {
        trackId: string;
        brokerId: number;
        sharingServiceId?: number | undefined;
        submitter?: string | undefined;
        excludeCandids?: string[];
      }
    >({
      query: ({
        trackId,
        brokerId,
        sharingServiceId,
        submitter,
        excludeCandids,
      }) => ({
        url: `api/moving_object/track/${encodeURIComponent(trackId)}/mpc`,
        params: {
          broker_id: brokerId,
          ...(sharingServiceId != null
            ? { sharing_service_id: sharingServiceId }
            : {}),
          ...(submitter ? { submitter } : {}),
          ...(excludeCandids?.length
            ? { exclude_candids: excludeCandids.join(",") }
            : {}),
        },
      }),
      extraOptions: { suppressErrorNotification: true },
      providesTags: (_result, _error, { trackId }) => [
        { type: "TrackMPC", id: trackId },
      ],
    }),
    submitTrackToMPC: build.mutation<
      { id: number },
      {
        trackId: string;
        sharing_service_id: number;
        obj_id: string;
        broker_id: number;
        submitter?: string | undefined;
        exclude_candids?: string[];
        psv?: string | undefined;
        submission_type: "regular" | "neo_candidate" | "new_comet";
      }
    >({
      query: ({ trackId, ...body }) => ({
        url: `api/moving_object/track/${encodeURIComponent(trackId)}/mpc`,
        method: "POST",
        body,
      }),
      invalidatesTags: (_result, _error, { trackId }) => [
        { type: "TrackMPC", id: trackId },
      ],
    }),
    measureTrackCutouts: build.mutation<
      TrackMeasurement,
      { detections: TrackEpoch[]; broker_id: number; survey?: string }
    >({
      query: (body) => ({
        url: "api/moving_object/track",
        method: "POST",
        body: { ...body, measure_cutouts: true, include_images: true },
      }),
    }),
    // Filled over the websocket: JPL takes minutes, longer than a request may.
    getTrackKnownObject: build.query<KnownObjectVerdict | null, string>({
      queryFn: () => ({ data: null }),
    }),
    checkTrackKnownObject: build.mutation<
      unknown,
      { trackId: string; broker_id: number; survey?: string }
    >({
      query: ({ trackId, ...body }) => ({
        url: `api/moving_object/track/${encodeURIComponent(trackId)}/known`,
        method: "POST",
        body,
      }),
    }),
  }),
});

messageHandler.add((actionType: string, payload: any, dispatch: any) => {
  if (actionType !== TRACK_KNOWN_OBJECT) return;
  dispatch(
    movingObjectTrackApi.util.upsertQueryData(
      "getTrackKnownObject",
      payload.track_id,
      payload.known_object,
    ),
  );
});

export const {
  useGetMovingObjectTrackQuery,
  useGetTrackMPCQuery,
  useSubmitTrackToMPCMutation,
  useMeasureTrackGeometryMutation,
  useMeasureTrackCutoutsMutation,
  useGetTrackKnownObjectQuery,
  useCheckTrackKnownObjectMutation,
} = movingObjectTrackApi;
