import * as Action from './actions';
import MessageHandler from 'baselayer/MessageHandler';

let CustomMessageHandler = dispatch => {
  return new MessageHandler(dispatch, message => {
    let {action, payload} = message;

    switch (action) {

    default:
      console.log('Unknown message received through flow:',
                  message);
    }
  });
};

export default CustomMessageHandler;
