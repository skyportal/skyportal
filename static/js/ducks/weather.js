import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

export const FETCH_WEATHER = "skyportal/FETCH_WEATHER";
export const FETCH_WEATHER_OK = "skyportal/FETCH_WEATHER_OK";

export function fetchWeather() {
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
      const weather = action.data;
      return {
        weather,
      };
    }
    default:
      return state;
  }
};

export default fetchWeather;
store.injectReducer("weather", reducer);
