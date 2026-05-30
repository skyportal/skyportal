import * as API from "../API";
import store from "../store";

const FETCH_DB_STATS = "skyportal/FETCH_DB_STATS";
const FETCH_DB_STATS_OK = "skyportal/FETCH_DB_STATS_OK";

export const fetchDBStats = () => API.GET("/api/db_stats", FETCH_DB_STATS);

export type DBStatsState = Record<string, unknown> | null;

interface DBStatsAction {
  type: string;
  data?: Record<string, unknown>;
}

const reducer = (
  state: DBStatsState = null,
  action: DBStatsAction,
): DBStatsState => {
  switch (action.type) {
    case FETCH_DB_STATS_OK: {
      return action.data ?? null;
    }
    default:
      return state;
  }
};

store.injectReducer("dbStats", reducer);
