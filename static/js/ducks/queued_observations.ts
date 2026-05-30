import messageHandler from "baselayer/MessageHandler";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import * as API from "../API";
import store from "../store";
import type { AppDispatch, RootState } from "../types/store";

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

const REQUEST_API_QUEUES = "skyportal/REQUEST_API_QUEUES";

const DELETE_API_QUEUE = "skyportal/DELETE_API_QUEUE";

export function fetchQueuedObservations(
  filterParams: Record<string, any> = {},
) {
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

export function requestAPIQueuedObservations(id: number | string, data = {}) {
  return API.GET(
    `/api/observation/external_api/${id}`,
    REQUEST_API_QUEUED_OBSERVATIONS,
    data,
  );
}

export function requestAPIQueues(
  id: number | string,
  data = { queuesOnly: true },
) {
  return API.GET(
    `/api/observation/external_api/${id}`,
    REQUEST_API_QUEUES,
    data,
  );
}

export function deleteAPIQueue(id: number | string, data = {}) {
  return API.DELETE(
    `/api/observation/external_api/${id}`,
    DELETE_API_QUEUE,
    data,
  );
}

// Websocket message handler
messageHandler.add(
  (actionType: string, payload: any, dispatch: AppDispatch) => {
    if (actionType === REFRESH_QUEUED_OBSERVATIONS) {
      dispatch(fetchQueuedObservations());
    }
  },
);

export function fetchGcnEventQueuedObservations(
  dateobs: string,
  filterParams: Record<string, any> = {},
) {
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
    filterParams,
  );
}

// Websocket message handler
messageHandler.add(
  (
    actionType: string,
    payload: any,
    dispatch: AppDispatch,
    getState: () => RootState,
  ) => {
    const { gcnEvent } = getState();
    if (actionType === FETCH_GCNEVENT_QUEUED_OBSERVATIONS) {
      if (gcnEvent && gcnEvent.id === payload.gcnEvent.id) {
        dispatch(fetchGcnEventQueuedObservations(gcnEvent.dateobs));
      }
    }
  },
);

type QueuedObservationsState = Record<string, any> | null;

interface QueuedObservationsAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (
  state: QueuedObservationsState = null,
  action: QueuedObservationsAction,
): QueuedObservationsState => {
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
