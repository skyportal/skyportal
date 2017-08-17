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
      default:
        // eslint-disable-next-line no-console
        console.log('Unknown message received through flow:', message);
    }
  })
);


export default CustomMessageHandler;
