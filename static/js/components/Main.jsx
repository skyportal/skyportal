import React from 'react';
import PropTypes from 'prop-types';
import { Provider } from 'react-redux';
import { render } from 'react-dom';
import { BrowserRouter, Link, Switch } from 'react-router-dom';
import styled from 'styled-components';
// Baselayer components
import WebSocket from 'baselayer/components/WebSocket';
import { Notifications } from 'baselayer/components/Notifications';
// Message Handler
import messageHandler from 'baselayer/MessageHandler';
// Store
import store from '../store';
// Actions
import hydrate from '../actions';
import * as rotateLogoActions from '../ducks/logo';
import PropsRoute from '../route';
import {
  NoMatchingRoute,
  Responsive,
  HomePage,
  Source,
  Groups,
  Group,
  Profile,
  SourceList,
  UserInfo,
  Theme,
  ProfileDropdown,
  Logo,
  Footer,
} from '../components';

messageHandler.init(store.dispatch, store.getState);

const Main = styled.div`
  font-family: 'Roboto', sans-serif;
  position: absolute;
  width: 100%;
  top: 0;
  left: 0;
  min-height: 100%;
  padding-bottom: 5em;
`;

const TopBanner = styled.div`
  position: relative;
  display: inline-block;
  top: 0;
  margin: 0;
  background: #38B0DE;
  border-bottom: 0.25em solid lightgray;
  z-index: 10;
  width: 100%;
  height: 6em;
`;

const TopBannerContent = styled.div`
  position: relative;
  top: 50%;
  transform: translate(0%, -50%);
  padding-left: 1em;
  padding-right: 1em;
`;

const Title = styled(Link)`
  text-decoration: none;
  color: white;
  padding-left: 0.4em;
  font-size: 200%;
  font-weight: bold;
  vertical-align: middle;
`;

const WebSocketContainer = styled.div`
  display: none;
`;

const Content = styled.div`
  padding: 1em;
  height: auto;
  padding-bottom: 6em; /* same as footer height */
  & a {
    text-decoration: none;
    color: gray;
    font-weight: bold;
  }
`;


class MainContent extends React.Component {
  async componentDidMount() {
    await store.dispatch(hydrate());
    store.dispatch(rotateLogoActions.rotateLogo());
  }

  render() {
    const { root } = this.props;
    return (
      <Theme>
        <Main>
          <TopBanner>
            <TopBannerContent>
              <Logo />
              <Title to="/">SkyPortal ∝</Title>
              <WebSocketContainer>
                <WebSocket
                  url={`${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${root}websocket`}
                  auth_url={`${window.location.protocol}//${root}baselayer/socket_auth_token`}
                  messageHandler={messageHandler}
                  dispatch={store.dispatch}
                />
              </WebSocketContainer>
              <Responsive desktopElement={ProfileDropdown} />
            </TopBannerContent>
          </TopBanner>

          <Responsive mobileElement={ProfileDropdown} />

          <Content>
            <Notifications />
            <Switch>
              <PropsRoute exact path="/" component={HomePage} />
              <PropsRoute exact path="/source/:id" component={Source} />
              <PropsRoute exact path="/groups" component={Groups} />
              <PropsRoute exact path="/group/:id" component={Group} />
              <PropsRoute exact path="/profile" component={Profile} />
              <PropsRoute exact path="/sources" component={SourceList} />
              <PropsRoute exact path="/user/:id" component={UserInfo} />
              <PropsRoute component={NoMatchingRoute} />
            </Switch>
          </Content>
          <Footer />
        </Main>
      </Theme>
    );
  }
}

MainContent.propTypes = {
  root: PropTypes.string.isRequired
};

render(
  <Provider store={store}>
    <BrowserRouter basename="/">
      <MainContent root={`${window.location.host}/`} />
    </BrowserRouter>
  </Provider>,
  document.getElementById('content')
);
