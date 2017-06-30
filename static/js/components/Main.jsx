// React and Redux
import React from 'react';
import { Provider } from 'react-redux';
import ReactDOM from 'react-dom';

import { BrowserRouter, Link } from 'react-router-dom';
import { Switch } from 'react-router';
import PropsRoute from '../route';

// Baselayer components
import WebSocket from 'baselayer/components/WebSocket';
import { Notifications } from 'baselayer/components/Notifications';
import MessageHandler from 'baselayer/MessageHandler';

// Main style
import styles from './Main.css';

// Store
import configureStore from '../store';
const store = configureStore({});

// Local
import CachedSource from '../containers/CachedSource';
import SourceListContainer from '../containers/SourceListContainer';
import NoMatchingRoute from './NoMatchingRoute';
import { hydrate } from '../actions';

const messageHandler = (new MessageHandler(store.dispatch));

class MainContent extends React.Component {
  componentDidMount() {
    store.dispatch(hydrate());
  }
  render() {
    return (
      <div className={styles.main}>
        <div className={styles.websocket}>
          <WebSocket
              url={`ws://${this.props.root}websocket`}
              auth_url={`${location.protocol}//${this.props.root}socket_auth_token`}
              messageHandler={messageHandler}
              dispatch={store.dispatch}
          />
        </div>

        <div className={styles.topBanner}>
          <img className={styles.logo} src="/static/images/skyportal_logo_dark.png"/>
          <Link className={styles.title} to="/">SkyPortal ∝</Link>
        </div>

        <div className={styles.content}>

          <Notifications/>

          <Switch>
            <PropsRoute exact path="/" component={SourceListContainer}/>
            {'See https://stackoverflow.com/a/35604855 for syntax'}
            <PropsRoute path="/source/:id" component={CachedSource}/>
            <PropsRoute component={NoMatchingRoute}/>
          </Switch>

        </div>

        <div className={styles.footer}>
          This is a first proof of concept. Please file issues at&nbsp;
          <a href="https://github.com/skyportal/skyportal">
            https://github.com/skyportal/skyportal
          </a>.
        </div>

      </div>
    );
  }
}

ReactDOM.render(
  <Provider store={store}>
    <BrowserRouter basename="/">
      <MainContent root={location.host + '/'} />
    </BrowserRouter>
  </Provider>,
  document.getElementById('content')
);
