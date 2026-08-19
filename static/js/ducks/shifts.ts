/**
 * Shifts.
 *
 * RTK Query conversion of the old `FETCH_SHIFT(S)` duck. Endpoints are injected
 * into the central `skyportalApi`. Shift list/detail queries convert the
 * backend's naive UTC date strings to `Date` objects (the old reducer did this
 * via `shiftStringDateToDate`). Mutations (create/update/delete a shift, add /
 * update / remove shift users, and comment CRUD) invalidate the `Shift` tag so
 * active shift queries refetch.
 *
 * The websocket `REFRESH_SHIFT` / `REFRESH_SHIFTS` messages are bridged to cache
 * invalidation via `invalidateOnMessage`.
 */
import type { CommentAttachment } from "skyportal-js/Comments";
import type {
  FetchShiftsOptions,
  Shift,
  ShiftPost,
  ShiftSummaryReport,
  UpdateShiftOptions,
} from "skyportal-js/Shifts";

import { skyportalApi } from "../api/skyportalApi";
import { clientQuery } from "../api/skyportalClient";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface ShiftSummaryArg {
  shiftID?: number | string | undefined;
  startDate?: string | undefined;
  endDate?: string | undefined;
}

interface ShiftUserArg {
  userID: number | string;
  shiftID: number | string;
  admin?: boolean | undefined;
  needs_replacement?: boolean | undefined;
}

interface CommentAttachmentArg {
  shiftID: number | string;
  commentID: number | string;
}

/** A shift whose UTC date strings have been parsed into `Date`s. */
export type ShiftWithDates = Omit<Shift, "start_date" | "end_date"> & {
  start_date: Date;
  end_date: Date;
};

function shiftStringDateToDate(shift: Shift): ShiftWithDates {
  return {
    ...shift,
    start_date: new Date(`${shift.start_date}Z`),
    end_date: new Date(`${shift.end_date}Z`),
  };
}

function fileReaderPromise(
  file: File,
): Promise<{ body: string | ArrayBuffer | null; name: string }> {
  return new Promise((resolve) => {
    const filereader = new FileReader();
    filereader.readAsDataURL(file);
    filereader.onloadend = () =>
      resolve({ body: filereader.result, name: file.name });
  });
}

export const shiftsApi = skyportalApi.injectEndpoints({
  endpoints: (build) => ({
    getShift: build.query<ShiftWithDates, number | string>({
      queryFn: (id, api) =>
        clientQuery(api, async (client) =>
          shiftStringDateToDate(await client.fetchShift(Number(id))),
        ),
      providesTags: ["Shift"],
    }),
    getShifts: build.query<ShiftWithDates[], FetchShiftsOptions | void>({
      queryFn: (params, api) =>
        clientQuery(api, async (client) =>
          (await client.fetchShifts(params ?? {})).map((shift) =>
            shiftStringDateToDate(shift),
          ),
        ),
      providesTags: ["Shift"],
    }),
    getShiftsSummary: build.query<ShiftSummaryReport, ShiftSummaryArg>({
      queryFn: ({ shiftID, startDate, endDate }, api) =>
        clientQuery(api, (client) =>
          client.fetchShiftSummary(
            startDate && endDate
              ? { startDate, endDate }
              : shiftID
                ? { shiftId: Number(shiftID) }
                : {},
          ),
        ),
      providesTags: ["Shift"],
    }),
    // download/preview must be empty for the JSON form: the handler treats any
    // non-empty value (including "false") as truthy and streams the file.
    getCommentOnShiftAttachment: build.query<
      CommentAttachment,
      CommentAttachmentArg
    >({
      queryFn: ({ shiftID, commentID }, api) =>
        clientQuery(api, (client) =>
          client.fetchCommentAttachmentText(shiftID, Number(commentID), {
            resourceType: "shift",
          }),
        ),
    }),
    submitShift: build.mutation<{ id: number }, ShiftPost>({
      queryFn: (run, api) =>
        clientQuery(api, (client) => client.postShift(run)),
      invalidatesTags: ["Shift"],
    }),
    updateShift: build.mutation<
      void,
      { id: number | string; payload: UpdateShiftOptions }
    >({
      queryFn: ({ id, payload }, api) =>
        clientQuery(api, (client) => client.updateShift(Number(id), payload)),
      invalidatesTags: ["Shift"],
    }),
    deleteShift: build.mutation<void, number | string>({
      queryFn: (shiftID, api) =>
        clientQuery(api, (client) => client.deleteShift(Number(shiftID))),
      invalidatesTags: ["Shift"],
    }),
    addShiftUser: build.mutation<
      { shift_id: number; user_id: number; admin: boolean },
      ShiftUserArg
    >({
      queryFn: ({ userID, shiftID, admin }, api) =>
        clientQuery(api, (client) =>
          client.postShiftUser(Number(shiftID), Number(userID), { admin }),
        ),
      invalidatesTags: ["Shift"],
    }),
    updateShiftUser: build.mutation<void, ShiftUserArg>({
      queryFn: ({ shiftID, userID, admin, needs_replacement }, api) =>
        clientQuery(api, (client) =>
          client.updateShiftUser(Number(shiftID), Number(userID), {
            admin,
            needsReplacement: needs_replacement,
          }),
        ),
      invalidatesTags: ["Shift"],
    }),
    deleteShiftUser: build.mutation<void, ShiftUserArg>({
      queryFn: ({ userID, shiftID }, api) =>
        clientQuery(api, (client) =>
          client.deleteShiftUser(Number(shiftID), Number(userID)),
        ),
      invalidatesTags: ["Shift"],
    }),
    addCommentOnShift: build.mutation<
      { comment_id: number },
      {
        shiftID: number | string;
        text: string;
        group_ids?: number[];
        attachment?: File;
      }
    >({
      queryFn: async ({ shiftID, text, group_ids, attachment }, api) => {
        const file = attachment
          ? await fileReaderPromise(attachment)
          : undefined;
        return clientQuery(api, (client) =>
          file
            ? client.postCommentWithAttachment(
                shiftID,
                text,
                file.name,
                String(file.body),
                { resourceType: "shift", groupIds: group_ids },
              )
            : client.postComment(shiftID, text, {
                resourceType: "shift",
                groupIds: group_ids,
              }),
        );
      },
      invalidatesTags: ["Shift"],
    }),
    editCommentOnShift: build.mutation<
      void,
      {
        commentID: number | string;
        formData: {
          shift_id: number | string;
          text?: string;
          group_ids?: number[];
          attachment?: File;
        };
      }
    >({
      queryFn: async ({ commentID, formData }, api) => {
        const file = formData.attachment
          ? await fileReaderPromise(formData.attachment)
          : undefined;
        return clientQuery(api, (client) =>
          client.updateComment(formData.shift_id, Number(commentID), {
            resourceType: "shift",
            text: formData.text,
            groupIds: formData.group_ids,
            ...(file
              ? { attachmentName: file.name, attachmentBody: String(file.body) }
              : {}),
          }),
        );
      },
      invalidatesTags: ["Shift"],
    }),
    deleteCommentOnShift: build.mutation<
      void,
      { shiftID: number | string; commentID: number | string }
    >({
      queryFn: ({ shiftID, commentID }, api) =>
        clientQuery(api, (client) =>
          client.deleteComment(shiftID, Number(commentID), {
            resourceType: "shift",
          }),
        ),
      invalidatesTags: ["Shift"],
    }),
  }),
});

// Websocket-driven invalidation: the old handler refetched the affected shift
// (REFRESH_SHIFT) or the whole list (REFRESH_SHIFTS). Both map to the `Shift`
// tag, so any active shift query refetches.
invalidateOnMessage("skyportal/REFRESH_SHIFT", () => ["Shift"]);
invalidateOnMessage("skyportal/REFRESH_SHIFTS", () => ["Shift"]);

export const {
  useGetShiftQuery,
  useGetShiftsQuery,
  useGetShiftsSummaryQuery,
  useGetCommentOnShiftAttachmentQuery,
  useLazyGetCommentOnShiftAttachmentQuery,
  useSubmitShiftMutation,
  useUpdateShiftMutation,
  useDeleteShiftMutation,
  useAddShiftUserMutation,
  useUpdateShiftUserMutation,
  useDeleteShiftUserMutation,
  useAddCommentOnShiftMutation,
  useEditCommentOnShiftMutation,
  useDeleteCommentOnShiftMutation,
} = shiftsApi;
