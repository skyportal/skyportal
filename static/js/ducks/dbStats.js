import * as API from "../API";
import store from "../store";

const FETCH_DB_STATS = "skyportal/FETCH_DB_STATS";
const FETCH_DB_STATS_OK = "skyportal/FETCH_DB_STATS_OK";

export const fetchDBStats = () => API.GET("/api/db_stats", FETCH_DB_STATS);

const reducer = (state = null, action) => {
  switch (action.type) {
    case FETCH_DB_STATS_OK: {
      return action.data;
    }
    default:
      return state;
  }
};

store.injectReducer("dbStats", reducer);
