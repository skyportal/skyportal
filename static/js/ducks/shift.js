import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_SHIFT = "skyportal/FETCH_SHIFT";
const FETCH_SHIFT_OK = "skyportal/FETCH_SHIFT_OK";

const REFRESH_SHIFT = "skyportal/REFRESH_SHIFT";

const SUBMIT_SHIFT = "skyportal/SUBMIT_SHIFT";

const UPDATE_SHIFT = "skyportal/UPDATE_SHIFT";

const DELETE_SHIFT = "skyportal/DELETE_SHIFT";

const ADD_COMMENT_ON_SHIFT = "skyportal/ADD_COMMENT_ON_SHIFT";
const DELETE_COMMENT_ON_SHIFT = "skyportal/DELETE_COMMENT_ON_SHIFT";
const EDIT_COMMENT_ON_SHIFT = "skyportal/EDIT_COMMENT_ON_SHIFT";

const GET_COMMENT_ON_SHIFT_ATTACHMENT =
  "skyportal/GET_COMMENT_ON_SHIFT_ATTACHMENT";
const GET_COMMENT_ON_SHIFT_ATTACHMENT_OK =
  "skyportal/GET_COMMENT_ON_SHIFT_ATTACHMENT_OK";

const GET_COMMENT_ON_SHIFT_ATTACHMENT_PREVIEW =
  "skyportal/GET_COMMENT_ON_SHIFT_ATTACHMENT_PREVIEW";
const GET_COMMENT_ON_SHIFT_ATTACHMENT_PREVIEW_OK =
  "skyportal/GET_COMMENT_ON_SHIFT_ATTACHMENT_PREVIEW_OK";
const CURRENT_SHIFT_SELECTED_USERS = "skyportal/CURRENT_SHIFT_SELECTED_USERS";

const FETCH_SHIFT_SUMMARY = "skyportal/FETCH_SHIFT_SUMMARY";

const FETCH_SHIFT_SUMMARY_OK = "skyportal/FETCH_SHIFT_SUMMARY_OK";

export const fetchShift = (id) => API.GET(`/api/shifts/${id}`, FETCH_SHIFT);

export const submitShift = (run) => API.POST(`/api/shifts`, SUBMIT_SHIFT, run);

export function deleteShift(shiftID) {
  return API.DELETE(`/api/shifts/${shiftID}`, DELETE_SHIFT);
}

export const updateShift = (id, payload) =>
  API.PATCH(`/api/shifts/${id}`, UPDATE_SHIFT, payload);

export function addCommentOnShift(formData) {
  function fileReaderPromise(file) {
    return new Promise((resolve) => {
      const filereader = new FileReader();
      filereader.readAsDataURL(file);
      filereader.onloadend = () =>
        resolve({ body: filereader.result, name: file.name });
    });
  }
  if (formData.attachment) {
    return (dispatch) => {
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

export function editCommentOnShift(commentID, formData) {
  function fileReaderPromise(file) {
    return new Promise((resolve) => {
      const filereader = new FileReader();
      filereader.readAsDataURL(file);
      filereader.onloadend = () =>
        resolve({ body: filereader.result, name: file.name });
    });
  }
  if (formData.attachment) {
    return (dispatch) => {
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

export function deleteCommentOnShift(shiftID, commentID) {
  return API.DELETE(
    `/api/shift/${shiftID}/comments/${commentID}`,
    DELETE_COMMENT_ON_SHIFT,
  );
}

export function getCommentOnShiftAttachment(shiftID, commentID) {
  return API.GET(
    `/api/shift/${shiftID}/comments/${commentID}/attachment`,
    GET_COMMENT_ON_SHIFT_ATTACHMENT,
  );
}

export function getCommentOnShiftTextAttachment(shiftID, commentID) {
  return API.GET(
    `/api/shift/${shiftID}/comments/${commentID}/attachment?download=false&preview=false`,
    GET_COMMENT_ON_SHIFT_ATTACHMENT_PREVIEW,
  );
}

export function getShiftsSummary({ shiftID, startDate, endDate }) {
  let data = null;
  let url = `/api/shifts/summary`;
  if (startDate && endDate) {
    data = { startDate, endDate };
  } else if (shiftID) {
    url = `/api/shifts/summary/${shiftID}`;
  }
  return API.GET(url, FETCH_SHIFT_SUMMARY, data);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { shift } = getState();
  if (actionType === REFRESH_SHIFT) {
    if (shift?.currentShift?.id === payload?.shift_id) {
      dispatch(fetchShift(shift?.currentShift.id));
    }
  }
});

const reducer = (
  state = { currentShift: {}, selectedUsers: [], shiftsSummary: [] },
  action,
) => {
  switch (action.type) {
    case FETCH_SHIFT_OK: {
      const shift = action.data;
      return {
        ...state,
        currentShift: shift,
      };
    }
    case GET_COMMENT_ON_SHIFT_ATTACHMENT_OK: {
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
    case CURRENT_SHIFT_SELECTED_USERS: {
      const selectedUsers = action.data;
      return {
        ...state,
        selectedUsers,
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

store.injectReducer("shift", reducer);
