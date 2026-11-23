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

function errorMessage(error: FetchBaseQueryError): string {
  const message = (error.data as ApiEnvelope | undefined)?.message;
  if (message) {
    return message;
  }
  const status =
    error.status === "PARSING_ERROR" ? error.originalStatus : error.status;
  if (status === "FETCH_ERROR") {
    return "Could not reach the server. Check your connection and try again.";
  }
  if (status === "TIMEOUT_ERROR" || status === 504) {
    return "The server took too long to respond. Try again.";
  }
  if (status === 502 || status === 503) {
    return "The server is temporarily unavailable. Try again in a moment.";
  }
  if (typeof status === "number" && status >= 400) {
    return `Request failed (HTTP ${status})`;
  }
  return "Unexpected response from the server. Try reloading the page.";
}

const lastErrorShown = new Map<string, number>();

/**
 * Wraps `fetchBaseQuery` to (a) unwrap the SkyPortal `{status,data}` envelope
 * and (b) treat `status: "error"` (returned with HTTP 200) as an error. On any
 * error it dispatches an error notification, once per message when several
 * requests fail together.
 */
const skyportalBaseQuery: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError,
  object,
  SkyportalMeta
> = async (args, api, extraOptions) => {
  const isGet =
    typeof args === "string" || (args.method ?? "GET").toUpperCase() === "GET";
  let result = await rawBaseQuery(args, api, extraOptions);
  if (result.error?.status === "FETCH_ERROR" && isGet && !api.signal.aborted) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
    result = await rawBaseQuery(args, api, extraOptions);
  }

  // Endpoints that expect misses (e.g. "is this object already a source?") can
  // opt out of the automatic error notification.
  const quiet =
    (extraOptions as { suppressErrorNotification?: boolean })
      ?.suppressErrorNotification || api.signal.aborted;

  const notify = (message: string) => {
    const now = Date.now();
    if (now - (lastErrorShown.get(message) ?? 0) < 3000) {
      return;
    }
    lastErrorShown.set(message, now);
    api.dispatch(showNotification(message, "error"));
  };

  if (result.error) {
    if (!quiet) {
      notify(errorMessage(result.error));
    }
    return result;
  }

  const envelope = result.data as ApiEnvelope;
  if (envelope?.status !== "success") {
    const message = envelope?.message ?? "Unknown API error";
    if (!quiet) {
      notify(`${message}`);
    }
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
  "Assistant",
  "Broker",
  "BrokerCredential",
  "DBStats",
  "DBInfo",
  "Deployments",
  "Discussions",
  "CommentThreads",
  "Topics",
  "Feedback",
  "InstanceManagers",
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
  "SourceInterest",
  "Stream",
  "SuperObj",
  "TrackMPC",
  "Telescopes",
  "TermsOfService",
  "Weather",
  "Allocation",
  "Config",
  "FollowupRequest",
  "Group",
  "Invitation",
  "QueuedObservation",
  "Role",
  "SourceCounts",
  "TopSaver",
  "PublicSourcePage",
  "PublicProfile",
  "UserProfile",
  "DefaultFollowupRequest",
  "DefaultAnalysis",
  "Galaxy",
  "GroupAdmissionRequest",
  "Localization",
  "NewsFeed",
  "Photometry",
  "RecentGcnEvent",
  "RecentGcnExtraction",
  "SharingService",
  "SharingServiceSubmission",
  "PublicRelease",
  "AnalysisService",
  "DefaultGcnTag",
  "Ephemeris",
  "GcnAssociationRules",
  "GcnEventAssociations",
  "GcnEvent",
  "LocalizationProperties",
  "RecentSource",
  "Shift",
  "SourceInGcn",
  "SurveyEfficiencyObservationPlan",
  "UserNotification",
  "UserApplication",
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
  "AssistantQueries",
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
  "DataAvailability",
  "DataAccessRequest",
] as const;

export const skyportalApi = createApi({
  reducerPath: "skyportalApi",
  baseQuery: skyportalBaseQuery,
  tagTypes: TAG_TYPES,
  // Endpoints are added per-duck via `injectEndpoints`.
  endpoints: () => ({}),
});
