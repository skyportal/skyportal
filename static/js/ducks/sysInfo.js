import * as API from '../API';
import store from '../store';


export const FETCH_SYSINFO = 'skyportal/FETCH_SYSINFO';
export const FETCH_SYSINFO_OK = 'skyportal/FETCH_SYSINFO_OK';


export function fetchSystemInfo() {
  return API.GET('/api/sysinfo', FETCH_SYSINFO);
}


function reducer(state={}, action) {
  switch (action.type) {
    case FETCH_SYSINFO_OK: {
      const { version, data } = action;
      return {
        ...data,
        version
      };
    }
    default:
      return state;
  }
}

store.injectReducer('sysInfo', reducer);
