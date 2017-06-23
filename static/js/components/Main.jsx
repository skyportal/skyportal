import React from 'react';
import { connect, Provider } from 'react-redux';
import ReactDOM from 'react-dom';

import WebSocket from 'baselayer/components/WebSocket';
import { Notifications, reducer as notificationReducer, showNotification }
           from 'baselayer/components/Notifications';
import MessageHandler from 'baselayer/MessageHandler';

import SourceList from './SourceList';

// Construct the application state store
import { createStore, combineReducers, applyMiddleware, compose } from 'redux';
import thunk from 'redux-thunk';
import createLogger from 'redux-logger';


const logger = createLogger({
  collapsed: (getState, action, logEntry) => !logEntry.error
});

function sourceReducer(state=[], action) {
    switch (action.type) {
        default:
            return state;
    }
}

const store = createStore(
    combineReducers({
        sources: sourceReducer,
        notifications: notificationReducer,
    }),
    compose(
      applyMiddleware(thunk, logger),
      // Enable the Chrome developer plugin
      // https://github.com/zalmoxisus/redux-devtools-extension
      window.devToolsExtension ? window.devToolsExtension() : f => f,
    )
);
// End store construction

let fetchSources = () => (
  async (dispatch) => {
    try {
      let response = await fetch('/sources', {credentials: 'same-origin'});
      if (response.status != 200) {
        throw `Could not fetch data from server (${response.status})`;
      }
      let json = await response.json();
      dispatch(receiveSources());
    }
    catch (err) {
      dispatch(showNotification(err, 'error'));
    }
  }
)

let receiveSources = () => (
  {'type': 'skyportal/RECEIVE_SOURCES'}
)

let hydrate = () => (
  (dispatch) => {
    dispatch(fetchSources());
  }
)

const messageHandler = (new MessageHandler(store.dispatch));

class MainContent extends React.Component {
  componentDidMount() {
    store.dispatch(hydrate());
  }
  render() {
    return (
      <div>
        <div style={{float: "right"}}>
          <b>WebSocket connection: </b>
          <WebSocket
              url={`ws://${this.props.root}websocket`}
              auth_url={`${location.protocol}//${this.props.root}socket_auth_token`}
              messageHandler={messageHandler}
              dispatch={store.dispatch}
          />
        </div>

        <Notifications style={{}} />

        <h1>SkyPortal</h1>

        <SourceList/>

      </div>
    );
  }
}
//const mapStateToProps = function (state) (
//);
//const mapDispatchToProps = dispatch => (
//);
//
//MainContent = connect(mapStateToProps, mapDispatchToProps)(MainContent);

ReactDOM.render(
  <Provider store={store}>
    <MainContent root={location.host + location.pathname} />
  </Provider>,
  document.getElementById('content')
);
