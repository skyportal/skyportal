import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const REFRESH_SOURCE = "skyportal/REFRESH_SOURCE";
export const REFRESH_OBJ_ANALYSES = "skyportal/REFRESH_OBJ_ANALYSES";

const FETCH_LOADED_SOURCE = "skyportal/FETCH_LOADED_SOURCE";
const FETCH_LOADED_SOURCE_OK = "skyportal/FETCH_LOADED_SOURCE_OK";
const FETCH_LOADED_SOURCE_ERROR = "skyportal/FETCH_LOADED_SOURCE_ERROR";
const FETCH_LOADED_SOURCE_FAIL = "skyportal/FETCH_LOADED_SOURCE_FAIL";

const ADD_CLASSIFICATION = "skyportal/ADD_CLASSIFICATION";

const DELETE_CLASSIFICATION = "skyportal/DELETE_CLASSIFICATION";

const ADD_CLASSIFICATION_VOTE = "skyportal/ADD_CLASSIFICATION_VOTE";

const DELETE_CLASSIFICATION_VOTE = "skyportal/DELETE_CLASSIFICATION_VOTE";

const DELETE_CLASSIFICATIONS = "skyportal/DELETE_CLASSIFICATIONS";

const ADD_SOURCE_TNS = "skyportal/ADD_SOURCE_TNS";

const ADD_COMMENT = "skyportal/ADD_COMMENT";

const ADD_ANNOTATION = "skyportal/ADD_ANNOTATION";

const DELETE_ANNOTATION = "skyportal/DELETE_ANNOTATION";

const EDIT_COMMENT = "skyportal/EDIT_COMMENT";

const DELETE_COMMENT = "skyportal/DELETE_COMMENT";
const DELETE_COMMENT_ON_SPECTRUM = "skyportal/DELETE_COMMENT_ON_SPECTRUM";

const GET_COMMENT_ATTACHMENT = "skyportal/GET_COMMENT_ATTACHMENT";
const GET_COMMENT_ATTACHMENT_OK = "skyportal/GET_COMMENT_ATTACHMENT_OK";

const GET_COMMENT_ATTACHMENT_PREVIEW =
  "skyportal/GET_COMMENT_ATTACHMENT_PREVIEW";
const GET_COMMENT_ATTACHMENT_PREVIEW_OK =
  "skyportal/GET_COMMENT_ATTACHMENT_PREVIEW_OK";

const GET_COMMENT_ON_SPECTRUM_ATTACHMENT =
  "skyportal/GET_COMMENT_ON_SPECTRUM_ATTACHMENT";
const GET_COMMENT_ON_SPECTRUM_ATTACHMENT_OK =
  "skyportal/GET_COMMENT_ON_SPECTRUM_ATTACHMENT_OK";

const GET_COMMENT_ON_SPECTRUM_ATTACHMENT_PREVIEW =
  "skyportal/GET_COMMENT_ON_SPECTRUM_ATTACHMENT_PREVIEW";
const GET_COMMENT_ON_SPECTRUM_ATTACHMENT_PREVIEW_OK =
  "skyportal/GET_COMMENT_ON_SPECTRUM_ATTACHMENT_PREVIEW_OK";

const ADD_SOURCE_VIEW = "skyportal/ADD_SOURCE_VIEW";

const ADD_SOURCE_LABEL = "skyportal/ADD_SOURCE_LABEL";

const DELETE_SOURCE_LABEL = "skyportal/DELETE_SOURCE_LABEL";

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

const GET_PHOTOMETRY_REQUEST = "skyportal/GET_PHOTOMETRY_REQUEST";

const UPLOAD_PHOTOMETRY = "skyportal/UPLOAD_PHOTOMETRY";

const SHARE_DATA = "skyportal/SHARE_DATA";

const SEND_ALERT = "skyportal/SEND_ALERT";

const FETCH_GAIA = "skyportal/FETCH_GAIA";

const FETCH_WISE = "skyportal/FETCH_WISE";

const FETCH_VIZIER = "skyportal/FETCH_VIZIER";

const FETCH_PHOTOZ = "skyportal/FETCH_PHOTOZ";

const FETCH_PS1 = "skyportal/FETCH_PS1";

const CHECK_SOURCE = "skyportal/CHECK_SOURCE";

const FETCH_ASSOCIATED_GCNS = "skyportal/FETCH_ASSOCIATED_GCNS";
const FETCH_ASSOCIATED_GCNS_OK = "skyportal/FETCH_ASSOCIATED_GCNS_OK";
const START_ANALYSIS_FOR_OBJ = "skyportal/START_SERVICE_FOR_OBJ";
const DELETE_ANALYSIS = "skyportal/DELETE_ANALYSIS";

const FETCH_ANALYSES_FOR_OBJ = "skyportal/FETCH_ANALYSES_FOR_OBJ";
const FETCH_ANALYSES_FOR_OBJ_OK = "skyportal/FETCH_ANALYSES_FOR_OBJ_OK";
const FETCH_ANALYSIS_FOR_OBJ = "skyportal/FETCH_ANALYSIS_FOR_OBJ";
const FETCH_ANALYSIS_RESULTS_FOR_OBJ = "skyportal/FETCH_ANALYSIS_FOR_OBJ";

const COPY_SOURCE_PHOTOMETRY = "skyportal/COPY_SOURCE_PHOTOMETRY";

const ADD_TNS = "skyportal/ADD_TNS";

const ADD_HOST = "skyportal/ADD_HOST";

const REMOVE_HOST = "skyportal/REMOVE_HOST";

const ADD_MPC = "skyportal/ADD_MPC";

const ADD_GCN_CROSSMATCH = "skyportal/ADD_GCN_CROSSMATCH";

const FETCH_LOADED_SOURCE_POSITION = "skyportal/FETCH_LOADED_SOURCE_POSITION";
const FETCH_LOADED_SOURCE_POSITION_OK =
  "skyportal/FETCH_LOADED_SOURCE_POSITION_OK";
const REFRESH_SOURCE_POSITION = "skyportal/REFRESH_SOURCE_POSITION";

export function fetchPosition(id) {
  return API.GET(`/api/sources/${id}/position`, FETCH_LOADED_SOURCE_POSITION);
}

export function addGCNCrossmatch(id, formData) {
  return API.POST(`/api/sources/${id}/gcn_event`, ADD_GCN_CROSSMATCH, formData);
}

export function addMPC(id, formData) {
  return API.POST(`/api/sources/${id}/mpc`, ADD_MPC, formData);
}

export function addHost(id, formData) {
  return API.POST(`/api/sources/${id}/host`, ADD_HOST, formData);
}

export function removeHost(id) {
  return API.DELETE(`/api/sources/${id}/host`, REMOVE_HOST);
}

export function addTNS(id, formData) {
  return API.GET(`/api/sources/${id}/tns`, ADD_TNS, formData);
}

export const shareData = (data) => API.POST("/api/sharing", SHARE_DATA, data);

export const uploadPhotometry = (data) =>
  API.POST("/api/photometry?refresh=true", UPLOAD_PHOTOMETRY, data);

export function copySourcePhotometry(id, formData = {}) {
  return API.POST(
    `/api/sources/${id}/copy_photometry`,
    COPY_SOURCE_PHOTOMETRY,
    formData,
  );
}

export function addClassification(formData) {
  return API.POST(`/api/classification`, ADD_CLASSIFICATION, formData);
}

export function addClassificationVote(classification_id, data = {}) {
  return API.POST(
    `/api/classification/votes/${classification_id}`,
    ADD_CLASSIFICATION_VOTE,
    data,
  );
}

export function addSourceTNS(id, formData) {
  return API.POST(`/api/sources/${id}/tns`, ADD_SOURCE_TNS, formData);
}

export function startAnalysis(id, analysis_service_id, formData = {}) {
  return API.POST(
    `/api/obj/${id}/analysis/${analysis_service_id}`,
    START_ANALYSIS_FOR_OBJ,
    formData,
  );
}

export function deleteAnalysis(analysis_id, formData = {}) {
  return API.DELETE(
    `/api/obj/analysis/${analysis_id}`,
    DELETE_ANALYSIS,
    formData,
  );
}

export function fetchAnalyses(analysis_resource_type = "obj", params = {}) {
  return API.GET(
    `/api/${analysis_resource_type}/analysis`,
    FETCH_ANALYSES_FOR_OBJ,
    params,
  );
}

export function fetchAnalysis(
  analysis_id,
  analysis_resource_type = "obj",
  params = {},
) {
  return API.GET(
    `/api/${analysis_resource_type}/analysis/${analysis_id}`,
    FETCH_ANALYSIS_FOR_OBJ,
    params,
  );
}

export function fetchAnalysisResults(
  analysis_id,
  analysis_resource_type = "obj",
  params = {},
) {
  return API.GET(
    `/api/${analysis_resource_type}/analysis/${analysis_id}/results`,
    FETCH_ANALYSIS_RESULTS_FOR_OBJ,
    params,
  );
}

export function deleteClassification(classification_id) {
  return API.DELETE(
    `/api/classification/${classification_id}`,
    DELETE_CLASSIFICATION,
  );
}

export function deleteClassificationVote(classification_id) {
  return API.DELETE(
    `/api/classification/votes/${classification_id}`,
    DELETE_CLASSIFICATION_VOTE,
  );
}

export function deleteClassifications(source_id) {
  return API.DELETE(
    `/api/sources/${source_id}/classifications`,
    DELETE_CLASSIFICATIONS,
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

        if (formData.spectrum_id) {
          dispatch(
            API.POST(
              `/api/spectra/${formData.spectrum_id}/comments`,
              ADD_COMMENT,
              formData,
            ),
          );
        } else {
          dispatch(
            API.POST(
              `/api/sources/${formData.obj_id}/comments`,
              ADD_COMMENT,
              formData,
            ),
          );
        }
      });
    };
  }
  if (formData.spectrum_id) {
    return API.POST(
      `/api/spectra/${formData.spectrum_id}/comments`,
      ADD_COMMENT,
      formData,
    );
  }
  return API.POST(
    `/api/sources/${formData.obj_id}/comments`,
    ADD_COMMENT,
    formData,
  );
}

export function addAnnotation(sourceID, formData) {
  return API.POST(
    `/api/sources/${sourceID}/annotations`,
    ADD_ANNOTATION,
    formData,
  );
}

export function deleteAnnotation(sourceID, annotationID) {
  return API.DELETE(
    `/api/sources/${sourceID}/annotations/${annotationID}`,
    DELETE_ANNOTATION,
  );
}

export function deleteComment(sourceID, commentID) {
  return API.DELETE(
    `/api/sources/${sourceID}/comments/${commentID}`,
    DELETE_COMMENT,
  );
}

export function deleteCommentOnSpectrum(spectrumID, commentID) {
  return API.DELETE(
    `/api/spectra/${spectrumID}/comments/${commentID}`,
    DELETE_COMMENT_ON_SPECTRUM,
  );
}

export function editComment(commentID, formData) {
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

        if (formData.spectrum_id) {
          dispatch(
            API.PUT(
              `/api/spectra/${formData.spectrum_id}/comments/${commentID}`,
              EDIT_COMMENT,
              formData,
            ),
          );
        } else {
          dispatch(
            API.PUT(
              `/api/sources/${formData.obj_id}/comments/${commentID}`,
              EDIT_COMMENT,
              formData,
            ),
          );
        }
      });
    };
  }
  if (formData.spectrum_id) {
    return API.PUT(
      `/api/spectra/${formData.spectrum_id}/comments/${commentID}`,
      EDIT_COMMENT,
      formData,
    );
  }
  return API.PUT(
    `/api/sources/${formData.obj_id}/comments/${commentID}`,
    EDIT_COMMENT,
    formData,
  );
}

export function getCommentAttachment(sourceID, commentID) {
  return API.GET(
    `/api/sources/${sourceID}/comments/${commentID}/attachment`,
    GET_COMMENT_ATTACHMENT,
  );
}

export function getCommentTextAttachment(sourceID, commentID) {
  return API.GET(
    `/api/sources/${sourceID}/comments/${commentID}/attachment?download=false&preview=false`,
    GET_COMMENT_ATTACHMENT_PREVIEW,
  );
}

export function getCommentOnSpectrumAttachment(spectrumID, commentID) {
  return API.GET(
    `/api/spectra/${spectrumID}/comments/${commentID}/attachment`,
    GET_COMMENT_ON_SPECTRUM_ATTACHMENT,
  );
}

export function getCommentOnSpectrumTextAttachment(spectrumID, commentID) {
  return API.GET(
    `/api/spectra/${spectrumID}/comments/${commentID}/attachment?download=false&preview=false`,
    GET_COMMENT_ON_SPECTRUM_ATTACHMENT_PREVIEW,
  );
}

export function fetchSource(id, actionType = FETCH_LOADED_SOURCE) {
  const urlParams = {
    includeComments: true,
    includeColorMagnitude: true,
    includeThumbnails: true,
    includePhotometryExists: true,
    includeSpectrumExists: true,
    includeLabellers: true,
    includeDetectionStats: true,
    includeGCNCrossmatches: true,
    includeGCNNotes: true,
    includeCandidates: true,
  };
  const queryString = new URLSearchParams(urlParams).toString();
  return API.GET(`/api/sources/${id}?${queryString}`, actionType);
}

export function checkSource(id, params, actionType = CHECK_SOURCE) {
  if ("nameOnly" in params && params.nameOnly === true) {
    return API.GET(`/api/source_exists/${id}`, actionType);
  }
  return API.GET(
    `/api/source_exists/${id}?ra=${params.ra}&dec=${params.dec}&radius=0.0003`,
    actionType,
  );
}

export function addSourceView(id) {
  return API.POST(`/api/internal/source_views/${id}`, ADD_SOURCE_VIEW);
}

export function addSourceLabels(id, data) {
  return API.POST(`/api/sources/${id}/labels`, ADD_SOURCE_LABEL, data);
}

export function deleteSourceLabels(id, data) {
  return API.DELETE(`/api/sources/${id}/labels`, DELETE_SOURCE_LABEL, data);
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
    paramsToSubmit,
  );
};

export const editFollowupRequest = (params, requestID) => {
  const { instrument_name, ...paramsToSubmit } = params;
  return API.PUT(
    `/api/followup_request/${requestID}`,
    EDIT_FOLLOWUP_REQUEST,
    paramsToSubmit,
  );
};

export const deleteFollowupRequest = (id, params = {}) =>
  API.DELETE(`/api/followup_request/${id}`, DELETE_FOLLOWUP_REQUEST, params);

export const getPhotometryRequest = (id, params = {}) =>
  API.GET(`/api/photometry_request/${id}`, GET_PHOTOMETRY_REQUEST, params);

export const submitAssignment = (params) =>
  API.POST("/api/assignment", SUBMIT_ASSIGNMENT, params);

export const editAssignment = (params, assignmentID) =>
  API.PUT(`/api/assignment/${assignmentID}`, EDIT_ASSIGNMENT, params);

export const deleteAssignment = (id) =>
  API.DELETE(`/api/assignment/${id}`, DELETE_ASSIGNMENT);

export const sendAlert = (params) =>
  API.POST(`/api/source_notifications`, SEND_ALERT, params);

export const fetchGaia = (sourceID) =>
  API.POST(`/api/sources/${sourceID}/annotations/gaia`, FETCH_GAIA);

export const fetchWise = (sourceID) =>
  API.POST(`/api/sources/${sourceID}/annotations/irsa`, FETCH_WISE);

export const fetchVizier = (sourceID, catalog = "VII/290") =>
  API.POST(`/api/sources/${sourceID}/annotations/vizier`, FETCH_VIZIER, {
    catalog,
  });

export const fetchPhotoz = (sourceID) =>
  API.POST(`/api/sources/${sourceID}/annotations/datalab`, FETCH_PHOTOZ);

export const fetchPS1 = (sourceID) =>
  API.POST(`/api/sources/${sourceID}/annotations/ps1`, FETCH_PS1);

export const fetchAssociatedGCNs = (sourceID) =>
  API.GET(`/api/associated_gcns/${sourceID}`, FETCH_ASSOCIATED_GCNS);

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { source } = getState();
  if (actionType === REFRESH_SOURCE) {
    const loaded_obj_key = source?.internal_key;
    if (loaded_obj_key === payload.obj_key) {
      dispatch(fetchSource(source.id));
    }
  } else if (actionType === REFRESH_SOURCE_POSITION) {
    const loaded_obj_key = source?.internal_key;
    if (loaded_obj_key === payload.obj_key) {
      dispatch(fetchPosition(source.id));
    }
  } else if (actionType === REFRESH_OBJ_ANALYSES) {
    const loaded_obj_key = source?.internal_key;
    if (loaded_obj_key === payload.obj_key) {
      dispatch(fetchAnalyses("obj", { obj_id: source.id }));
    }
  }
});

// Reducer for currently displayed source
const reducer = (
  state = {
    source: null,
    loadError: false,
    associatedGCNs: null,
    analyses: null,
  },
  action,
) => {
  switch (action.type) {
    case FETCH_LOADED_SOURCE_OK: {
      const source = action.data;
      return {
        ...state,
        host: null,
        host_offset: null,
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
        loadError: `Error while loading source: ${action.message}`,
      };
    case GET_COMMENT_ATTACHMENT_OK: {
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
    case GET_COMMENT_ATTACHMENT_PREVIEW_OK: {
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
    case GET_COMMENT_ON_SPECTRUM_ATTACHMENT_OK: {
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
    case GET_COMMENT_ON_SPECTRUM_ATTACHMENT_PREVIEW_OK: {
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
    case FETCH_ASSOCIATED_GCNS_OK: {
      const { gcns } = action.data;
      return {
        ...state,
        associatedGCNs: gcns,
      };
    }
    case FETCH_ANALYSES_FOR_OBJ_OK: {
      const { data } = action;
      return {
        ...state,
        analyses: data,
      };
    }
    case FETCH_LOADED_SOURCE_POSITION_OK: {
      const { ra, dec, gal_lon, gal_lat, ebv, separation } = action.data;
      return {
        ...state,
        adjusted_position: {
          ra,
          dec,
          gal_lon,
          gal_lat,
          ebv,
          separation,
        },
      };
    }
    default:
      return state;
  }
};

store.injectReducer("source", reducer);
