/**
 * Multimessenger Astronomical Detectors (MMADetectors).
 *
 * RTK Query conversion of the old `FETCH_MMADETECTOR(S)` duck. Endpoints are
 * injected into the central `skyportalApi`. The single-detector detail query
 * (`getMMADetector`) provides the `MMADetector` tag; the list query
 * (`getMMADetectors`) provides the `MMADetectors` tag. Creating a detector is a
 * mutation that invalidates the `MMADetectors` tag so the list refetches.
 *
 * The websocket `REFRESH_MMADETECTOR` / `REFRESH_MMADETECTOR_LIST` messages are
 * bridged to cache invalidation via `invalidateOnMessage`. The old handler
 * gated the single-detector refresh on the loaded detector id matching the
 * pushed one; with RTK Query, invalidating the `MMADetector` tag only refetches
 * whichever detector detail query is currently mounted.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import { components } from "../types/api";

export type MMADetector = components["schemas"]["MMADetector"];

export const mmadetectorApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getMMADetector: build.query<MMADetector, number | string>({
      query: (id) => `api/mmadetector/${id}`,
      providesTags: ["MMADetector"],
    }),
    getMMADetectors: build.query<MMADetector[], void>({
      query: () => "api/mmadetector",
      providesTags: ["MMADetectors"],
    }),
    submitMMADetector: build.mutation<unknown, Record<string, unknown>>({
      query: (run) => ({
        url: "api/mmadetector",
        method: "POST",
        body: run,
      }),
      invalidatesTags: ["MMADetectors"],
    }),
  }),
});

// Websocket-driven invalidation: the old handler refetched the loaded detector
// (REFRESH_MMADETECTOR, gated on the loaded id matching the pushed one) or the
// whole list (REFRESH_MMADETECTOR_LIST).
invalidateOnMessage("skyportal/REFRESH_MMADETECTOR", () => ["MMADetector"]);
invalidateOnMessage("skyportal/REFRESH_MMADETECTOR_LIST", () => [
  "MMADetectors",
]);

export const {
  useGetMMADetectorQuery,
  useGetMMADetectorsQuery,
  useSubmitMMADetectorMutation,
} = mmadetectorApi;
