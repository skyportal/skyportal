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
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { RouteData } from "../types/routeSchemaMap";

export const recurringAPIsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getRecurringAPIs: build.query<
      RouteData<"GET /api/recurring_api">,
      Record<string, unknown> | void
    >({
      query: (params) => ({
        url: "api/recurring_api",
        params: params ?? {},
      }),
      providesTags: ["RecurringAPIs"],
    }),
    submitRecurringAPI: build.mutation<unknown, Record<string, unknown>>({
      query: (run) => ({
        url: "api/recurring_api",
        method: "POST",
        body: run,
      }),
      invalidatesTags: ["RecurringAPIs"],
    }),
    deleteRecurringAPI: build.mutation<unknown, number | string>({
      query: (id) => ({
        url: `api/recurring_api/${id}`,
        method: "DELETE",
      }),
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
