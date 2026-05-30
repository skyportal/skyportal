import { createStore, combineReducers, applyMiddleware, compose } from "redux";
import type { AnyAction, Middleware, Reducer } from "redux";
import thunk from "redux-thunk";

import { reducer as notificationsReducer } from "baselayer/components/Notifications";

import {
  createStateSyncMiddleware,
  initStateWithPrevTab,
  withReduxStateSync,
} from "redux-state-sync";

import type { AppStore } from "./types/store";

declare global {
  interface Window {
    __REDUX_DEVTOOLS_EXTENSION_COMPOSE__?: typeof compose;
  }
}

const syncConfig = {
  whitelist: [
    // "baselayer/SHOW_NOTIFICATION",
    "baselayer/HIDE_NOTIFICATION",
    "baselayer/HIDE_NOTIFICATION_BY_TAG",
    // "skyportal/FETCH_INSTRUMENTS_OK",
    // TODO: add more _OK actions here, as long as
    // they don't trigger any fetching of data
  ],
};

const logger: Middleware = (store) => (next) => (action) => {
  const prevState = store.getState();
  let errored = false;
  try {
    return next(action);
  } catch (e) {
    errored = true;
    throw e;
  } finally {
    const group = errored ? console.group : console.groupCollapsed;
    group(`action ${(action as AnyAction).type}`);
    console.log("%cprev state", "color: #9E9E9E", prevState);
    console.log("%caction    ", "color: #03A9F4", action);
    console.log("%cnext state", "color: #4CAF50", store.getState());
    console.groupEnd();
  }
};

// Compose function that hooks up the Chrome/FF developer plugin
// https://github.com/zalmoxisus/redux-devtools-extension

const composeWithDevTools =
  window.__REDUX_DEVTOOLS_EXTENSION_COMPOSE__ || compose;

function configureStore(): AppStore {
  const nullReducer: Reducer = (state = null) => state;

  const middlewares = [thunk, logger, createStateSyncMiddleware(syncConfig)];

  const store = createStore(
    nullReducer,
    {},
    composeWithDevTools(applyMiddleware(...middlewares)),
  ) as unknown as AppStore;

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
