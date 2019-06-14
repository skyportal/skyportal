import MessageHandler from 'baselayer/MessageHandler';
import * as Action from './actions';


const CustomMessageHandler = (dispatch, getState) => (
  new MessageHandler(dispatch, (message) => {
    const { action, payload } = message;

    // eslint-disable-next-line no-console
    console.log('WebSocket', action, payload);

    switch (action) {
      case Action.REFRESH_SOURCE: {
        const state = getState();
        const loaded_source_id = state.source ? state.source.id : null;

        if (loaded_source_id === payload.source_id) {
          dispatch(Action.fetchSource(loaded_source_id));
        }
        break;
      }
      case Action.REFRESH_GROUP: {
        const state = getState();
        const loaded_group_id = state.group ? state.group.id : null;

        if (loaded_group_id === payload.group_id) {
          dispatch(Action.fetchGroup(loaded_group_id));
        }
        break;
      }
      case Action.FETCH_GROUPS: {
        dispatch(Action.fetchGroups());
        break;
      }
      case Action.FETCH_USER_PROFILE: {
        dispatch(Action.fetchUserProfile());
        break;
      }
      case Action.FETCH_SOURCES: {
        // Check if user is on front page, and if so, re-submit current search
        if (window.location.href.endsWith(`${window.location.host}/`) ||
            window.location.href.endsWith(window.location.host) ||
            window.location.href.includes(`${window.location.host}/?`)) {
          document.getElementById("sourceFilterFormSubmitButton").click();
        } else {
          dispatch(Action.fetchSources());
        }
        break;
      }
      default:
        // eslint-disable-next-line no-console
        console.log('Unknown message received through flow:', message);
    }
  })
);


export default CustomMessageHandler;
