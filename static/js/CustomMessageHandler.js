import MessageHandler from 'baselayer/MessageHandler';
import * as sourceActions from './ducks/source';
import * as groupActions from './ducks/group';
import * as groupsActions from './ducks/groups';
import * as profileActions from './ducks/profile';


const CustomMessageHandler = (dispatch, getState) => (
  new MessageHandler(dispatch, (message) => {
    const { action, payload } = message;

    // eslint-disable-next-line no-console
    console.log('WebSocket', action, payload);

    switch (action) {
      case sourceActions.REFRESH_SOURCE: {
        const state = getState();
        const loaded_source_id = state.source ? state.source.id : null;

        if (loaded_source_id === payload.source_id) {
          dispatch(sourceActions.fetchSource(loaded_source_id));
        }
        break;
      }
      case groupActions.REFRESH_GROUP: {
        const state = getState();
        const loaded_group_id = state.group ? state.group.id : null;

        if (loaded_group_id === payload.group_id) {
          dispatch(groupActions.fetchGroup(loaded_group_id));
        }
        break;
      }
      case groupsActions.FETCH_GROUPS: {
        dispatch(groupsActions.fetchGroups());
        break;
      }
      case profileActions.FETCH_USER_PROFILE: {
        dispatch(profileActions.fetchUserProfile());
        break;
      }
      default:
        // eslint-disable-next-line no-console
        console.log('Unknown message received through flow:', message);
    }
  })
);


export default CustomMessageHandler;
