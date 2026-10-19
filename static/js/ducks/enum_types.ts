/**
 * Enum types (allowed bandpasses, API classnames, analysis types, etc.).
 *
 * RTK Query conversion of the old `FETCH_ENUM_TYPES` duck. The endpoint is
 * injected into the central `skyportalApi`. The backend returns a map of enum
 * names to their allowed values.
 */
import { skyportalApi } from "../api/skyportalApi";

export type EnumTypes = Record<string, any>;

export const enumTypesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getEnumTypes: build.query<EnumTypes, void>({
      query: () => "api/enum_types",
      providesTags: ["EnumTypes"],
    }),
  }),
});

export const { useGetEnumTypesQuery } = enumTypesApi;
