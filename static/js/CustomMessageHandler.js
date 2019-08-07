import MessageHandler from 'baselayer/MessageHandler';
import * as Action from './actions';
import * as sourceActions from './ducks/source';
import * as fetchGroupActions from './ducks/fetchGroup';
import * as groupsActions from './ducks/groups';
import * as userProfileActions from './ducks/userProfile';
import * as fetchSources from './ducks/fetchSources';


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
      case fetchGroupActions.REFRESH_GROUP: {
        const state = getState();
        const loaded_group_id = state.group ? state.group.id : null;

        if (loaded_group_id === payload.group_id) {
          dispatch(fetchGroupActions.fetchGroup(loaded_group_id));
        }
        break;
      }
      case groupsActions.FETCH_GROUPS: {
        dispatch(groupsActions.fetchGroups());
        break;
      }
      case Action.FETCH_USER_PROFILE: {
        dispatch(userProfileActions.fetchUserProfile());
        break;
      }
      default:
        // eslint-disable-next-line no-console
        console.log('Unknown message received through flow:', message);
    }
  })
);


export default CustomMessageHandler;
