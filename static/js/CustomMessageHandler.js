import * as Action from './actions';
import MessageHandler from 'baselayer/MessageHandler';

let CustomMessageHandler = (dispatch, getState) => {
  return new MessageHandler(dispatch, message => {
    let {action, payload} = message;

    console.log('WebSocket', action, payload);

    switch (action) {

    case Action.REFRESH_SOURCE:
      let state = getState();
      let loaded_source_id = state.source ? state.source.id : null;

      if (loaded_source_id == payload.source_id) {
        dispatch(Action.fetchSource(loaded_source_id));
      }
      break;

    default:
      console.log('Unknown message received through flow:',
                  message);
    }
  });
};

export default CustomMessageHandler;
