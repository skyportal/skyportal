import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const REFRESH_GCN_EVENT = "skyportal/REFRESH_GCN_EVENT";

export const FETCH_GCNEVENT = "skyportal/FETCH_GCNEVENT";
export const FETCH_GCNEVENT_OK = "skyportal/FETCH_GCNEVENT_OK";

export const SUBMIT_GCNEVENT = "skyportal/SUBMIT_GCNEVENT";

const ADD_COMMENT_ON_GCNEVENT = "skyportal/ADD_COMMENT_ON_GCNEVENT";

const EDIT_COMMENT_ON_GCNEVENT = "skyportal/EDIT_COMMENT_ON_GCNEVENT";

const DELETE_COMMENT_ON_GCNEVENT = "skyportal/DELETE_COMMENT_ON_GCNEVENT";
const PATCH_GCNEVENT_SUMMARY = "skyportal/PATCH_GCNEVENT_SUMMARY";

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

const FETCH_OBSERVATION_PLAN_REQUEST =
  "skyportal/FETCH_OBSERVATION_PLAN_REQUEST";
const FETCH_OBSERVATION_PLAN_REQUEST_OK =
  "skyportal/FETCH_OBSERVATION_PLAN_REQUEST_OK";

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

const POST_GCNEVENT_REPORT = "skyportal/POST_GCNEVENT_REPORT";
const FETCH_GCNEVENT_REPORT = "skyportal/FETCH_GCNEVENT_REPORT";
const FETCH_GCNEVENT_REPORT_OK = "skyportal/FETCH_GCNEVENT_REPORT_OK";
const FETCH_GCNEVENT_REPORTS = "skyportal/FETCH_GCNEVENT_REPORTS";
const FETCH_GCNEVENT_REPORTS_OK = "skyportal/FETCH_GCNEVENT_REPORTS_OK";
const REFRESH_GCNEVENT_REPORT = "skyportal/REFRESH_GCNEVENT_REPORT";
const REFRESH_GCNEVENT_REPORTS = "skyportal/REFRESH_GCNEVENT_REPORTS";
const DELETE_GCNEVENT_REPORT = "skyportal/DELETE_GCNEVENT_REPORT";
const PATCH_GCNEVENT_REPORT = "skyportal/PATCH_GCNEVENT_REPORT";

const POST_GCN_TACH = "skyportal/POST_GCN_TACH";
const FETCH_GCN_TACH = "skyportal/FETCH_GCN_TACH";
const FETCH_GCN_TACH_OK = "skyportal/FETCH_GCN_TACH_OK";

const POST_GCN_GRACEDB = "skyportal/POST_GCN_GRACEDB";

const PUT_GCN_TRIGGERED = "skyportal/PUT_GCN_TRIGGERED";
const FETCH_GCN_TRIGGERED = "skyportal/FETCH_GCN_TRIGGERED";
const FETCH_GCN_TRIGGERED_OK = "skyportal/FETCH_GCN_TRIGGERED_OK";
const DELETE_GCN_TRIGGERED = "skyportal/DELETE_GCN_TRIGGERED";
const REFRESH_GCN_TRIGGERED = "skyportal/REFRESH_GCN_TRIGGERED";

const POST_GCN_ALIAS = "skyportal/POST_GCN_ALIAS";
const DELETE_GCN_ALIAS = "skyportal/DELETE_GCN_ALIAS";

const FETCH_GCNEVENT_SURVEY_EFFICIENCY =
  "skyportal/FETCH_GCNEVENT_SURVEY_EFFICIENCY";
const FETCH_GCNEVENT_SURVEY_EFFICIENCY_OK =
  "skyportal/FETCH_GCNEVENT_SURVEY_EFFICIENCY_OK";
const REFRESH_GCNEVENT_SURVEY_EFFICIENCY =
  "skyportal/REFRESH_GCNEVENT_SURVEY_EFFICIENCY";

const FETCH_GCNEVENT_CATALOG_QUERIES =
  "skyportal/FETCH_GCNEVENT_CATALOG_QUERIES";
const FETCH_GCNEVENT_CATALOG_QUERIES_OK =
  "skyportal/FETCH_GCNEVENT_CATALOG_QUERIES_OK";
const REFRESH_GCNEVENT_CATALOG_QUERIES =
  "skyportal/REFRESH_GCNEVENT_CATALOG_QUERIES";

const FETCH_GCNEVENT_OBSERVATION_PLAN_REQUESTS =
  "skyportal/FETCH_GCNEVENT_OBSERVATION_PLAN_REQUESTS";

const FETCH_GCNEVENT_OBSERVATION_PLAN_REQUESTS_OK =
  "skyportal/FETCH_GCNEVENT_OBSERVATION_PLAN_REQUESTS_OK";

const REFRESH_GCNEVENT_OBSERVATION_PLAN_REQUESTS =
  "skyportal/REFRESH_GCNEVENT_OBSERVATION_PLAN_REQUESTS";

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
            formData,
          ),
        );
      });
    };
  }
  return API.POST(
    `/api/gcn_event/${formData.gcnevent_id}/comments`,
    ADD_COMMENT_ON_GCNEVENT,
    formData,
  );
}

export function editCommentOnGcnEvent(commentID, gcnEventID, formData) {
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
            `/api/gcn_event/${gcnEventID}/comments/${commentID}`,
            EDIT_COMMENT_ON_GCNEVENT,
            formData,
          ),
        );
      });
    };
  }
  return API.PUT(
    `/api/gcn_event/${gcnEventID}/comments/${commentID}`,
    EDIT_COMMENT_ON_GCNEVENT,
    formData,
  );
}

export function deleteCommentOnGcnEvent(gcnEventID, commentID) {
  return API.DELETE(
    `/api/gcn_event/${gcnEventID}/comments/${commentID}`,
    DELETE_COMMENT_ON_GCNEVENT,
  );
}

export function fetchObservationPlanRequests(gcnEventID) {
  return API.GET(
    `/api/gcn_event/${gcnEventID}/observation_plan_requests`,
    FETCH_GCNEVENT_OBSERVATION_PLAN_REQUESTS,
  );
}

export const submitObservationPlanRequest = (params) => {
  const { instrument_name, ...paramsToSubmit } = params;
  return API.POST(
    "/api/observation_plan",
    SUBMIT_OBSERVATION_PLAN_REQUEST,
    paramsToSubmit,
  );
};

export const editObservationPlanRequest = (params, requestID) => {
  const { instrument_name, ...paramsToSubmit } = params;
  return API.PUT(
    `/api/observation_plan/${requestID}`,
    EDIT_OBSERVATION_PLAN_REQUEST,
    paramsToSubmit,
  );
};

export const sendObservationPlanRequest = (id) =>
  API.POST(`/api/observation_plan/${id}/queue`, SEND_OBSERVATION_PLAN_REQUEST);

export const removeObservationPlanRequest = (id) =>
  API.DELETE(
    `/api/observation_plan/${id}/queue`,
    REMOVE_OBSERVATION_PLAN_REQUEST,
  );

export const deleteObservationPlanRequest = (id) =>
  API.DELETE(`/api/observation_plan/${id}`, DELETE_OBSERVATION_PLAN_REQUEST);

export const submitObservationPlanRequestTreasureMap = (id) =>
  API.POST(
    `/api/observation_plan/${id}/treasuremap`,
    SUBMIT_OBSERVATION_PLAN_REQUEST_TREASUREMAP,
  );

export const deleteObservationPlanRequestTreasureMap = (id) =>
  API.DELETE(
    `/api/observation_plan/${id}/treasuremap`,
    DELETE_OBSERVATION_PLAN_REQUEST_TREASUREMAP,
  );

export const createObservationPlanRequestObservingRun = (id, params = {}) =>
  API.POST(
    `/api/observation_plan/${id}/observing_run`,
    CREATE_OBSERVATION_PLAN_REQUEST_OBSERVING_RUN,
    params,
  );

export const deleteObservationPlanFields = (id, fieldIds) =>
  API.DELETE(
    `/api/observation_plan/${id}/fields`,
    DELETE_OBSERVATION_PLAN_FIELDS,
    { fieldIds },
  );

export function fetchObservationPlan(id) {
  return API.GET(
    `/api/observation_plan/${id}?includePlannedObservations=true`,
    FETCH_OBSERVATION_PLAN_REQUEST,
  );
}

export function getCommentOnGcnEventAttachment(gcnEventID, commentID) {
  return API.GET(
    `/api/gcn_event/${gcnEventID}/comments/${commentID}/attachment`,
    GET_COMMENT_ON_GCNEVENT_ATTACHMENT,
  );
}

export function getCommentOnGcnEventTextAttachment(gcnEventID, commentID) {
  return API.GET(
    `/api/gcn_event/${gcnEventID}/comments/${commentID}/attachment?download=false&preview=false`,
    GET_COMMENT_ON_GCNEVENT_ATTACHMENT_PREVIEW,
  );
}

export function submitGcnEvent(data) {
  return API.POST("/api/gcn_event", SUBMIT_GCNEVENT, data);
}

export function postGcnEventSummary({ dateobs, params }) {
  return API.POST(
    `/api/gcn_event/${dateobs}/summary`,
    POST_GCNEVENT_SUMMARY,
    params,
  );
}

export function fetchGcnEventSummary({ dateobs, summaryID }) {
  return API.GET(
    `/api/gcn_event/${dateobs}/summary/${summaryID}`,
    FETCH_GCNEVENT_SUMMARY,
  );
}

export function deleteGcnEventSummary({ dateobs, summaryID }) {
  return API.DELETE(
    `/api/gcn_event/${dateobs}/summary/${summaryID}`,
    DELETE_GCNEVENT_SUMMARY,
  );
}

export function patchGcnEventSummary({ dateobs, summaryID, formData }) {
  return API.PATCH(
    `/api/gcn_event/${dateobs}/summary/${summaryID}`,
    PATCH_GCNEVENT_SUMMARY,
    formData,
  );
}

export function postGcnEventReport({ dateobs, params }) {
  return API.POST(
    `/api/gcn_event/${dateobs}/report`,
    POST_GCNEVENT_REPORT,
    params,
  );
}

export function fetchGcnEventReport({ dateobs, reportID }) {
  return API.GET(
    `/api/gcn_event/${dateobs}/report/${reportID}`,
    FETCH_GCNEVENT_REPORT,
  );
}

export function fetchGcnEventReports(dateobs) {
  return API.GET(`/api/gcn_event/${dateobs}/report`, FETCH_GCNEVENT_REPORTS);
}

export function deleteGcnEventReport({ dateobs, reportID }) {
  return API.DELETE(
    `/api/gcn_event/${dateobs}/report/${reportID}`,
    DELETE_GCNEVENT_REPORT,
  );
}

export function patchGcnEventReport({ dateobs, reportID, formData }) {
  return API.PATCH(
    `/api/gcn_event/${dateobs}/report/${reportID}`,
    PATCH_GCNEVENT_REPORT,
    formData,
  );
}

export function postGcnAlias(dateobs, params = {}) {
  return API.POST(`/api/gcn_event/${dateobs}/alias`, POST_GCN_ALIAS, params);
}

export function deleteGcnAlias(dateobs, params = {}) {
  return API.DELETE(
    `/api/gcn_event/${dateobs}/alias`,
    DELETE_GCN_ALIAS,
    params,
  );
}

export function postGcnTach(dateobs) {
  return API.POST(`/api/gcn_event/${dateobs}/tach`, POST_GCN_TACH);
}

export function fetchGcnTach(dateobs) {
  return API.GET(`/api/gcn_event/${dateobs}/tach`, FETCH_GCN_TACH);
}

export function postGcnGraceDB(dateobs) {
  return API.POST(`/api/gcn_event/${dateobs}/gracedb`, POST_GCN_GRACEDB);
}

export function putGcnTrigger({ dateobs, allocationID, triggered }) {
  return API.PUT(
    `/api/gcn_event/${dateobs}/triggered/${allocationID}`,
    PUT_GCN_TRIGGERED,
    { triggered },
  );
}

export function fetchGcnTrigger({ dateobs, allocationID = null }) {
  if (allocationID) {
    return API.GET(
      `/api/gcn_event/${dateobs}/triggered/${allocationID}`,
      FETCH_GCN_TRIGGERED,
    );
  }
  return API.GET(`/api/gcn_event/${dateobs}/triggered`, FETCH_GCN_TRIGGERED);
}

export function deleteGcnTrigger({ dateobs, allocationID }) {
  return API.DELETE(
    `/api/gcn_event/${dateobs}/triggered/${allocationID}`,
    DELETE_GCN_TRIGGERED,
  );
}

export function fetchGcnEventSurveyEfficiency({ gcnID }) {
  return API.GET(
    `/api/gcn_event/${gcnID}/survey_efficiency`,
    FETCH_GCNEVENT_SURVEY_EFFICIENCY,
  );
}

export function fetchGcnEventCatalogQueries({ gcnID }) {
  return API.GET(
    `/api/gcn_event/${gcnID}/catalog_query`,
    FETCH_GCNEVENT_CATALOG_QUERIES,
  );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { gcnEvent } = getState();
  const loaded_gcnevent_key = gcnEvent?.dateobs;
  const loaded_report_key = gcnEvent?.report?.id;

  if (actionType === FETCH_GCNEVENT) {
    dispatch(fetchGcnEvent(gcnEvent.dateobs)).then((response) => {
      if (response.status === "success") {
        dispatch(fetchGcnTach(gcnEvent.dateobs));
      }
    });
  }
  if (actionType === REFRESH_GCN_EVENT) {
    if (loaded_gcnevent_key === payload.gcnEvent_dateobs) {
      dispatch(fetchGcnEvent(gcnEvent.dateobs)).then((response) => {
        if (response.status === "success") {
          dispatch(fetchGcnTach(gcnEvent.dateobs));
        }
      });
    }
  }
  if (actionType === REFRESH_GCN_TRIGGERED) {
    if (loaded_gcnevent_key === payload.gcnEvent_dateobs) {
      dispatch(fetchGcnTrigger({ dateobs: gcnEvent.dateobs }));
    }
  }
  if (actionType === REFRESH_GCNEVENT_OBSERVATION_PLAN_REQUESTS) {
    if (loaded_gcnevent_key === payload.gcnEvent_dateobs) {
      dispatch(fetchObservationPlanRequests(gcnEvent?.id));
    }
  }
  if (actionType === REFRESH_GCNEVENT_CATALOG_QUERIES) {
    if (loaded_gcnevent_key === payload.gcnEvent_dateobs) {
      dispatch(fetchGcnEventCatalogQueries({ gcnID: gcnEvent?.id }));
    }
  }
  if (actionType === REFRESH_GCNEVENT_SURVEY_EFFICIENCY) {
    if (loaded_gcnevent_key === payload.gcnEvent_dateobs) {
      dispatch(fetchGcnEventSurveyEfficiency({ gcnID: gcnEvent?.id }));
    }
  }
  if (actionType === REFRESH_GCNEVENT_REPORT) {
    if (loaded_report_key === payload?.report_id) {
      dispatch(
        fetchGcnEventReport({
          dateobs: loaded_gcnevent_key,
          reportID: loaded_report_key,
        }),
      );
    }
  }
  if (actionType === REFRESH_GCNEVENT_REPORTS) {
    if (loaded_gcnevent_key === payload?.gcnEvent_dateobs) {
      dispatch(fetchGcnEventReports(loaded_gcnevent_key));
    }
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_GCNEVENT_OK: {
      if (action.data?.dateobs === state?.dateobs) {
        return {
          ...state,
          ...action.data,
        };
      }
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
    case FETCH_GCN_TRIGGERED_OK: {
      return {
        ...state,
        gcn_triggers: action.data,
      };
    }
    case FETCH_GCNEVENT_SURVEY_EFFICIENCY_OK: {
      return {
        ...state,
        survey_efficiency: action.data,
      };
    }
    case FETCH_GCNEVENT_CATALOG_QUERIES_OK: {
      return {
        ...state,
        catalog_queries: action.data,
      };
    }
    case FETCH_GCNEVENT_OBSERVATION_PLAN_REQUESTS_OK: {
      return {
        ...state,
        observation_plans: action.data,
      };
    }
    case FETCH_OBSERVATION_PLAN_REQUEST_OK: {
      return {
        ...state,
        observation_plan: action.data,
      };
    }
    case FETCH_GCNEVENT_REPORT_OK: {
      return {
        ...state,
        report: action.data,
      };
    }
    case FETCH_GCNEVENT_REPORTS_OK: {
      return {
        ...state,
        reports: action.data,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("gcnEvent", reducer);
