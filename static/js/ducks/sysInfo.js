import * as API from '../API';


export const FETCH_SYSINFO = 'skyportal/FETCH_SYSINFO';
export const FETCH_SYSINFO_OK = 'skyportal/FETCH_SYSINFO_OK';

export function fetchSystemInfo() {
  return API.GET('/api/sysinfo', FETCH_SYSINFO);
}

export default function reducer(state={}, action) {
  switch (action.type) {
    case FETCH_SYSINFO_OK:
      return action.data;
    default:
      return state;
  }
}
