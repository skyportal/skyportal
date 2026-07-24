/**
 * Source spectra.
 *
 * RTK Query conversion of the old `FETCH_SOURCE_SPECTRA` duck. The query fetches
 * a source's spectra and is tagged `Spectra`; the mutations that change spectra
 * (delete, upload, synthetic photometry, delete annotation) invalidate it so the
 * list refetches. `parseASCIISpectrum` is a mutation whose result the caller
 * reads via `.unwrap()` (it was never cached in the old reducer beyond `parsed`).
 *
 * The websocket `REFRESH_SOURCE_SPECTRA` message is bridged to `Spectra` tag
 * invalidation via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

const REFRESH_SOURCE_SPECTRA = "skyportal/REFRESH_SOURCE_SPECTRA";

export interface Spectrum {
  id: number;
  obj_id: string;
  [key: string]: any;
}

export interface BulkSpectraSource {
  id: string;
  redshift: number | null;
  first_detected_mjd: number | null;
  peak_mjd: number | null;
  tns_discovery_date: string | null;
}

export interface BulkSpectrum {
  obj_id: string;
  observed_at: string | null;
  wavelengths: number[];
  fluxes: number[];
}

export interface BulkSpectraArgs {
  group_id?: number;
  obj_ids?: string[];
  classifications?: string[];
  classificationProbThreshold?: number;
  maxSources?: number;
}

export const spectraApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // Slim spectra + per-source phase anchors for a whole source set in one
    // request (group / object list / classification), for phase-stacked plots.
    getBulkSpectra: build.query<
      {
        sources: BulkSpectraSource[];
        spectra: BulkSpectrum[];
        truncated: boolean;
      },
      BulkSpectraArgs
    >({
      query: (body) => ({ url: "/api/spectra/bulk", method: "POST", body }),
      providesTags: ["Spectra"],
    }),
    // The spectrum shape is highly dynamic across SkyPortal apps; consumers read
    // many optional fields, so the element type is `any` (the `Spectrum`
    // interface above documents the stable fields).
    fetchSourceSpectra: build.query<
      any[],
      { id: number | string; normalization?: string | null }
    >({
      query: ({ id, normalization = null }) =>
        `/api/sources/${id}/spectra${
          normalization
            ? `?normalization=${normalization}&sortBy=observed_at&order=asc`
            : ""
        }`,
      transformResponse: (data: { spectra?: Spectrum[] }) =>
        data?.spectra ?? [],
      providesTags: ["Spectra"],
    }),
    // Single spectrum WITH the raw uploaded file (original_file_string), which is
    // deferred from the source-spectra payload. Fetched on demand for download.
    fetchSpectrumOriginalFile: build.query<any, number | string>({
      query: (id) => `/api/spectra/${id}?includeOriginalFile=true`,
    }),
    parseASCIISpectrum: build.mutation<
      RouteData<"POST /api/spectrum/parse/ascii">,
      any
    >({
      query: (data) => ({
        url: "/api/spectrum/parse/ascii",
        method: "POST",
        body: data,
      }),
    }),
    addSyntheticPhotometry: build.mutation<
      RouteData<"POST /api/spectra/synthphot/{spectrum_id}">,
      { id: number | string; formData?: { [key: string]: any } }
    >({
      query: ({ id, formData = {} }) => ({
        url: `/api/spectra/synthphot/${id}`,
        method: "POST",
        body: formData,
      }),
      invalidatesTags: ["Spectra"],
    }),
    deleteSpectrum: build.mutation<
      RouteData<"DELETE /api/spectrum/{spectrum_id}">,
      number | string
    >({
      query: (id) => ({
        url: `/api/spectrum/${id}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Spectra"],
    }),
    uploadASCIISpectrum: build.mutation<unknown, any>({
      query: (data) => ({
        url: "/api/spectrum/ascii",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Spectra"],
    }),
    deleteAnnotation: build.mutation<
      unknown,
      { id: number | string; annotationID: number | string }
    >({
      query: ({ id, annotationID }) => ({
        url: `/api/spectra/${id}/annotations/${annotationID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Spectra"],
    }),
  }),
});

// Websocket-driven invalidation: refresh spectra on REFRESH_SOURCE_SPECTRA.
invalidateOnMessage(REFRESH_SOURCE_SPECTRA, (payload) =>
  payload?.obj_internal_key != null ? ["Spectra"] : null,
);

export const {
  useGetBulkSpectraQuery,
  useFetchSourceSpectraQuery,
  useLazyFetchSourceSpectraQuery,
  useLazyFetchSpectrumOriginalFileQuery,
  useParseASCIISpectrumMutation,
  useAddSyntheticPhotometryMutation,
  useDeleteSpectrumMutation,
  useUploadASCIISpectrumMutation,
  useDeleteAnnotationMutation,
} = spectraApi;
