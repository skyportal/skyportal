import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";
import type { AppDispatch, RootState } from "../types/store";

const REFRESH_EARTHQUAKE = "skyportal/REFRESH_EARTHQUAKE";

const FETCH_EARTHQUAKE = "skyportal/FETCH_EARTHQUAKE";
const FETCH_EARTHQUAKE_OK = "skyportal/FETCH_EARTHQUAKE_OK";

const REFRESH_EARTHQUAKES = "skyportal/REFRESH_EARTHQUAKES";

const FETCH_EARTHQUAKES = "skyportal/FETCH_EARTHQUAKES";
const FETCH_EARTHQUAKES_OK = "skyportal/FETCH_EARTHQUAKES_OK";

const SUBMIT_EARTHQUAKE = "skyportal/SUBMIT_EARTHQUAKE";

const CURRENT_EARTHQUAKES_AND_MENU = "skyportal/CURRENT_EARTHQUAKES_AND_MENU";

const ADD_COMMENT_ON_EARTHQUAKE = "skyportal/ADD_COMMENT_ON_EARTHQUAKE";

const DELETE_COMMENT_ON_EARTHQUAKE = "skyportal/DELETE_COMMENT_ON_EARTHQUAKE";

const GET_COMMENT_ON_EARTHQUAKE_ATTACHMENT =
  "skyportal/GET_COMMENT_ON_EARTHQUAKE_ATTACHMENT";
const GET_COMMENT_ON_EARTHQUAKE_ATTACHMENT_OK =
  "skyportal/GET_COMMENT_ON_EARTHQUAKE_ATTACHMENT_OK";

const GET_COMMENT_ON_EARTHQUAKE_ATTACHMENT_PREVIEW =
  "skyportal/GET_COMMENT_ON_EARTHQUAKE_ATTACHMENT_PREVIEW";
const GET_COMMENT_ON_EARTHQUAKE_ATTACHMENT_PREVIEW_OK =
  "skyportal/GET_COMMENT_ON_EARTHQUAKE_ATTACHMENT_PREVIEW_OK";

const ADD_EARTHQUAKE_PREDICTION = "skyportal/ADD_EARTHQUAKE_PREDICTION";

export const fetchEarthquake = (id: number | string) =>
  API.GET(`/api/earthquake/${id}`, FETCH_EARTHQUAKE);

export const submitEarthquake = (run: any) =>
  API.POST(`/api/earthquake`, SUBMIT_EARTHQUAKE, run);

export const submitPrediction = (
  id: number | string,
  mmadetector_id: number | string,
  params = {},
) =>
  API.POST(
    `/api/earthquake/${id}/mmadetector/${mmadetector_id}/predictions`,
    ADD_EARTHQUAKE_PREDICTION,
    params,
  );

export const fetchEarthquakes = (params = {}) =>
  API.GET("/api/earthquake", FETCH_EARTHQUAKES, params);

export function addCommentOnEarthquake(formData: any) {
  function fileReaderPromise(file: any) {
    return new Promise((resolve) => {
      const filereader = new FileReader();
      filereader.readAsDataURL(file);
      filereader.onloadend = () =>
        resolve({ body: filereader.result, name: file.name });
    });
  }
  if (formData.attachment) {
    return (dispatch: AppDispatch) => {
      fileReaderPromise(formData.attachment).then((fileData) => {
        formData.attachment = fileData;

        dispatch(
          API.POST(
            `/api/earthquake/${formData.earthquake_id}/comments`,
            ADD_COMMENT_ON_EARTHQUAKE,
            formData,
          ),
        );
      });
    };
  }
  return API.POST(
    `/api/earthquake/${formData.earthquake_id}/comments`,
    ADD_COMMENT_ON_EARTHQUAKE,
    formData,
  );
}

export function deleteCommentOnEarthquake(
  earthquakeID: number | string,
  commentID: number | string,
) {
  return API.DELETE(
    `/api/earthquake/${earthquakeID}/comments/${commentID}`,
    DELETE_COMMENT_ON_EARTHQUAKE,
  );
}

export function getCommentOnEarthquakeAttachment(
  earthquakeID: number | string,
  commentID: number | string,
) {
  return API.GET(
    `/api/earthquake/${earthquakeID}/comments/${commentID}/attachment`,
    GET_COMMENT_ON_EARTHQUAKE_ATTACHMENT,
  );
}

export function getCommentOnEarthquakeTextAttachment(
  earthquakeID: number | string,
  commentID: number | string,
) {
  return API.GET(
    `/api/earthquake/${earthquakeID}/comments/${commentID}/attachment?download=false&preview=false`,
    GET_COMMENT_ON_EARTHQUAKE_ATTACHMENT_PREVIEW,
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
    const { earthquake } = getState();
    if (actionType === REFRESH_EARTHQUAKE) {
      const { earthquake_event_id } = payload;
      if (earthquake_event_id === earthquake?.event_id) {
        dispatch(fetchEarthquake(earthquake.event_id));
      }
    }
    if (actionType === REFRESH_EARTHQUAKES) {
      dispatch(fetchEarthquakes());
    }
  },
);

interface EarthquakeAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer_earthquake = (
  state: Record<string, any> = {
    currentEarthquakes: null,
    currentEarthquakeMenu: "Earthquake List",
  },
  action: EarthquakeAction,
): Record<string, any> => {
  switch (action.type) {
    case GET_COMMENT_ON_EARTHQUAKE_ATTACHMENT_OK: {
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
    case GET_COMMENT_ON_EARTHQUAKE_ATTACHMENT_PREVIEW_OK: {
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
    case FETCH_EARTHQUAKE_OK: {
      const earthquake = action.data;
      return {
        ...state,
        ...earthquake,
      };
    }
    case CURRENT_EARTHQUAKES_AND_MENU: {
      const earthquake: Record<string, any> = {};
      earthquake.currentEarthquakes = action.data.currentEarthquakes;
      earthquake.currentEarthquakeMenu = action.data.currentEarthquakeMenu;
      return {
        ...state,
        ...earthquake,
      };
    }
    default:
      return state;
  }
};

type EarthquakesState = any;

const reducer_earthquakes = (
  state: EarthquakesState = null,
  action: EarthquakeAction,
): EarthquakesState => {
  switch (action.type) {
    case FETCH_EARTHQUAKES_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("earthquake", reducer_earthquake);
store.injectReducer("earthquakes", reducer_earthquakes);
