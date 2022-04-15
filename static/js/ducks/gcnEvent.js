import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const REFRESH_GCNEVENT = "skyportal/REFRESH_GCNEVENT";

export const FETCH_GCNEVENT = "skyportal/FETCH_GCNEVENT";
export const FETCH_GCNEVENT_OK = "skyportal/FETCH_GCNEVENT_OK";

const ADD_COMMENT_ON_GCNEVENT = "skyportal/ADD_COMMENT_ON_GCNEVENT";

const DELETE_COMMENT_ON_GCNEVENT = "skyportal/DELETE_COMMENT_ON_GCNEVENT";

const GET_COMMENT_ON_GCNEVENT_ATTACHMENT =
  "skyportal/GET_COMMENT_ON_GCNEVENT_ATTACHMENT";
const GET_COMMENT_ON_GCNEVENT_ATTACHMENT_OK =
  "skyportal/GET_COMMENT_ON_GCNEVENT_ATTACHMENT_OK";

const GET_COMMENT_ON_GCNEVENT_ATTACHMENT_PREVIEW =
  "skyportal/GET_COMMENT_ON_GCNEVENT_ATTACHMENT_PREVIEW";
const GET_COMMENT_ON_GCNEVENT_ATTACHMENT_PREVIEW_OK =
  "skyportal/GET_COMMENT_ON_GCNEVENT_ATTACHMENT_PREVIEW_OK";

const SUBMIT_OBSERVATION_PLAN_REQUEST =
  "skyportal/SUBMIT_OBSERVATION_PLAN_REQUEST";

const EDIT_OBSERVATION_PLAN_REQUEST = "skyportal/EDIT_OBSERVATION_PLAN_REQUEST";

const DELETE_OBSERVATION_PLAN_REQUEST =
  "skyportal/DELETE_OBSERVATION_PLAN_REQUEST";

const SUBMIT_OBSERVATION_PLAN_REQUEST_TREASUREMAP =
  "skyportal/SUBMIT_OBSERVATION_PLAN_REQUEST_TREASUREMAP";
const DELETE_OBSERVATION_PLAN_REQUEST_TREASUREMAP =
  "skyportal/DELETE_OBSERVATION_PLAN_REQUEST_TREASUREMAP";

const SEND_OBSERVATION_PLAN_REQUEST = "skyportal/SEND_OBSERVATION_PLAN_REQUEST";
const REMOVE_OBSERVATION_PLAN_REQUEST =
  "skyportal/REMOVE_OBSERVATION_PLAN_REQUEST";

export const fetchGcnEvent = (dateobs) =>
  API.GET(`/api/gcn_event/${dateobs}`, FETCH_GCNEVENT);

export function addCommentOnGcnEvent(formData) {
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
            `/api/gcn_event/${formData.gcnevent_id}/comments`,
            ADD_COMMENT_ON_GCNEVENT,
            formData
          )
        );
      });
    };
  }
  return API.POST(
    `/api/gcn_event/${formData.gcnevent_id}/comments`,
    ADD_COMMENT_ON_GCNEVENT,
    formData
  );
}

export function deleteCommentOnGcnEvent(gcnEventID, commentID) {
  return API.DELETE(
    `/api/gcn_event/${gcnEventID}/comments/${commentID}`,
    DELETE_COMMENT_ON_GCNEVENT
  );
}

export const submitObservationPlanRequest = (params) => {
  const { instrument_name, ...paramsToSubmit } = params;
  return API.POST(
    "/api/observation_plan",
    SUBMIT_OBSERVATION_PLAN_REQUEST,
    paramsToSubmit
  );
};

export const editObservationPlanRequest = (params, requestID) => {
  const { instrument_name, ...paramsToSubmit } = params;
  return API.PUT(
    `/api/observation_plan/${requestID}`,
    EDIT_OBSERVATION_PLAN_REQUEST,
    paramsToSubmit
  );
};

export const sendObservationPlanRequest = (id) =>
  API.POST(`/api/observation_plan/${id}/queue`, SEND_OBSERVATION_PLAN_REQUEST);

export const removeObservationPlanRequest = (id) =>
  API.DELETE(
    `/api/observation_plan/${id}/queue`,
    REMOVE_OBSERVATION_PLAN_REQUEST
  );

export const deleteObservationPlanRequest = (id) =>
  API.DELETE(`/api/observation_plan/${id}`, DELETE_OBSERVATION_PLAN_REQUEST);

export const submitObservationPlanRequestTreasureMap = (id) =>
  API.POST(
    `/api/observation_plan/${id}/treasuremap`,
    SUBMIT_OBSERVATION_PLAN_REQUEST_TREASUREMAP
  );

export const deleteObservationPlanRequestTreasureMap = (id) =>
  API.DELETE(
    `/api/observation_plan/${id}/treasuremap`,
    DELETE_OBSERVATION_PLAN_REQUEST_TREASUREMAP
  );

export function getCommentOnGcnEventAttachment(gcnEventID, commentID) {
  return API.GET(
    `/api/gcn_event/${gcnEventID}/comments/${commentID}/attachment`,
    GET_COMMENT_ON_GCNEVENT_ATTACHMENT
  );
}

export function getCommentOnGcnEventAttachmentPreview(gcnEventID, commentID) {
  return API.GET(
    `/api/gcn_event/${gcnEventID}/comments/${commentID}`,
    GET_COMMENT_ON_GCNEVENT_ATTACHMENT_PREVIEW
  );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { gcnEvent } = getState();
  if (actionType === FETCH_GCNEVENT) {
    dispatch(fetchGcnEvent(gcnEvent.dateobs));
  }
  if (actionType === REFRESH_GCNEVENT) {
    const loaded_gcnevent_key = gcnEvent?.dateobs;

    if (loaded_gcnevent_key === payload.gcnEvent_dateobs) {
      dispatch(fetchGcnEvent(gcnEvent.dateobs));
    }
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_GCNEVENT_OK: {
      return action.data;
    }
    case GET_COMMENT_ON_GCNEVENT_ATTACHMENT_OK: {
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
    case GET_COMMENT_ON_GCNEVENT_ATTACHMENT_PREVIEW_OK: {
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
    default:
      return state;
  }
};

store.injectReducer("gcnEvent", reducer);
