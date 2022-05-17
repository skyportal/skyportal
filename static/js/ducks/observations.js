import messageHandler from "baselayer/MessageHandler";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import * as API from "../API";
import store from "../store";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const FETCH_OBSERVATIONS = "skyportal/FETCH_OBSERVATIONS";
const FETCH_OBSERVATIONS_OK = "skyportal/FETCH_OBSERVATIONS_OK";

const FETCH_GCNEVENT_OBSERVATIONS = "skyportal/FETCH_GCNEVENT_OBSERVATIONS";
const FETCH_GCNEVENT_OBSERVATIONS_OK =
  "skyportal/FETCH_GCNEVENT_OBSERVATIONS_OK";

const SUBMIT_OBSERVATIONS = "skyportal/SUBMIT_OBSERVATIONS";

const UPLOAD_OBSERVATIONS = "skyportal/UPLOAD_OBSERVATIONS";

const REFRESH_OBSERVATIONS = "skyportal/REFRESH_OBSERVATIONS";

const SUBMIT_OBSERVATIONS_TREASUREMAP =
  "skyportal/SUBMIT_OBSERVATIONS_TREASUREMAP";
const DELETE_OBSERVATIONS_TREASUREMAP =
  "skyportal/DELETE_OBSERVATIONS_TREASUREMAP";
const REQUEST_API_OBSERVATIONS = "skyportal/REQUEST_API_OBSERVATIONS";
const REQUEST_API_QUEUED_OBSERVATIONS =
  "skyportal/REQUEST_API_QUEUED_OBSERVATIONS";

export const submitObservations = (params) =>
  API.POST(`/api/observation`, SUBMIT_OBSERVATIONS, params);

export function fetchObservations(filterParams = {}) {
  if (!Object.keys(filterParams).includes("startDate")) {
    filterParams.startDate = dayjs()
      .utc()
      .subtract(3650, "day")
      .utc()
      .format("YYYY-MM-DDTHH:mm:ssZ");
  }

  if (!Object.keys(filterParams).includes("endDate")) {
    filterParams.endDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  }

  if (!Object.keys(filterParams).includes("numPerPage")) {
    filterParams.numPerPage = 10;
  }

  return API.GET("/api/observation", FETCH_OBSERVATIONS, filterParams);
}

export function uploadObservations(data) {
  return API.POST(`/api/observation/ascii`, UPLOAD_OBSERVATIONS, data);
}

export function requestAPIObservations(data) {
  return API.POST(
    `/api/observation/external_api`,
    REQUEST_API_OBSERVATIONS,
    data
  );
}

export function requestAPIQueuedObservations(id, data = {}) {
  return API.GET(
    `/api/observation/external_api/${id}`,
    REQUEST_API_QUEUED_OBSERVATIONS,
    data
  );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === REFRESH_OBSERVATIONS) {
    dispatch(fetchObservations());
  }
});

export function fetchGcnEventObservations(dateobs, filterParams = {}) {
  filterParams.localizationDateobs = dateobs;

  if (!Object.keys(filterParams).includes("startDate")) {
    if (dateobs) {
      filterParams.startDate = dayjs(dateobs).format("YYYY-MM-DD HH:mm:ss");
    }
  }

  if (!Object.keys(filterParams).includes("endDate")) {
    if (dateobs) {
      filterParams.endDate = dayjs(dateobs)
        .add(7, "day")
        .format("YYYY-MM-DD HH:mm:ss");
    }
  }

  return API.GET("/api/observation", FETCH_GCNEVENT_OBSERVATIONS, filterParams);
}

export const submitObservationsTreasureMap = (id, data) =>
  API.POST(
    `/api/observation/treasuremap/${id}`,
    SUBMIT_OBSERVATIONS_TREASUREMAP,
    data
  );

export const deleteObservationsTreasureMap = (id, data) =>
  API.DELETE(
    `/api/observation/treasuremap/${id}`,
    DELETE_OBSERVATIONS_TREASUREMAP,
    data
  );

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { gcnEvent } = getState();
  if (actionType === FETCH_GCNEVENT_OBSERVATIONS) {
    if (gcnEvent && gcnEvent.id === payload.gcnEvent.id) {
      dispatch(fetchGcnEventObservations(gcnEvent.dateobs));
    }
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_OBSERVATIONS_OK: {
      return {
        ...state,
        observations: action.data,
      };
    }
    case FETCH_GCNEVENT_OBSERVATIONS_OK: {
      return {
        ...state,
        gcnEventObservations: action.data,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("observations", reducer);
