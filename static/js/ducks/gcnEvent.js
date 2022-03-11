import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const REFRESH_GCNEVENT = "skyportal/REFRESH_GCNEVENT";

export const FETCH_GCNEVENT = "skyportal/FETCH_GCNEVENT";
export const FETCH_GCNEVENT_OK = "skyportal/FETCH_GCNEVENT_OK";

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
    default:
      return state;
  }
};

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

store.injectReducer("gcnEvent", reducer);
