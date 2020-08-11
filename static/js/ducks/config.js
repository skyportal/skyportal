import * as API from "../API";

export const FETCH_CONFIG = "skyportal/FETCH_CONFIG";
export const FETCH_CONFIG_OK = "skyportal/FETCH_CONFIG_OK";

export function fetchConfig() {
  return API.GET("/api/internal/config", FETCH_CONFIG);
}

export default function reducer(state = {}, action) {
  switch (action.type) {
    case FETCH_CONFIG_OK:
      return action.data.config;
    default:
      return state;
  }
}
