import * as API from "../API";
import store from "../store";

const FETCH_ALERTS = "skyportal/FETCH_ALERTS";
const FETCH_ALERTS_OK = "skyportal/FETCH_ALERTS_OK";
const FETCH_ALERTS_ERROR = "skyportal/FETCH_ALERTS_ERROR";
const FETCH_ALERTS_FAIL = "skyportal/FETCH_ALERTS_FAIL";

// eslint-disable-next-line import/prefer-default-export
export const fetchAlerts = ({ object_id, ra, dec, radius }) => {
  if (object_id?.length && ra && dec && radius) {
    return API.GET(
      `/api/alerts?objectId=${object_id}&ra=${ra}&dec=${dec}&radius=${radius}&radius_units=arcsec`,
      FETCH_ALERTS
    );
  }
  if (object_id?.length) {
    return API.GET(`/api/alerts?objectId=${object_id}`, FETCH_ALERTS);
  }
  if (ra && dec && radius) {
    return API.GET(
      `/api/alerts?ra=${ra}&dec=${dec}&radius=${radius}&radius_units=arcsec`,
      FETCH_ALERTS
    );
  }
  return API.GET(`/api/alerts?objectId=${object_id}`, FETCH_ALERTS);
};

const reducer = (state = { alerts: null, queryInProgress: false }, action) => {
  switch (action.type) {
    case FETCH_ALERTS: {
      return {
        ...state,
        queryInProgress: true,
      };
    }
    case FETCH_ALERTS_OK: {
      return {
        alerts: action.data,
        queryInProgress: false,
      };
    }
    case FETCH_ALERTS_ERROR: {
      return {
        message: action.message,
        queryInProgress: false,
      };
    }
    case FETCH_ALERTS_FAIL: {
      return {
        message: "uncaught error",
        queryInProgress: false,
      };
    }
    default:
      return state;
  }
};

store.injectReducer("alerts", reducer);
