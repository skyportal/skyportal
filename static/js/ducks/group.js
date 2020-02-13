import messageHandler from 'baselayer/MessageHandler';

import * as API from '../API';

export const REFRESH_GROUP = 'skyportal/REFRESH_GROUP';

export const FETCH_GROUP = 'skyportal/FETCH_GROUP';
export const FETCH_GROUP_OK = 'skyportal/FETCH_GROUP_OK';
const FETCH_GROUP_FAIL = 'skyportal/FETCH_GROUP_FAIL';

export function fetchGroup(id) {
  return API.GET(`/api/groups/${id}`, FETCH_GROUP);
}


// Websocket message handler
messageHandler.add((action, payload, dispatch, getState) => {
  const { group } = getState();

  if (action === REFRESH_GROUP) {
    const loaded_group_id = group ? group.id : null;

    if (loaded_group_id === payload.group_id) {
      dispatch(fetchGroup(loaded_group_id));
    }
  }
});


export default function reducer(state={}, action) {
  switch (action.type) {
    case FETCH_GROUP_OK: {
      const { group } = action.data;
      return group;
    }
    case FETCH_GROUP_FAIL: {
      return {};
    }
    default:
      return state;
  }
}
