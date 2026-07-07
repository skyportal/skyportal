/**
 * Skymap triggers (the observation-plan "skymap trigger" API).
 *
 * RTK Query conversion of the old `REQUEST_API_SKYMAP_TRIGGERS` duck. The
 * endpoints are injected into the central `skyportalApi`. The GET fetches the
 * trigger payload for an allocation; post/delete are mutations that invalidate
 * the `Localizations`/`Observations` tags so dependent listings refetch.
 */
import { skyportalApi } from "../api/skyportalApi";
import type { RouteData } from "../types/routeSchemaMap";

export interface SkymapTriggers {
  trigger_names?: string[] | undefined;
  [key: string]: unknown;
}

export interface RequestSkymapTriggersArg {
  id: number | string;
  params?: Record<string, unknown> | undefined;
}

export interface PostSkymapTriggerArg {
  allocation_id: number | string;
  localization_id: number | string | null;
  [key: string]: unknown;
}

export interface DeleteSkymapTriggerArg {
  id: number | string;
  params?: Record<string, unknown> | undefined;
}

const buildQueryString = (params: Record<string, unknown>): string => {
  const filtered: Record<string, string> = {};
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== false) {
      filtered[key] = String(value);
    }
  });
  const queryString = new URLSearchParams(filtered).toString();
  return queryString ? `?${queryString}` : "";
};

export const skymapTriggersApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getApiSkymapTriggers: build.query<
      RouteData<"GET /api/skymap_trigger/{allocation_id}">,
      RequestSkymapTriggersArg
    >({
      query: ({ id, params = { triggersOnly: true } }) =>
        `api/skymap_trigger/${id}${buildQueryString(params)}`,
      providesTags: ["Localizations", "Observations"],
    }),
    postApiSkymapTrigger: build.mutation<unknown, PostSkymapTriggerArg>({
      query: (data) => ({
        url: "api/skymap_trigger",
        method: "POST",
        body: data,
      }),
      invalidatesTags: ["Localizations", "Observations"],
    }),
    deleteApiSkymapTrigger: build.mutation<unknown, DeleteSkymapTriggerArg>({
      query: ({ id, params = {} }) => ({
        url: `api/skymap_trigger/${id}`,
        method: "DELETE",
        body: params,
      }),
      invalidatesTags: ["Localizations", "Observations"],
    }),
  }),
});

export const {
  useGetApiSkymapTriggersQuery,
  usePostApiSkymapTriggerMutation,
  useDeleteApiSkymapTriggerMutation,
} = skymapTriggersApi;
