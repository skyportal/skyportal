import { createStore, combineReducers, applyMiddleware, compose } from 'redux';
import thunk from 'redux-thunk';
import { createLogger } from 'redux-logger';

import { reducer as notificationsReducer } from 'baselayer/components/Notifications';

const logger = createLogger({
  collapsed: (getState, action, logEntry) => !logEntry.error
});

// Compose function that hooks up the Chrome/FF developer plugin
// https://github.com/zalmoxisus/redux-devtools-extension

// eslint-disable-next-line no-underscore-dangle
const composeWithDevTools = (window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ ||
                             compose);

function configureStore() {
  const nullReducer = (state) => state;

  const store = createStore(
    nullReducer,
    {},
    composeWithDevTools(
      applyMiddleware(thunk, logger)
    )
  );

  // Track reducers injected by components
  store.reducers = {};

  store.injectReducer = (key, reducer) => {
    store.reducers[key] = reducer;
    store.replaceReducer(combineReducers(store.reducers));
  };

  return store;
}

const store = configureStore();

// Add the notifications reducer from baselayer
store.injectReducer('notifications', notificationsReducer);

export default store;
