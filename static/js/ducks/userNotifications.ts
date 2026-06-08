/**
 * User notifications (the bell/notifications popover).
 *
 * RTK Query conversion of the old `FETCH_NOTIFICATIONS` duck. The endpoints are
 * injected into the central `skyportalApi`. The list query provides the
 * "UserNotifications" tag; the mutations (mark read/unread, delete, delete all)
 * invalidate it so the list refetches.
 *
 * The old websocket handler refetched notifications on a FETCH_NOTIFICATIONS
 * message; here we invalidate the "UserNotifications" tag so the active query
 * refetches.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

export interface UserNotification {
  id: number;
  text: string;
  url?: string | null;
  viewed: boolean;
  [key: string]: unknown;
}

export const userNotificationsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getNotifications: build.query<UserNotification[], void>({
      query: () => "api/internal/notifications",
      providesTags: ["UserNotifications"],
    }),
    testNotifications: build.mutation<unknown, Record<string, unknown>>({
      query: (data) => ({
        url: "api/internal/notifications_test",
        method: "POST",
        body: data,
      }),
    }),
    updateNotification: build.mutation<
      unknown,
      { notificationID: number | string; data: Record<string, unknown> }
    >({
      query: ({ notificationID, data }) => ({
        url: `api/internal/notifications/${notificationID}`,
        method: "PATCH",
        body: data,
      }),
      invalidatesTags: ["UserNotifications"],
    }),
    updateAllNotifications: build.mutation<unknown, Record<string, unknown>>({
      query: (data) => ({
        url: "api/internal/notifications/all",
        method: "PATCH",
        body: data,
      }),
      invalidatesTags: ["UserNotifications"],
    }),
    deleteNotification: build.mutation<unknown, number | string>({
      query: (notificationID) => ({
        url: `api/internal/notifications/${notificationID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["UserNotifications"],
    }),
    deleteAllNotifications: build.mutation<unknown, void>({
      query: () => ({
        url: "api/internal/notifications/all",
        method: "DELETE",
      }),
      invalidatesTags: ["UserNotifications"],
    }),
  }),
});

// Websocket: old handler refetched notifications on FETCH_NOTIFICATIONS.
invalidateOnMessage("skyportal/FETCH_NOTIFICATIONS", () => [
  "UserNotifications",
]);

export const {
  useGetNotificationsQuery,
  useTestNotificationsMutation,
  useUpdateNotificationMutation,
  useUpdateAllNotificationsMutation,
  useDeleteNotificationMutation,
  useDeleteAllNotificationsMutation,
} = userNotificationsApi;
