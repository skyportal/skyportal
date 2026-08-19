/**
 * Skymap triggers (the observation-plan "skymap trigger" API).
 *
 * RTK Query conversion of the old `REQUEST_API_SKYMAP_TRIGGERS` duck, calling
 * the typed `skyportal-js` client. The GET fetches the queued trigger names for
 * an allocation; post/delete are mutations that invalidate the
 * `Localizations`/`Observations` tags so dependent listings refetch.
 */
import type { SkymapTriggerQueue } from "skyportal-js/SkymapTriggers";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";

export type SkymapTriggers = SkymapTriggerQueue;

export interface RequestSkymapTriggersArg {
  id: number | string;
}

export interface PostSkymapTriggerArg {
  allocation_id: number | string;
  localization_id: number | string;
  integrated_probability?: number;
}

export interface DeleteSkymapTriggerArg {
  id: number | string;
  params: { trigger_name: string };
}

export const skymapTriggersApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getApiSkymapTriggers: build.query<
      SkymapTriggerQueue,
      RequestSkymapTriggersArg
    >({
      queryFn: ({ id }, api) =>
        clientQuery(api, (client) => client.fetchSkymapTriggers(Number(id))),
      providesTags: ["Localizations", "Observations"],
    }),
    postApiSkymapTrigger: build.mutation<void, PostSkymapTriggerArg>({
      queryFn: (
        { allocation_id, localization_id, integrated_probability },
        api,
      ) =>
        clientQuery(api, (client) =>
          client.postSkymapTrigger(
            Number(allocation_id),
            Number(localization_id),
            { integratedProbability: integrated_probability },
          ),
        ),
      invalidatesTags: ["Localizations", "Observations"],
    }),
    deleteApiSkymapTrigger: build.mutation<void, DeleteSkymapTriggerArg>({
      queryFn: ({ id, params }, api) =>
        clientQuery(api, (client) =>
          client.deleteSkymapTrigger(Number(id), params.trigger_name),
        ),
      invalidatesTags: ["Localizations", "Observations"],
    }),
  }),
});

export const {
  useGetApiSkymapTriggersQuery,
  usePostApiSkymapTriggerMutation,
  useDeleteApiSkymapTriggerMutation,
} = skymapTriggersApi;
