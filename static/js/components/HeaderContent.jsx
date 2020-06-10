import React from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";

import WebSocket from "baselayer/components/WebSocket";
import messageHandler from "baselayer/MessageHandler";

import store from "../store";

import Responsive from "./Responsive";
import ProfileDropdown from "./ProfileDropdown";
import Logo from "./Logo";

import styles from "./Main.css";


messageHandler.init(store.dispatch, store.getState);


const HeaderContent = ({ root }) => (
  <div className={styles.topBannerContent}>
    <div style={{ display: "inline-block", float: "left" }}>
      <Logo className={styles.logo} />
      <Link className={styles.title} to="/">
        SkyPortal ∝
      </Link>
      <div className={styles.websocket}>
        <WebSocket
          url={`${window.location.protocol === "https:" ? "wss" : "ws"}://${root}websocket`}
          auth_url={`${window.location.protocol}//${root}baselayer/socket_auth_token`}
          messageHandler={messageHandler}
          dispatch={store.dispatch}
        />
      </div>
    </div>
    <div style={{ position: "fixed", right: "1em" }}>
      <Responsive desktopElement={ProfileDropdown} />
    </div>
  </div>
);

HeaderContent.propTypes = {
  root: PropTypes.string.isRequired
};

export default HeaderContent;
