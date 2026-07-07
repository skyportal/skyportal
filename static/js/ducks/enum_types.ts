/**
 * Enum types (allowed bandpasses, API classnames, analysis types, etc.).
 *
 * RTK Query conversion of the old `FETCH_ENUM_TYPES` duck. The endpoint is
 * injected into the central `skyportalApi`. The backend returns a map of enum
 * names to their allowed values. The old websocket handler refetched on a
 * FETCH_ENUM_TYPES message; here we invalidate the "EnumTypes" tag so the active
 * query refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export type EnumTypes = Record<string, any>;

export const enumTypesApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getEnumTypes: build.query<EnumTypes, void>({
      query: () => "api/enum_types",
      providesTags: ["EnumTypes"],
    }),
  }),
});

// Websocket: old handler refetched enum types on FETCH_ENUM_TYPES.
invalidateOnMessage("skyportal/FETCH_ENUM_TYPES", () => ["EnumTypes"]);

export const { useGetEnumTypesQuery } = enumTypesApi;
