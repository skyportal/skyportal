import { createStore, applyMiddleware, compose } from 'redux';
import thunk from 'redux-thunk';
import createLogger from 'redux-logger';

import rootReducer from './reducers';


const logger = createLogger({
  collapsed: (getState, action, logEntry) => !logEntry.error
});


export default function configureStore(preloadedState) {
  return createStore(
    rootReducer,
    preloadedState,
    compose(
      applyMiddleware(thunk, logger),
      // Enable the Chrome developer plugin
      // https://github.com/zalmoxisus/redux-devtools-extension
      window.devToolsExtension ? window.devToolsExtension() : f => f,
    )
  );
}
