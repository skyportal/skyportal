import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const REFRESH_SOURCE = "skyportal/REFRESH_SOURCE";

const FETCH_LOADED_SOURCE = "skyportal/FETCH_LOADED_SOURCE";
const FETCH_LOADED_SOURCE_OK = "skyportal/FETCH_LOADED_SOURCE_OK";
const FETCH_LOADED_SOURCE_ERROR = "skyportal/FETCH_LOADED_SOURCE_ERROR";
const FETCH_LOADED_SOURCE_FAIL = "skyportal/FETCH_LOADED_SOURCE_FAIL";

const ADD_CLASSIFICATION = "skyportal/ADD_CLASSIFICATION";

const DELETE_CLASSIFICATION = "skyportal/DELETE_CLASSIFICATION";

const ADD_COMMENT = "skyportal/ADD_COMMENT";

const DELETE_COMMENT = "skyportal/DELETE_COMMENT";

const GET_COMMENT_ATTACHMENT = "skyportal/GET_COMMENT_ATTACHMENT";
const GET_COMMENT_ATTACHMENT_OK = "skyportal/GET_COMMENT_ATTACHMENT_OK";

const ADD_SOURCE_VIEW = "skyportal/ADD_SOURCE_VIEW";

const SUBMIT_FOLLOWUP_REQUEST = "skyportal/SUBMIT_FOLLOWUP_REQUEST";

const EDIT_FOLLOWUP_REQUEST = "skyportal/EDIT_FOLLOWUP_REQUEST";

const SUBMIT_ASSIGNMENT = "skyportal/SUBMIT_ASSIGNMENT";

const EDIT_ASSIGNMENT = "skyportal/EDIT_ASSIGNMENT";

const DELETE_ASSIGNMENT = "skyportal/DELETE_ASSIGNMENT";

const SAVE_SOURCE = "skyportal/SAVE_SOURCE";

const TRANSFER_SOURCE_OR_REQUEST_SAVE =
  "skyportal/TRANSFER_SOURCE_OR_REQUEST_SAVE";

const UPDATE_SOURCE = "skyportal/UPDATE_SOURCE";

const DELETE_FOLLOWUP_REQUEST = "skyportal/DELETE_FOLLOWUP_REQUEST";

const UPLOAD_PHOTOMETRY = "skyportal/UPLOAD_PHOTOMETRY";

const SHARE_DATA = "skyportal/SHARE_DATA";

const SEND_ALERT = "skyportal/SEND_ALERT";

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

export function deleteComment(comment_id, associatedResourceType = "object") {
  return API.DELETE(
    `/api/comment/${comment_id}/${associatedResourceType}`,
    DELETE_COMMENT
  );
}

export function getCommentAttachment(comment_id) {
  return API.GET(
    `/api/comment/${comment_id}/attachment?download=False`,
    GET_COMMENT_ATTACHMENT
  );
}

export function fetchSource(id) {
  return API.GET(
    `/api/sources/${id}?includeComments=true&includeColorMagnitude=true&includeThumbnails=true`,
    FETCH_LOADED_SOURCE
  );
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
    case GET_COMMENT_ATTACHMENT_OK: {
      const { commentId, attachment } = action.data;
      return {
        ...state,
        commentAttachment: {
          commentId,
          attachment,
        },
      };
    }
    default:
      return state;
  }
};

store.injectReducer("source", reducer);
