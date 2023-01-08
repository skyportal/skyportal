import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const REFRESH_GCN_EVENT = "skyportal/REFRESH_GCN_EVENT";

export const FETCH_GCNEVENT = "skyportal/FETCH_GCNEVENT";
export const FETCH_GCNEVENT_OK = "skyportal/FETCH_GCNEVENT_OK";

export const SUBMIT_GCNEVENT = "skyportal/SUBMIT_GCNEVENT";

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

const CREATE_OBSERVATION_PLAN_REQUEST_OBSERVING_RUN =
  "skyportal/CREATE_OBSERVATION_PLAN_REQUEST_OBSERVING_RUN";

const DELETE_OBSERVATION_PLAN_FIELDS =
  "skyportal/DELETE_OBSERVATION_PLAN_FIELDS";

const POST_GCNEVENT_SUMMARY = "skyportal/POST_GCNEVENT_SUMMARY";
const FETCH_GCNEVENT_SUMMARY = "skyportal/FETCH_GCNEVENT_SUMMARY";
const DELETE_GCNEVENT_SUMMARY = "skyportal/DELETE_GCNEVENT_SUMMARY";

const POST_GCN_TACH = "skyportal/POST_GCN_TACH";
const FETCH_GCN_TACH = "skyportal/FETCH_GCN_TACH";
const FETCH_GCN_TACH_OK = "skyportal/FETCH_GCN_TACH_OK";

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

export const createObservationPlanRequestObservingRun = (id, params = {}) =>
  API.POST(
    `/api/observation_plan/${id}/observing_run`,
    CREATE_OBSERVATION_PLAN_REQUEST_OBSERVING_RUN,
    params
  );

export const deleteObservationPlanFields = (id, fieldIds) =>
  API.DELETE(
    `/api/observation_plan/${id}/fields`,
    DELETE_OBSERVATION_PLAN_FIELDS,
    { fieldIds }
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

export function submitGcnEvent(data) {
  return API.POST("/api/gcn_event", SUBMIT_GCNEVENT, data);
}

export function postGcnEventSummary({ dateobs, params }) {
  return API.POST(
    `/api/gcn_event/${dateobs}/summary`,
    POST_GCNEVENT_SUMMARY,
    params
  );
}

export function fetchGcnEventSummary({ dateobs, summaryID }) {
  return API.GET(
    `/api/gcn_event/${dateobs}/summary/${summaryID}`,
    FETCH_GCNEVENT_SUMMARY
  );
}

export function deleteGcnEventSummary({ dateobs, summaryID }) {
  return API.DELETE(
    `/api/gcn_event/${dateobs}/summary/${summaryID}`,
    DELETE_GCNEVENT_SUMMARY
  );
}

export function postGcnTach(dateobs) {
  return API.POST(`/api/gcn_event/${dateobs}/tach`, POST_GCN_TACH);
}

export function fetchGcnTach(dateobs) {
  return API.GET(`/api/gcn_event/${dateobs}/tach`, FETCH_GCN_TACH);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { gcnEvent } = getState();
  if (actionType === FETCH_GCNEVENT) {
    dispatch(fetchGcnEvent(gcnEvent.dateobs)).then((response) => {
      if (response.status === "success") {
        dispatch(fetchGcnTach(gcnEvent.dateobs));
      }
    });
  }
  if (actionType === REFRESH_GCN_EVENT) {
    const loaded_gcnevent_key = gcnEvent?.dateobs;

    if (loaded_gcnevent_key === payload.gcnEvent_dateobs) {
      dispatch(fetchGcnEvent(gcnEvent.dateobs)).then((response) => {
        if (response.status === "success") {
          dispatch(fetchGcnTach(gcnEvent.dateobs));
        }
      });
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
    case FETCH_GCN_TACH_OK: {
      return {
        ...state,
        circulars: action.data.circulars,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("gcnEvent", reducer);
