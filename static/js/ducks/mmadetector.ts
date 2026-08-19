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
import type { MmaDetector, MmaDetectorPost } from "skyportal-js/MmaDetectors";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const mmadetectorApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getMMADetector: build.query<MmaDetector, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.fetchMmaDetector(Number(id))),
      providesTags: ["MMADetector"],
    }),
    getMMADetectors: build.query<MmaDetector[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchMmaDetectors()),
      providesTags: ["MMADetectors"],
    }),
    submitMMADetector: build.mutation<{ id: number }, MmaDetectorPost>({
      queryFn: (run, api) =>
        clientQuery(api, (client) => client.postMmaDetector(run)),
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
