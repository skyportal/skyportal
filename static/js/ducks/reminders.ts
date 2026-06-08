/**
 * Reminders for a given resource (source, gcn_event, spectra, shift).
 *
 * RTK Query conversion of the old `FETCH_REMINDERS` duck. The query is keyed on
 * the `(resourceType, resourceId)` pair and provides a `Reminder` tag scoped to
 * that pair (`id: "${resourceType}-${resourceId}"`) so a websocket REFRESH only
 * refetches the reminders for the matching resource. The mutations
 * (submit/update/delete) invalidate that same scoped tag.
 *
 * The old websocket handlers gated a refetch on the currently-loaded resource
 * matching the pushed id, for each resource type. Those are bridged to scoped
 * cache invalidation via `invalidateOnMessage`.
 */
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface Reminder {
  id: number;
  user_id: number;
  text: string;
  next_reminder: string;
  number_of_reminders: number;
  reminder_delay: number;
  [key: string]: unknown;
}

interface RemindersArg {
  resourceId: number | string;
  resourceType: string;
}

interface SubmitReminderArg extends RemindersArg {
  data: Record<string, unknown>;
}

interface UpdateReminderArg extends RemindersArg {
  reminderID: number | string;
  data: Record<string, unknown>;
}

interface DeleteReminderArg extends RemindersArg {
  reminderID: number | string;
}

const reminderTag = (resourceType: string, resourceId: number | string) => ({
  type: "Reminder" as const,
  id: `${resourceType}-${resourceId}`,
});

export const remindersApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getReminders: build.query<Reminder[], RemindersArg>({
      query: ({ resourceId, resourceType }) =>
        `api/${resourceType}/${resourceId}/reminders`,
      transformResponse: (data: { reminders?: Reminder[] }) =>
        data?.reminders ?? [],
      providesTags: (_result, _error, { resourceId, resourceType }) => [
        reminderTag(resourceType, resourceId),
      ],
    }),
    submitReminder: build.mutation<unknown, SubmitReminderArg>({
      query: ({ resourceId, resourceType, data }) => ({
        url: `api/${resourceType}/${resourceId}/reminders`,
        method: "POST",
        body: data,
      }),
      invalidatesTags: (_result, _error, { resourceId, resourceType }) => [
        reminderTag(resourceType, resourceId),
      ],
    }),
    updateReminder: build.mutation<unknown, UpdateReminderArg>({
      query: ({ resourceId, resourceType, reminderID, data }) => ({
        url: `api/${resourceType}/${resourceId}/reminders/${reminderID}`,
        method: "PATCH",
        body: data,
      }),
      invalidatesTags: (_result, _error, { resourceId, resourceType }) => [
        reminderTag(resourceType, resourceId),
      ],
    }),
    deleteReminder: build.mutation<unknown, DeleteReminderArg>({
      query: ({ resourceId, resourceType, reminderID }) => ({
        url: `api/${resourceType}/${resourceId}/reminders/${reminderID}`,
        method: "DELETE",
      }),
      invalidatesTags: (_result, _error, { resourceId, resourceType }) => [
        reminderTag(resourceType, resourceId),
      ],
    }),
  }),
});

// Websocket-driven invalidation. The old handlers refreshed the reminders for
// the currently-loaded resource when a REFRESH for the matching id + type
// arrived; here we invalidate the scoped tag so only that active query refetches.
const registerReminderRefresh = (actionType: string, resourceType: string) => {
  invalidateOnMessage(actionType, (payload) =>
    payload?.id != null ? [reminderTag(resourceType, payload.id)] : null,
  );
};

registerReminderRefresh("skyportal/REFRESH_REMINDER_SOURCE", "source");
registerReminderRefresh("skyportal/REFRESH_REMINDER_GCNEVENT", "gcn_event");
registerReminderRefresh("skyportal/REFRESH_REMINDER_SOURCE_SPECTRA", "spectra");
registerReminderRefresh("skyportal/REFRESH_REMINDER_SHIFT", "shift");

export const {
  useGetRemindersQuery,
  useSubmitReminderMutation,
  useUpdateReminderMutation,
  useDeleteReminderMutation,
} = remindersApi;
