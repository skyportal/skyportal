import messageHandler from "baselayer/MessageHandler";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import * as API from "../API";
import store from "../store";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const FETCH_QUEUED_OBSERVATIONS = "skyportal/FETCH_QUEUED_OBSERVATIONS";
const FETCH_QUEUED_OBSERVATIONS_OK = "skyportal/FETCH_QUEUED_OBSERVATIONS_OK";

const FETCH_GCNEVENT_QUEUED_OBSERVATIONS =
  "skyportal/FETCH_GCNEVENT_QUEUED_OBSERVATIONS";
const FETCH_GCNEVENT_QUEUED_OBSERVATIONS_OK =
  "skyportal/FETCH_GCNEVENT_QUEUED_OBSERVATIONS_OK";

const REFRESH_QUEUED_OBSERVATIONS = "skyportal/REFRESH_QUEUED_OBSERVATIONS";

const REQUEST_API_QUEUED_OBSERVATIONS =
  "skyportal/REQUEST_API_QUEUED_OBSERVATIONS";

export function fetchQueuedObservations(filterParams = {}) {
  if (!Object.keys(filterParams).includes("startDate")) {
    filterParams.startDate = dayjs().utc().format("YYYY-MM-DDTHH:mm:ssZ");
  }

  if (!Object.keys(filterParams).includes("endDate")) {
    filterParams.endDate = dayjs()
      .utc()
      .add(7, "day")
      .utc()
      .format("YYYY-MM-DDTHH:mm:ssZ");
  }
  filterParams.observationStatus = "queued";

  return API.GET("/api/observation", FETCH_QUEUED_OBSERVATIONS, filterParams);
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
  if (actionType === REFRESH_QUEUED_OBSERVATIONS) {
    dispatch(fetchQueuedObservations());
  }
});

export function fetchGcnEventQueuedObservations(dateobs, filterParams = {}) {
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

  if (!Object.keys(filterParams).includes("numPerPage")) {
    filterParams.numPerPage = 10;
  }

  filterParams.observationStatus = "queued";

  return API.GET(
    "/api/observation",
    FETCH_GCNEVENT_QUEUED_OBSERVATIONS,
    filterParams
  );
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch, getState) => {
  const { gcnEvent } = getState();
  if (actionType === FETCH_GCNEVENT_QUEUED_OBSERVATIONS) {
    if (gcnEvent && gcnEvent.id === payload.gcnEvent.id) {
      dispatch(fetchGcnEventQueuedObservations(gcnEvent.dateobs));
    }
  }
});

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_QUEUED_OBSERVATIONS_OK: {
      return {
        ...state,
        queued_observations: action.data,
      };
    }
    case FETCH_GCNEVENT_QUEUED_OBSERVATIONS_OK: {
      return {
        ...state,
        gcnEventQueuedObservations: action.data,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("queued_observations", reducer);
