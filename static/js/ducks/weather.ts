import messageHandler from "baselayer/MessageHandler";

import * as API from "../API";
import store from "../store";

const FETCH_WEATHER = "skyportal/FETCH_WEATHER";
const FETCH_WEATHER_OK = "skyportal/FETCH_WEATHER_OK";

export function fetchWeather(telescope_id: number | string | null = null) {
  if (telescope_id) {
    return API.GET(`/api/weather?telescope_id=${telescope_id}`, FETCH_WEATHER);
  }
  return API.GET(`/api/weather`, FETCH_WEATHER);
}

// Websocket message handler
messageHandler.add((actionType: any, _payload: any, dispatch: any) => {
  if (actionType === FETCH_WEATHER) {
    dispatch(fetchWeather());
  }
});

interface WeatherAction {
  type: string;
  data?: any;
  [key: string]: any;
}

const reducer = (
  state: Record<string, any> = { weather: undefined },
  action: WeatherAction,
): Record<string, any> => {
  switch (action.type) {
    case FETCH_WEATHER_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("weather", reducer);
