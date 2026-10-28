import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";
import type { components } from "../types/api";

export type InstanceManager = components["schemas"]["InstanceManagerResponse"];

export const instanceManagersApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getInstanceManagers: build.query<InstanceManager[], void>({
      query: () => "api/instance_managers",
      transformResponse: (data: { managers: InstanceManager[] }) =>
        data.managers,
      providesTags: ["InstanceManagers"],
    }),
    addInstanceManager: build.mutation<unknown, number>({
      query: (userId) => ({
        url: "api/instance_managers",
        method: "POST",
        body: { user_id: userId },
      }),
      invalidatesTags: ["InstanceManagers"],
    }),
    updateInstanceManager: build.mutation<
      unknown,
      { userId: number; show_email: boolean }
    >({
      query: ({ userId, ...body }) => ({
        url: `api/instance_managers/${userId}`,
        method: "PATCH",
        body,
      }),
      invalidatesTags: ["InstanceManagers"],
    }),
    removeInstanceManager: build.mutation<unknown, number>({
      query: (userId) => ({
        url: `api/instance_managers/${userId}`,
        method: "DELETE",
      }),
      invalidatesTags: ["InstanceManagers"],
    }),
  }),
});

invalidateOnMessage("skyportal/REFRESH_INSTANCE_MANAGERS", () => [
  "InstanceManagers",
]);

export const {
  useGetInstanceManagersQuery,
  useAddInstanceManagerMutation,
  useUpdateInstanceManagerMutation,
  useRemoveInstanceManagerMutation,
} = instanceManagersApi;
