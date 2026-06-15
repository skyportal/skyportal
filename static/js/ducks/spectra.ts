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

export const spectraApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
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
  useFetchSourceSpectraQuery,
  useLazyFetchSourceSpectraQuery,
  useParseASCIISpectrumMutation,
  useAddSyntheticPhotometryMutation,
  useDeleteSpectrumMutation,
  useUploadASCIISpectrumMutation,
  useDeleteAnnotationMutation,
} = spectraApi;
