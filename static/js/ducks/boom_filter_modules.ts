/**
 * Broker filter-builder "modules" duck: the alert-schema and the reusable
 * building blocks (variables / listVariables / switchCases / blocks) the
 * pipeline-filter builder composes.
 *
 * RTK Query conversion of the old `boom_filter_modules` action/reducer duck: the
 * ambient `state.filter_modules.schema` slice becomes the shared
 * `useFilterSchema()` hook. Endpoints target the active broker via
 * `brokerFilterBase()` (`/api/brokers/{id}`).
 */
import { skyportalApi } from "../api/skyportalApi";
import { brokerFilterBase } from "./brokerFilterTarget";
import { useBoomFilterVersion } from "./boom_filter";
import {
  ztf_crossmatch_fields,
  lsst_crossmatch_fields,
} from "../constants/crossmatch";

// Append survey-specific cross-match fields to a fetched schema.
const patchSchema = (schema: any) => {
  if (!schema) return schema;

  const patchedSchema = JSON.parse(JSON.stringify(schema));

  if (patchedSchema.fields) {
    if (patchedSchema.name.includes("Ztf")) {
      patchedSchema.fields.push(ztf_crossmatch_fields);
    }
    if (patchedSchema.name.includes("Lsst")) {
      patchedSchema.fields.push(lsst_crossmatch_fields);
    }
  }

  return patchedSchema;
};

export const boomFilterModulesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getFilterSchema: build.query<any, string>({
      query: (survey) =>
        `${brokerFilterBase()}/filter_modules?survey=${survey}&elements=schema`,
      transformResponse: (response: any) => {
        try {
          return patchSchema(response?.schema);
        } catch (error) {
          console.error("Error parsing schema JSON:", error);
          return null;
        }
      },
    }),
    getFilterElements: build.query<any, { elements: string; survey?: string }>({
      query: ({ elements, survey }) =>
        `${brokerFilterBase()}/filter_modules?elements=${elements}${
          survey ? `&survey=${survey}` : ""
        }`,
    }),
    // Single module by name, for name-availability checks. Returns null when
    // there is no such module.
    getFilterElementByName: build.query<
      any,
      { name: string; elements: string }
    >({
      query: ({ name, elements }) =>
        `${brokerFilterBase()}/filter_modules/${name}?elements=${elements}`,
    }),
    postFilterElement: build.mutation<
      any,
      { name: string; data: any; elements: string }
    >({
      query: ({ name, data, elements }) => ({
        url: `${brokerFilterBase()}/filter_modules/${name}`,
        method: "POST",
        body: { data, elements },
      }),
    }),
    putFilterElement: build.mutation<
      any,
      { name: string; data: any; elements: string }
    >({
      query: ({ name, data, elements }) => ({
        url: `${brokerFilterBase()}/filter_modules/${name}`,
        method: "PUT",
        body: { data, elements },
      }),
    }),
  }),
});

export const {
  useGetFilterSchemaQuery,
  useLazyGetFilterElementsQuery,
  useLazyGetFilterElementByNameQuery,
  usePostFilterElementMutation,
  usePutFilterElementMutation,
} = boomFilterModulesApi;

// Shared read of the filter schema. Defaults to the current filter version's
// survey (the pipeline-filter builder path), but a caller without a filter
// version — e.g. the standalone Lasair query builder — can pass the survey
// explicitly. Replaces the ambient `state.filter_modules.schema` slice; RTK
// Query dedupes so the builder and its condition components share one entry.
export const useFilterSchema = (surveyOverride?: string) => {
  const { data: filterVersion } = useBoomFilterVersion();
  const survey = surveyOverride ?? filterVersion?.stream?.name?.split(" ")[0];
  // Expose the resolved survey alongside the query state so callers can show a
  // clear "no schema for this survey" message when the broker has none.
  return {
    ...useGetFilterSchemaQuery(survey ?? "", { skip: !survey }),
    survey,
  };
};
