import * as Action from './actions';
import MessageHandler from 'baselayer/MessageHandler';

let CustomMessageHandler = dispatch => {
  return new MessageHandler(dispatch, message => {
    let {action, payload} = message;

    switch (action) {

    case Action.FETCH_COMMENTS:
      let {source_id} = payload;
      dispatch(Action.fetchComments(source_id));
      break;
    default:
      console.log('Unknown message received through flow:',
                  message);
    }
  });
};

export default CustomMessageHandler;
