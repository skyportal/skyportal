// Baselayer components
import WebSocket from 'baselayer/components/WebSocket';
import { Notifications } from 'baselayer/components/Notifications';

// React and Redux
import React from 'react';
import PropTypes from 'prop-types';
import { Provider } from 'react-redux';
import ReactDOM from 'react-dom';

import { BrowserRouter, Link, Switch } from 'react-router-dom';
import PropsRoute from '../route';

// Main style
import styles from './Main.css';

// Store
import configureStore from '../store';

// Actions
import hydrate from '../actions';
import * as rotateLogoActions from '../ducks/logo';

// Message Handler
import CustomMessageHandler from '../CustomMessageHandler';

// Local
import NoMatchingRoute from './NoMatchingRoute';
import Responsive from './Responsive';

import Source from './Source';
import Group from './Group';
import SourceList from './SourceList';
import Groups from './Groups';
import Profile from './Profile';
import ProfileDropdown from './ProfileDropdown';
import Logo from './Logo';
import Footer from './Footer';
import UserInfo from './UserInfo';


const store = configureStore({});
const messageHandler = (
  new CustomMessageHandler(store.dispatch, store.getState)
);

class MainContent extends React.Component {
  async componentDidMount() {
    await store.dispatch(hydrate());
    store.dispatch(rotateLogoActions.rotateLogo());
  }

  render() {
    const { root } = this.props;
    return (
      <div className={styles.main}>

        <div className={styles.topBanner}>
          <div className={styles.topBannerContent}>
            <Logo className={styles.logo} />
            <Link className={styles.title} to="/">
              SkyPortal ∝
            </Link>
            <div className={styles.websocket}>
              <WebSocket
                url={`${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${root}websocket`}
                auth_url={`${window.location.protocol}//${root}baselayer/socket_auth_token`}
                messageHandler={messageHandler}
                dispatch={store.dispatch}
              />
            </div>
            <Responsive desktopElement={ProfileDropdown} />
          </div>
        </div>

        <Responsive mobileElement={ProfileDropdown} />

        <div className={styles.content}>

          <Notifications />

          <Switch>
            <PropsRoute exact path="/" component={SourceList} />
            See https://stackoverflow.com/a/35604855 for syntax
            <PropsRoute path="/source/:id" component={Source} />
            <PropsRoute exact path="/groups/" component={Groups} />
            <PropsRoute path="/group/:id" component={Group} />
            <PropsRoute path="/profile" component={Profile} />
            <PropsRoute path="/user/:id" component={UserInfo} />
            <PropsRoute component={NoMatchingRoute} />
          </Switch>

        </div>

        <Footer />

      </div>
    );
  }
}

MainContent.propTypes = {
  root: PropTypes.string.isRequired
};

ReactDOM.render(
  <Provider store={store}>
    <BrowserRouter basename="/">
      <MainContent root={`${window.location.host}/`} />
    </BrowserRouter>
  </Provider>,
  document.getElementById('content')
);
