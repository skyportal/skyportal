import * as API from "../API";
import store from "../store";

export const FETCH_ALERT = "skyportal/FETCH_ALERT";
export const FETCH_ALERT_OK = "skyportal/FETCH_ALERT_OK";
export const FETCH_ALERT_ERROR = "skyportal/FETCH_ALERT_ERROR";
export const FETCH_ALERT_FAIL = "skyportal/FETCH_ALERT_FAIL";

export const FETCH_AUX = "skyportal/FETCH_AUX";
export const FETCH_AUX_OK = "skyportal/FETCH_AUX_OK";
export const FETCH_AUX_ERROR = "skyportal/FETCH_AUX_ERROR";
export const FETCH_AUX_FAIL = "skyportal/FETCH_AUX_FAIL";

export const SAVE_ALERT = "skyportal/SAVE_ALERT";
export const SAVE_ALERT_OK = "skyportal/SAVE_ALERT_OK";

export function fetchAlertData(id) {
  return API.GET(`/api/alerts/ztf/${id}`, FETCH_ALERT);
}

export const fetchAuxData = (id) =>
  API.GET(`/api/alerts/ztf/${id}/aux`, FETCH_AUX);

export function saveAlertAsSource({ id, payload }) {
  return API.POST(`/api/alerts/ztf/${id}`, SAVE_ALERT, payload);
}

const alertDataReducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_ALERT_OK: {
      return action.data;
    }
    case FETCH_ALERT_ERROR: {
      return action.message;
    }
    case FETCH_ALERT_FAIL: {
      return "uncaught error";
    }
    default:
      return state;
  }
};

const auxDataReducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_AUX_OK: {
      return action.data;
    }
    case FETCH_AUX_ERROR: {
      return action.message;
    }
    case FETCH_AUX_FAIL: {
      return "uncaught error";
    }
    default:
      return state;
  }
};

store.injectReducer("alert_data", alertDataReducer);
store.injectReducer("alert_aux_data", auxDataReducer);
