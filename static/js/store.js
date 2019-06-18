import { createStore, applyMiddleware, compose } from 'redux';
import thunk from 'redux-thunk';
import { createLogger } from 'redux-logger';

import rootReducer from './reducers';


const logger = createLogger({
  collapsed: (getState, action, logEntry) => !logEntry.error
});


// Compose function that hooks up the Chrome/FF developer plugin
// https://github.com/zalmoxisus/redux-devtools-extension

// eslint-disable-next-line no-underscore-dangle
const composeWithDevTools = (window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ ||
                             compose);

export default function configureStore(preloadedState) {
  return createStore(
    rootReducer,
    preloadedState,
    composeWithDevTools(
      applyMiddleware(thunk, logger)
    )
  );
}
