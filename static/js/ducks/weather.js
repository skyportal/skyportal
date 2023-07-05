import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_WEATHER = "skyportal/FETCH_WEATHER";
const FETCH_WEATHER_OK = "skyportal/FETCH_WEATHER_OK";

// eslint-disable-next-line import/prefer-default-export
export function fetchWeather(telescope_id = null) {
  if (telescope_id) {
    return API.GET(`/api/weather?telescope_id=${telescope_id}`, FETCH_WEATHER);
  }
  return API.GET(`/api/weather`, FETCH_WEATHER);
}

// Websocket message handler
messageHandler.add((actionType, payload, dispatch) => {
  if (actionType === FETCH_WEATHER) {
    dispatch(fetchWeather());
  }
});

const reducer = (state = { weather: undefined }, action) => {
  switch (action.type) {
    case FETCH_WEATHER_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("weather", reducer);
