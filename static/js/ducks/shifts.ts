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
import { skyportalApi } from "../api/skyportalApi";
import { invalidateOnMessage } from "../api/wsInvalidation";

interface Shift {
  id: number;
  start_date: string | Date;
  end_date: string | Date;
  [key: string]: unknown;
}

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

interface CommentAttachment {
  commentId: number | string;
  text: string;
  attachment: string;
  attachment_name: string;
}

interface CommentAttachmentArg {
  shiftID: number | string;
  commentID: number | string;
}

function shiftStringDateToDate(shift: Shift): Shift {
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
    getShift: build.query<Shift, number | string>({
      query: (id) => `api/shifts/${id}`,
      transformResponse: (data: Shift) => shiftStringDateToDate(data),
      providesTags: ["Shift"],
    }),
    getShifts: build.query<Shift[], Record<string, unknown> | void>({
      query: (params) => {
        const search = new URLSearchParams(
          (params as Record<string, string>) ?? {},
        ).toString();
        return search ? `api/shifts?${search}` : "api/shifts";
      },
      transformResponse: (data: Shift[]) =>
        (data ?? []).map((shift) => shiftStringDateToDate(shift)),
      providesTags: ["Shift"],
    }),
    getShiftsSummary: build.query<any, ShiftSummaryArg>({
      query: ({ shiftID, startDate, endDate }) => {
        if (startDate && endDate) {
          const search = new URLSearchParams({
            startDate,
            endDate,
          }).toString();
          return `api/shifts/summary?${search}`;
        }
        if (shiftID) {
          return `api/shifts/summary/${shiftID}`;
        }
        return "api/shifts/summary";
      },
      providesTags: ["Shift"],
    }),
    getCommentOnShiftAttachment: build.query<
      CommentAttachment,
      CommentAttachmentArg
    >({
      query: ({ shiftID, commentID }) =>
        `api/shift/${shiftID}/comments/${commentID}/attachment?download=false&preview=false`,
    }),
    submitShift: build.mutation<unknown, any>({
      query: (run) => ({
        url: "api/shifts",
        method: "POST",
        body: run,
      }),
      invalidatesTags: ["Shift"],
    }),
    updateShift: build.mutation<unknown, { id: number | string; payload: any }>(
      {
        query: ({ id, payload }) => ({
          url: `api/shifts/${id}`,
          method: "PATCH",
          body: payload,
        }),
        invalidatesTags: ["Shift"],
      },
    ),
    deleteShift: build.mutation<unknown, number | string>({
      query: (shiftID) => ({
        url: `api/shifts/${shiftID}`,
        method: "DELETE",
      }),
      invalidatesTags: ["Shift"],
    }),
    addShiftUser: build.mutation<unknown, ShiftUserArg>({
      query: ({ userID, shiftID, admin }) => ({
        url: `api/shifts/${shiftID}/users`,
        method: "POST",
        body: { userID, shiftID, admin },
      }),
      invalidatesTags: ["Shift"],
    }),
    updateShiftUser: build.mutation<unknown, ShiftUserArg>({
      query: ({ shiftID, userID, admin, needs_replacement }) => ({
        url: `api/shifts/${shiftID}/users/${userID}`,
        method: "PATCH",
        body: { admin, needs_replacement },
      }),
      invalidatesTags: ["Shift"],
    }),
    deleteShiftUser: build.mutation<unknown, ShiftUserArg>({
      query: ({ userID, shiftID }) => ({
        url: `api/shifts/${shiftID}/users/${userID}`,
        method: "DELETE",
        body: { userID, shiftID },
      }),
      invalidatesTags: ["Shift"],
    }),
    addCommentOnShift: build.mutation<unknown, any>({
      queryFn: async (formData, _api, _extra, baseQuery) => {
        const body = { ...formData };
        if (body.attachment) {
          body.attachment = await fileReaderPromise(body.attachment);
        }
        const result = await baseQuery({
          url: `api/shift/${body.shiftID}/comments`,
          method: "POST",
          body,
        });
        if (result.error) {
          return { error: result.error };
        }
        return { data: result.data };
      },
      invalidatesTags: ["Shift"],
    }),
    editCommentOnShift: build.mutation<
      unknown,
      { commentID: number | string; formData: any }
    >({
      queryFn: async ({ commentID, formData }, _api, _extra, baseQuery) => {
        const body = { ...formData };
        if (body.attachment) {
          body.attachment = await fileReaderPromise(body.attachment);
        }
        const result = await baseQuery({
          url: `api/shift/${body.shift_id}/comments/${commentID}`,
          method: "PUT",
          body,
        });
        if (result.error) {
          return { error: result.error };
        }
        return { data: result.data };
      },
      invalidatesTags: ["Shift"],
    }),
    deleteCommentOnShift: build.mutation<
      unknown,
      { shiftID: number | string; commentID: number | string }
    >({
      query: ({ shiftID, commentID }) => ({
        url: `api/shift/${shiftID}/comments/${commentID}`,
        method: "DELETE",
      }),
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
