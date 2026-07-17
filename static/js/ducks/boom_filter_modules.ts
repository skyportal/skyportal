import { skyportalApi } from "../api/skyportalApi";
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
        `api/boom/filter_modules?survey=${survey}&elements=schema`,
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
        `api/boom/filter_modules?elements=${elements}` +
        (survey ? `&survey=${survey}` : ""),
    }),
    postFilterElement: build.mutation<
      any,
      { name: string; data: any; elements: string }
    >({
      query: ({ name, data, elements }) => ({
        url: `api/boom/filter_modules/${name}`,
        method: "POST",
        body: { data, elements },
      }),
    }),
    putFilterElement: build.mutation<
      any,
      { name: string; data: any; elements: string }
    >({
      query: ({ name, data, elements }) => ({
        url: `api/boom/filter_modules/${name}`,
        method: "PUT",
        body: { data, elements },
      }),
    }),
  }),
});

export const {
  useGetFilterSchemaQuery,
  useLazyGetFilterElementsQuery,
  usePostFilterElementMutation,
  usePutFilterElementMutation,
} = boomFilterModulesApi;

// Shared read of the filter schema for the current boom filter version's survey.
// Replaces the ambient `state.filter_modules.schema` slice; RTK Query dedupes so
// the builder and its condition components share one request/cache entry.
export const useFilterSchema = () => {
  const { data: filterVersion } = useBoomFilterVersion();
  const survey = filterVersion?.stream?.name?.split(" ")[0];
  return useGetFilterSchemaQuery(survey ?? "", { skip: !survey });
};
