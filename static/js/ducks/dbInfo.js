import * as API from '../API';


export const FETCH_DB_INFO = 'skyportal/FETCH_DB_INFO';
export const FETCH_DB_INFO_OK = 'skyportal/FETCH_DB_INFO_OK';

export function fetchDBInfo() {
  return API.GET('/api/internal/dbinfo', FETCH_DB_INFO);
}

export default function reducer(state={}, action) {
  switch (action.type) {
    case FETCH_DB_INFO_OK:
      return action.data;
    default:
      return state;
  }
}
