import * as API from '../API';


export const FETCH_SOURCE_TABLE_STATUS = 'skyportal/FETCH_SOURCE_TABLE_STATUS';
export const FETCH_SOURCE_TABLE_STATUS_OK = 'skyportal/FETCH_SOURCE_TABLE_STATUS_OK';

export function fetchSourceTableStatus() {
  return API.GET('/api/internal/source_table_empty', FETCH_SOURCE_TABLE_STATUS);
}

export default function reducer(state={}, action) {
  switch (action.type) {
    case FETCH_SOURCE_TABLE_STATUS_OK:
      return action.data;
    default:
      return state;
  }
}
