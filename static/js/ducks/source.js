import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const REFRESH_SOURCE = "skyportal/REFRESH_SOURCE";

export const FETCH_LOADED_SOURCE = "skyportal/FETCH_LOADED_SOURCE";
export const FETCH_LOADED_SOURCE_OK = "skyportal/FETCH_LOADED_SOURCE_OK";
export const FETCH_LOADED_SOURCE_ERROR = "skyportal/FETCH_LOADED_SOURCE_ERROR";
export const FETCH_LOADED_SOURCE_FAIL = "skyportal/FETCH_LOADED_SOURCE_FAIL";

export const ADD_CLASSIFICATION = "skyportal/ADD_CLASSIFICATION";
export const ADD_CLASSIFICATION_OK = "skyportal/ADD_CLASSIFICATION_OK";

export const DELETE_CLASSIFICATION = "skyportal/DELETE_CLASSIFICATION";
export const DELETE_CLASSIFICATION_OK = "skyportal/DELETE_CLASSIFICATION_OK";

export const ADD_COMMENT = "skyportal/ADD_COMMENT";
export const ADD_COMMENT_OK = "skyportal/ADD_COMMENT_OK";

export const DELETE_COMMENT = "skyportal/DELETE_COMMENT";
export const DELETE_COMMENT_OK = "skyportal/DELETE_COMMENT_OK";

export const ADD_SOURCE_VIEW = "skyportal/ADD_SOURCE_VIEW";
export const ADD_SOURCE_VIEW_OK = "skyportal/ADD_SOURCE_VIEW_OK";

export const SUBMIT_FOLLOWUP_REQUEST = "skyportal/SUBMIT_FOLLOWUP_REQUEST";
export const SUBMIT_FOLLOWUP_REQUEST_OK =
  "skyportal/SUBMIT_FOLLOWUP_REQUEST_OK";

export const EDIT_FOLLOWUP_REQUEST = "skyportal/EDIT_FOLLOWUP_REQUEST";
export const EDIT_FOLLOWUP_REQUEST_OK = "skyportal/EDIT_FOLLOWUP_REQUEST_OK";

export const SUBMIT_ASSIGNMENT = "skyportal/SUBMIT_ASSIGNMENT";
export const SUBMIT_ASSIGNMENT_OK = "skyportal/SUBMIT_ASSIGNMENT_OK";

export const EDIT_ASSIGNMENT = "skyportal/EDIT_ASSIGNMENT";
export const EDIT_ASSIGNMENT_OK = "skyportal/EDIT_ASSIGNMENT_OK";

export const DELETE_ASSIGNMENT = "skyportal/DELETE_ASSIGNMENT";
export const DELETE_ASSIGNMENT_OK = "skyportal/DELETE_ASSIGNMENT_OK";

export const SAVE_SOURCE = "skyportal/SAVE_SOURCE";
export const SAVE_SOURCE_OK = "skyportal/SAVE_SOURCE_OK";

export const TRANSFER_SOURCE_OR_REQUEST_SAVE =
  "skyportal/TRANSFER_SOURCE_OR_REQUEST_SAVE";
export const TRANSFER_SOURCE_OR_REQUEST_SAVE_OK =
  "skyportal/TRANSFER_SOURCE_OR_REQUEST_SAVE_OK";

export const UPDATE_SOURCE = "skyportal/UPDATE_SOURCE";
export const UPDATE_SOURCE_OK = "skyportal/UPDATE_SOURCE_OK";

export const DELETE_FOLLOWUP_REQUEST = "skyportal/DELETE_FOLLOWUP_REQUEST";
export const DELETE_FOLLOWUP_REQUEST_OK =
  "skyportal/DELETE_FOLLOWUP_REQUEST_OK";

export const UPLOAD_PHOTOMETRY = "skyportal/UPLOAD_PHOTOMETRY";
export const UPLOAD_PHOTOMETRY_OK = "skyportal/UPLOAD_PHOTOMETRY_OK";

export const SHARE_DATA = "skyportal/SHARE_DATA";
export const SHARE_DATA_OK = "skyportal/SHARE_DATA_OK";

export const SEND_ALERT = "skyportal/SEND_ALERT";
export const SEND_ALERT_OK = "skyportal/SEND_ALERT_OK";

export const shareData = (data) => API.POST("/api/sharing", SHARE_DATA, data);

export const uploadPhotometry = (data) =>
  API.POST("/api/photometry", UPLOAD_PHOTOMETRY, data);

export function addClassification(formData) {
  return API.POST(`/api/classification`, ADD_CLASSIFICATION, formData);
}

export function deleteClassification(classification_id) {
  return API.DELETE(
    `/api/classification/${classification_id}`,
    DELETE_CLASSIFICATION
  );
}

export function addComment(formData) {
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
        dispatch(API.POST(`/api/comment`, ADD_COMMENT, formData));
      });
    };
  }
  return API.POST(`/api/comment`, ADD_COMMENT, formData);
}

export function deleteComment(comment_id) {
  return API.DELETE(`/api/comment/${comment_id}`, DELETE_COMMENT);
}

export function fetchSource(id) {
  return API.GET(`/api/sources/${id}`, FETCH_LOADED_SOURCE);
}

export function addSourceView(id) {
  return API.POST(`/api/internal/source_views/${id}`, ADD_SOURCE_VIEW);
}

export const updateSource = (id, payload) =>
  API.PATCH(`/api/sources/${id}`, UPDATE_SOURCE, payload);

export const saveSource = (payload) =>
  API.POST(`/api/sources`, SAVE_SOURCE, payload);

export const acceptSaveRequest = ({ sourceID, groupID }) =>
  API.PATCH(`/api/source_groups/${sourceID}`, SAVE_SOURCE, {
    groupID,
    active: true,
    requested: false,
  });

export const declineSaveRequest = ({ sourceID, groupID }) =>
  API.PATCH(`/api/source_groups/${sourceID}`, SAVE_SOURCE, {
    groupID,
    active: false,
    requested: false,
  });

export const updateSourceGroups = (payload) =>
  API.POST(`/api/source_groups`, TRANSFER_SOURCE_OR_REQUEST_SAVE, payload);

export const submitFollowupRequest = (params) => {
  const { instrument_name, ...paramsToSubmit } = params;
  return API.POST(
    "/api/followup_request",
    SUBMIT_FOLLOWUP_REQUEST,
    paramsToSubmit
  );
};

export const editFollowupRequest = (params, requestID) => {
  const { instrument_name, ...paramsToSubmit } = params;
  return API.PUT(
    `/api/followup_request/${requestID}`,
    EDIT_FOLLOWUP_REQUEST,
    paramsToSubmit
  );
};

export const deleteFollowupRequest = (id) =>
  API.DELETE(`/api/followup_request/${id}`, DELETE_FOLLOWUP_REQUEST);

export const submitAssignment = (params) =>
  API.POST("/api/assignment", SUBMIT_ASSIGNMENT, params);

export const editAssignment = (params, assignmentID) =>
  API.PUT(`/api/assignment/${assignmentID}`, EDIT_ASSIGNMENT, params);

export const deleteAssignment = (id) =>
  API.DELETE(`/api/assignment/${id}`, DELETE_ASSIGNMENT);

export const sendAlert = (params) =>
  API.POST(`/api/source_notifications`, SEND_ALERT, params);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { source } = getState();

  if (actionType === REFRESH_SOURCE) {
    const loaded_obj_key = source?.internal_key;

    if (loaded_obj_key === payload.obj_key) {
      dispatch(fetchSource(source.id));
    }
  }
});

// Reducer for currently displayed source
const reducer = (state = { source: null, loadError: false }, action) => {
  switch (action.type) {
    case FETCH_LOADED_SOURCE_OK: {
      const source = action.data;
      return {
        ...state,
        ...source,
        loadError: "",
      };
    }
    case FETCH_LOADED_SOURCE_ERROR:
      return {
        ...state,
        loadError: action.message,
      };

    case FETCH_LOADED_SOURCE_FAIL:
      return {
        ...state,
        loadError: "Unknown error while loading source",
      };
    default:
      return state;
  }
};

store.injectReducer("source", reducer);
