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
import type {
  BulkSpectraResponse,
  ParsedSpectrum,
  PostSpectraBulkOptions,
  SpectrumAsciiParse,
  SpectrumAsciiPost,
} from "skyportal-js/Spectra";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

const REFRESH_SOURCE_SPECTRA = "skyportal/REFRESH_SOURCE_SPECTRA";

export interface Spectrum {
  id: number;
  obj_id: string;
  [key: string]: any;
}

export type { BulkSpectraSource, BulkSpectrum } from "skyportal-js/Spectra";

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
    getBulkSpectra: build.query<BulkSpectraResponse, BulkSpectraArgs>({
      queryFn: (
        {
          group_id,
          obj_ids,
          classifications,
          classificationProbThreshold,
          maxSources,
        },
        api,
      ) =>
        clientQuery(api, (client) =>
          client.postSpectraBulk({
            groupId: group_id,
            objIds: obj_ids,
            classifications,
            classificationProbThreshold,
            maxSources,
          } satisfies PostSpectraBulkOptions),
        ),
      providesTags: ["Spectra"],
    }),
    // The spectrum shape is highly dynamic across SkyPortal apps; consumers read
    // many optional fields, so the element type is `any` (the `Spectrum`
    // interface above documents the stable fields).
    fetchSourceSpectra: build.query<
      any[],
      { id: number | string; normalization?: string | null }
    >({
      queryFn: ({ id, normalization = null }, api) =>
        clientQuery(api, (client) =>
          client.fetchSpectra(String(id), {
            ...(normalization ? { normalization } : {}),
          }),
        ),
      providesTags: ["Spectra"],
    }),
    // Single spectrum WITH the raw uploaded file (original_file_string), which is
    // deferred from the source-spectra payload. Fetched on demand for download.
    fetchSpectrumOriginalFile: build.query<any, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) =>
          client.fetchSpectrum(Number(id), { includeOriginalFile: true }),
        ),
    }),
    parseASCIISpectrum: build.mutation<ParsedSpectrum, SpectrumAsciiParse>({
      queryFn: (data, api) =>
        clientQuery(api, (client) => client.parseSpectrumAscii(data)),
    }),
    addSyntheticPhotometry: build.mutation<
      void,
      { id: number | string; formData?: { filters?: string[] } }
    >({
      queryFn: ({ id, formData = {} }, api) =>
        clientQuery(api, (client) =>
          client.postSyntheticPhotometry(Number(id), formData.filters ?? []),
        ),
      invalidatesTags: ["Spectra"],
    }),
    deleteSpectrum: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteSpectrum(Number(id))),
      invalidatesTags: ["Spectra"],
    }),
    uploadASCIISpectrum: build.mutation<{ id: number }, SpectrumAsciiPost>({
      queryFn: (data, api) =>
        clientQuery(api, (client) => client.postSpectrumAscii(data)),
      invalidatesTags: ["Spectra"],
    }),
    deleteSpectrumAnnotation: build.mutation<
      void,
      { id: number | string; annotationID: number | string }
    >({
      queryFn: ({ id, annotationID }, api) =>
        clientQuery(api, (client) =>
          client.deleteAnnotation(id, Number(annotationID), {
            resourceType: "spectra",
          }),
        ),
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
  useLazyFetchSpectrumOriginalFileQuery,
  useParseASCIISpectrumMutation,
  useAddSyntheticPhotometryMutation,
  useDeleteSpectrumMutation,
  useUploadASCIISpectrumMutation,
  useDeleteSpectrumAnnotationMutation,
} = spectraApi;
