/**
 * Recurring APIs.
 *
 * RTK Query conversion of the old `FETCH_RECURRING_APIS_LIST` /
 * `SUBMIT_RECURRING_API` / `DELETE_RECURRING_API` duck. The list query keeps the
 * old slice shape implicitly: consumers read the returned array directly. Submit
 * and delete are mutations that invalidate the `RecurringAPIs` tag so the list
 * refetches.
 *
 * The websocket `REFRESH_RECURRING_APIS` message is bridged to cache
 * invalidation via `invalidateOnMessage`.
 */
import type {
  RecurringApi,
  RecurringApiPost,
} from "skyportal-js/RecurringApis";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

export const recurringAPIsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    // The handler takes no query parameters; the old duck passed params that
    // the server ignored.
    getRecurringAPIs: build.query<RecurringApi[], void>({
      queryFn: (_arg, api) =>
        clientQuery(api, (client) => client.fetchRecurringApis()),
      providesTags: ["RecurringAPIs"],
    }),
    submitRecurringAPI: build.mutation<{ id: number }, RecurringApiPost>({
      queryFn: (run, api) =>
        clientQuery(api, (client) => client.postRecurringApi(run)),
      invalidatesTags: ["RecurringAPIs"],
    }),
    deleteRecurringAPI: build.mutation<void, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, (client) => client.deleteRecurringApi(Number(id))),
      invalidatesTags: ["RecurringAPIs"],
    }),
  }),
});

// Websocket: old handler refetched the list on REFRESH_RECURRING_APIS.
invalidateOnMessage("skyportal/REFRESH_RECURRING_APIS", () => [
  "RecurringAPIs",
]);

export const {
  useGetRecurringAPIsQuery,
  useSubmitRecurringAPIMutation,
  useDeleteRecurringAPIMutation,
} = recurringAPIsApi;
