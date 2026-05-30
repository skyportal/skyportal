import * as API from "../API";
import store from "../store";

const FETCH_SYSINFO = "skyportal/FETCH_SYSINFO";
const FETCH_SYSINFO_OK = "skyportal/FETCH_SYSINFO_OK";

export function fetchSystemInfo() {
  return API.GET("/api/sysinfo", FETCH_SYSINFO);
}

interface SysInfoAction {
  type: string;
  data?: any;
  version?: any;
  [key: string]: any;
}

function reducer(
  state: Record<string, any> = {},
  action: SysInfoAction,
): Record<string, any> {
  switch (action.type) {
    case FETCH_SYSINFO_OK: {
      const { version, data } = action;
      return {
        ...data,
        version,
      };
    }
    default:
      return state;
  }
}

store.injectReducer("sysInfo", reducer);
