import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch } from "../types/store";

const FETCH_SHIFT = "skyportal/FETCH_SHIFT";
const FETCH_SHIFT_OK = "skyportal/FETCH_SHIFT_OK";

const REFRESH_SHIFT = "skyportal/REFRESH_SHIFT";

const SUBMIT_SHIFT = "skyportal/SUBMIT_SHIFT";

const UPDATE_SHIFT = "skyportal/UPDATE_SHIFT";

const DELETE_SHIFT = "skyportal/DELETE_SHIFT";

const SET_CURRENT_SHIFT = "skyportal/SET_CURRENT_SHIFT";

const ADD_COMMENT_ON_SHIFT = "skyportal/ADD_COMMENT_ON_SHIFT";
const DELETE_COMMENT_ON_SHIFT = "skyportal/DELETE_COMMENT_ON_SHIFT";
const EDIT_COMMENT_ON_SHIFT = "skyportal/EDIT_COMMENT_ON_SHIFT";

const GET_COMMENT_ON_SHIFT_ATTACHMENT_PREVIEW =
  "skyportal/GET_COMMENT_ON_SHIFT_ATTACHMENT_PREVIEW";
const GET_COMMENT_ON_SHIFT_ATTACHMENT_PREVIEW_OK =
  "skyportal/GET_COMMENT_ON_SHIFT_ATTACHMENT_PREVIEW_OK";

const FETCH_SHIFT_SUMMARY = "skyportal/FETCH_SHIFT_SUMMARY";

const FETCH_SHIFT_SUMMARY_OK = "skyportal/FETCH_SHIFT_SUMMARY_OK";

const FETCH_SHIFTS = "skyportal/FETCH_SHIFTS";
const FETCH_SHIFTS_OK = "skyportal/FETCH_SHIFTS_OK";

const REFRESH_SHIFTS = "skyportal/REFRESH_SHIFTS";

const ADD_SHIFT_USER = "skyportal/ADD_SHIFT_USER";

const UPDATE_SHIFT_USER = "skyportal/UPDATE_SHIFT_USER";

const DELETE_SHIFT_USER = "skyportal/DELETE_SHIFT_USER";

function shiftStringDateToDate(shift: any) {
  return {
    ...shift,
    start_date: new Date(`${shift.start_date}Z`),
    end_date: new Date(`${shift.end_date}Z`),
  };
}

export const fetchShift = (id: number | string) =>
  API.GET(`/api/shifts/${id}`, FETCH_SHIFT);

export const submitShift = (run: any) =>
  API.POST(`/api/shifts`, SUBMIT_SHIFT, run);

export function deleteShift(shiftID: number | string) {
  return API.DELETE(`/api/shifts/${shiftID}`, DELETE_SHIFT);
}

export const updateShift = (id: number | string, payload: any) =>
  API.PATCH(`/api/shifts/${id}`, UPDATE_SHIFT, payload);

export const fetchShifts = (params = {}) =>
  API.GET("/api/shifts", FETCH_SHIFTS, params);

export function addShiftUser({ userID, shiftID, admin }: any) {
  return API.POST(`/api/shifts/${shiftID}/users`, ADD_SHIFT_USER, {
    userID,
    shiftID,
    admin,
  });
}

export const updateShiftUser = ({
  shiftID,
  userID,
  admin,
  needs_replacement,
}: any) =>
  API.PATCH(`/api/shifts/${shiftID}/users/${userID}`, UPDATE_SHIFT_USER, {
    admin,
    needs_replacement,
  });

export function deleteShiftUser({ userID, shiftID }: any) {
  return API.DELETE(
    `/api/shifts/${shiftID}/users/${userID}`,
    DELETE_SHIFT_USER,
    { userID, shiftID },
  );
}

export function addCommentOnShift(formData: any) {
  function fileReaderPromise(file: any) {
    return new Promise((resolve) => {
      const filereader = new FileReader();
      filereader.readAsDataURL(file);
      filereader.onloadend = () =>
        resolve({ body: filereader.result, name: file.name });
    });
  }
  if (formData.attachment) {
    return (dispatch: AppDispatch) => {
      fileReaderPromise(formData.attachment).then((fileData) => {
        formData.attachment = fileData;

        dispatch(
          API.POST(
            `/api/shift/${formData.shiftID}/comments`,
            ADD_COMMENT_ON_SHIFT,
            formData,
          ),
        );
      });
    };
  }
  return API.POST(
    `/api/shift/${formData.shiftID}/comments`,
    ADD_COMMENT_ON_SHIFT,
    formData,
  );
}

export function editCommentOnShift(commentID: number | string, formData: any) {
  function fileReaderPromise(file: any) {
    return new Promise((resolve) => {
      const filereader = new FileReader();
      filereader.readAsDataURL(file);
      filereader.onloadend = () =>
        resolve({ body: filereader.result, name: file.name });
    });
  }
  if (formData.attachment) {
    return (dispatch: AppDispatch) => {
      fileReaderPromise(formData.attachment).then((fileData) => {
        formData.attachment = fileData;

        dispatch(
          API.PUT(
            `/api/shift/${formData.shift_id}/comments/${commentID}`,
            EDIT_COMMENT_ON_SHIFT,
            formData,
          ),
        );
      });
    };
  }
  return API.PUT(
    `/api/shift/${formData.shift_id}/comments/${commentID}`,
    EDIT_COMMENT_ON_SHIFT,
    formData,
  );
}

export function deleteCommentOnShift(
  shiftID: number | string,
  commentID: number | string,
) {
  return API.DELETE(
    `/api/shift/${shiftID}/comments/${commentID}`,
    DELETE_COMMENT_ON_SHIFT,
  );
}

export function getCommentOnShiftTextAttachment(
  shiftID: number | string,
  commentID: number | string,
) {
  return API.GET(
    `/api/shift/${shiftID}/comments/${commentID}/attachment?download=false&preview=false`,
    GET_COMMENT_ON_SHIFT_ATTACHMENT_PREVIEW,
  );
}

export function getShiftsSummary({ shiftID, startDate, endDate }: any) {
  let data: any = null;
  let url = `/api/shifts/summary`;
  if (startDate && endDate) {
    data = { startDate, endDate };
  } else if (shiftID) {
    url = `/api/shifts/summary/${shiftID}`;
  }
  return API.GET(url, FETCH_SHIFT_SUMMARY, data);
}

export const setCurrentShift =
  (shiftId: number | string) => async (dispatch: AppDispatch) => {
    if (!shiftId) {
      dispatch({
        type: SET_CURRENT_SHIFT,
        data: {},
      });
      return;
    }
    const response: any = await dispatch(fetchShift(shiftId));
    if (response?.status === "success") {
      dispatch({
        type: SET_CURRENT_SHIFT,
        data: response.data,
      });
    }
  };

// Websocket message handler
messageHandler.add(
  (actionType: string, payload: any, dispatch: AppDispatch) => {
    if (actionType === REFRESH_SHIFT) {
      dispatch(fetchShift(payload?.shift_id));
    }
    if (actionType === REFRESH_SHIFTS) {
      dispatch(fetchShifts());
    }
  },
);

type ShiftsState = Record<string, any>;

interface ShiftsAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (
  state: ShiftsState = { currentShift: {}, shiftsSummary: [], shiftList: [] },
  action: ShiftsAction,
): ShiftsState => {
  switch (action.type) {
    case SET_CURRENT_SHIFT: {
      return {
        ...state,
        currentShift: action.data,
      };
    }
    case FETCH_SHIFT_OK: {
      if (!action.data) return state;
      const newState = { ...state };
      const shift = action.data;

      // Update or add the shift in shiftList
      const formatedShift = shiftStringDateToDate(action.data);
      newState["shiftList"] = state["shiftList"].some(
        (s: any) => s.id === formatedShift.id,
      )
        ? state["shiftList"].map((s: any) =>
            s.id === formatedShift.id ? formatedShift : s,
          )
        : [...state["shiftList"], formatedShift];

      // Sync currentShift with the fetched shift
      if (shift.id === state["currentShift"]?.id) {
        newState["currentShift"] = shift;
      }
      return {
        ...newState,
      };
    }
    case FETCH_SHIFTS_OK: {
      const newState: Record<string, any> = {
        ...state,
        shiftList: action.data.map((shift: any) =>
          shiftStringDateToDate(shift),
        ),
      };
      // reset currentShift if it is not in the new shiftList
      if (
        state["currentShift"]?.id &&
        !newState["shiftList"].some(
          (s: any) => s.id === state["currentShift"].id,
        )
      ) {
        newState["currentShift"] = {};
      }
      return {
        ...newState,
      };
    }
    case GET_COMMENT_ON_SHIFT_ATTACHMENT_PREVIEW_OK: {
      const { commentId, text, attachment, attachment_name } = action.data;
      return {
        ...state,
        commentAttachment: {
          commentId,
          text,
          attachment,
          attachment_name,
        },
      };
    }
    case FETCH_SHIFT_SUMMARY_OK: {
      const shiftsSummary = action.data;
      return {
        ...state,
        shiftsSummary,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("shifts", reducer);
