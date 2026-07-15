/**
 * RTK Query API definition for SkyPortal.
 *
 * This replaces the hand-rolled `ducks/*` pattern (action constants + thunk +
 * reducer + manual loading/error/cache) with declarative endpoints. Each duck
 * file calls `skyportalApi.injectEndpoints(...)` to add its own endpoints, so
 * the migration stays modular and one duck per file is preserved.
 *
 * Two SkyPortal-specific concerns are handled here once, centrally:
 *
 *  1. The response envelope. Every backend response is wrapped by
 *     `BaseHandler.success`/`error` as `{ status, message, data }`, and the HTTP
 *     status is 200 even for application-level errors. `skyportalBaseQuery`
 *     unwraps `.data` on success and converts `status !== "success"` into an
 *     RTK Query error, mirroring the old `API.ts` behaviour (including the
 *     error notification).
 *
 *  2. WebSocket-driven invalidation. The backend pushes refresh messages over
 *     the websocket; `wsInvalidation.ts` bridges those to `invalidateTags` so
 *     active queries refetch. Tags are declared in `tagTypes` below.
 */
import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import type {
  BaseQueryFn,
  FetchArgs,
  FetchBaseQueryError,
} from "@reduxjs/toolkit/query/react";

import { showNotification } from "baselayer/components/Notifications";

/**
 * The `{ status, message, data, version }` envelope every endpoint returns.
 * `version` is injected into *every* response (success and error) by
 * SkyPortal's `BaseHandler.success`/`error` override, so it rides alongside
 * `data` rather than inside it.
 */
interface ApiEnvelope<T = unknown> {
  status: "success" | "error";
  message?: string;
  data: T;
  version?: string;
}

/**
 * Meta passed to `transformResponse(data, meta, arg)`. Mirrors the standard
 * fetch meta (`request`/`response`) plus the global `version` envelope field
 * (stripped from `data`) so endpoints that need it — the few that surface the
 * running SkyPortal version — can merge it back in without every endpoint
 * paying for it. Fields are explicitly `| undefined` to satisfy the project's
 * `exactOptionalPropertyTypes` setting (the fetch meta is absent on app errors).
 */
export interface SkyportalMeta {
  request?: Request | undefined;
  response?: Response | undefined;
  version?: string | undefined;
}

const rawBaseQuery = fetchBaseQuery({
  baseUrl: "/",
  credentials: "same-origin",
});

/**
 * Wraps `fetchBaseQuery` to (a) unwrap the SkyPortal `{status,data}` envelope
 * and (b) treat `status: "error"` (returned with HTTP 200) as an error. On any
 * error it dispatches the same `showNotification(...)` the old `API.ts` did, so
 * user-facing error behaviour is unchanged.
 */
const skyportalBaseQuery: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError,
  object,
  SkyportalMeta
> = async (args, api, extraOptions) => {
  const result = await rawBaseQuery(args, api, extraOptions);

  if (result.error) {
    const message =
      (result.error.data as ApiEnvelope | undefined)?.message ??
      `Request failed (${result.error.status})`;
    api.dispatch(showNotification(`${message}`, "error"));
    return result;
  }

  const envelope = result.data as ApiEnvelope;
  if (envelope?.status !== "success") {
    const message = envelope?.message ?? "Unknown API error";
    api.dispatch(showNotification(`${message}`, "error"));
    return {
      error: {
        status: "CUSTOM_ERROR",
        error: message,
        data: envelope,
      } satisfies FetchBaseQueryError,
    };
  }

  return {
    data: envelope.data,
    meta: { ...result.meta, version: envelope.version },
  };
};

/**
 * Cache tags. Each migrated duck adds the tag(s) it provides/invalidates here.
 * Keep this list in sync as endpoints are injected; an endpoint referencing a
 * tag not declared here is a runtime warning from RTK Query.
 */
export const TAG_TYPES = [
  "SysInfo",
  "DBStats",
  "DBInfo",
  "Acls",
  "Earthquake",
  "Earthquakes",
  "GcnTags",
  "Instruments",
  "MMADetectors",
  "ObservingRun",
  "Profile",
  "Source",
  "SourcePosition",
  "Stream",
  "Telescopes",
  "Weather",
  "Allocation",
  "Config",
  "EarthquakeStatus",
  "FollowupRequest",
  "Group",
  "Invitation",
  "QueuedObservation",
  "Role",
  "SourceCounts",
  "TopSaver",
  "PublicSourcePage",
  "DefaultFollowupRequest",
  "DefaultAnalysis",
  "Galaxy",
  "GroupAdmissionRequest",
  "Localization",
  "NewsFeed",
  "Photometry",
  "RecentGcnEvent",
  "SharingService",
  "SharingServiceSubmission",
  "PublicRelease",
  "AnalysisService",
  "DefaultGcnTag",
  "Ephemeris",
  "GcnEvent",
  "LocalizationProperties",
  "RecentSource",
  "Shift",
  "SourceInGcn",
  "SurveyEfficiencyObservationPlan",
  "UserNotification",
  "ScanReportItem",
  "DefaultObservationPlan",
  "Favorite",
  "Instrument",
  "LocalizationTag",
  "ObservationPlan",
  "PhotometryValidation",
  "RecurringAPI",
  "SpatialCatalog",
  "SurveyEfficiencyObservation",
  "User",
  "Candidate",
  "CatalogQuery",
  "DefaultSurveyEfficiency",
  "Filter",
  "Observations",
  "RejectedCandidates",
  "Taxonomies",
  "ScanReport",
  "FollowupApi",
  "SpatialCatalogs",
  "Taxonomy",
  "AnalysisServices",
  "Galaxies",
  "MMADetector",
  "Telescope",
  "AnnotationsInfo",
  "AltdataInfo",
  "EnumTypes",
  "InstrumentLog",
  "Streams",
  "TopSavers",
  "Candidates",
  "QueuedObservations",
  "Sources",
  "UserNotifications",
  "Observation",
  "FetchDefaultGcnTags",
  "FetchPublicSourcePages",
  "RecurringAPIs",
  "Reminder",
  "ObjTagOption",
  "ObjTag",
  "SourceTag",
  "SourceView",
  "Filters",
  "InstrumentForms",
  "InstrumentObsplanForms",
  "GcnEventInstruments",
  "Team",
  "GcnEventObservation",
  "GcnProperties",
  "Invitations",
  "Localizations",
  "Spectra",
  "UserManagement",
] as const;

export const skyportalApi = createApi({
  reducerPath: "skyportalApi",
  baseQuery: skyportalBaseQuery,
  tagTypes: TAG_TYPES,
  // Endpoints are added per-duck via `injectEndpoints`.
  endpoints: () => ({}),
});
