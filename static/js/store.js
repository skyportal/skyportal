import { createStore, combineReducers, applyMiddleware, compose } from "redux";
import thunk from "redux-thunk";
import { createLogger } from "redux-logger";

import { reducer as notificationsReducer } from "baselayer/components/Notifications";

import {
  createStateSyncMiddleware,
  initStateWithPrevTab,
  withReduxStateSync,
} from "redux-state-sync";

const syncConfig = {
  whitelist: [
    "baselayer/SHOW_NOTIFICATION",
    "baselayer/HIDE_NOTIFICATION",
    "baselayer/HIDE_NOTIFICATION_BY_TAG",
    "skyportal/FETCH_INSTRUMENTS_OK",
    // TODO: add more _OK actions here, as long as
    // they don't trigger any fetching of data
  ],
};

const logger = createLogger({
  collapsed: (getState, action, logEntry) => !logEntry.error,
});

// Compose function that hooks up the Chrome/FF developer plugin
// https://github.com/zalmoxisus/redux-devtools-extension

// eslint-disable-next-line no-underscore-dangle
const composeWithDevTools =
  window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose;

function configureStore() {
  const nullReducer = (state) => state;

  const middlewares = [thunk, logger, createStateSyncMiddleware(syncConfig)];

  const store = createStore(
    nullReducer,
    {},
    composeWithDevTools(applyMiddleware(...middlewares))
  );

  initStateWithPrevTab(store);

  // Track reducers injected by components
  store.reducers = {};

  store.injectReducer = (key, reducer) => {
    store.reducers[key] = reducer;
    store.replaceReducer(withReduxStateSync(combineReducers(store.reducers)));
  };

  return store;
}

const store = configureStore();

// Add the notifications reducer from baselayer
store.injectReducer("notifications", notificationsReducer);

export default store;
