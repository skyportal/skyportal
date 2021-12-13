// Baselayer components
import { Notifications } from "baselayer/components/Notifications";

// React and Redux
import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { Provider, useSelector } from "react-redux";
import ReactDOM from "react-dom";

import { BrowserRouter, Switch, useLocation } from "react-router-dom";

import { MuiPickersUtilsProvider } from "@material-ui/pickers";
import { makeStyles } from "@material-ui/core/styles";
import { isMobile } from "react-device-detect";

import DayJSUtils from "@date-io/dayjs";
import clsx from "clsx";

// WebSocket
import WebSocket from "baselayer/components/WebSocket";
import messageHandler from "baselayer/MessageHandler";

// Store
import store from "../store";

// Actions
import hydrate from "../actions";
import * as rotateLogoActions from "../ducks/logo";

import PropsRoute from "./Route";
import NoMatchingRoute from "./NoMatchingRoute";
import Responsive from "./Responsive";

import HomePage from "./HomePage";
import Source from "./Source";
import FavoritesPage from "./FavoritesPage";
import GcnEventPage from "./GcnEventPage";
import Groups from "./Groups";
import Group from "./Group";
import Profile from "./Profile";
import CandidateList from "./CandidateList";
import SourceList from "./SourceList";
import UserInfo from "./UserInfo";
import UploadPhotometry from "./UploadPhotometry";
import About from "./About";
import RunSummary from "./RunSummary";
import ManageDataForm from "./ManageDataForm";
import Filter from "./Filter";
import ObservingRunPage from "./ObservingRunPage";
import GroupSources from "./GroupSources";
import UserManagement from "./UserManagement";
import UploadSpectrum from "./UploadSpectrum";
import Observability from "./Observability";
import FindingChart from "./FindingChart";
import Periodogram from "./Periodogram";
import DBStats from "./DBStats";
import GcnEvents from "./GcnEvents";
import DashboardPage from "./DashboardPage";


import Theme from "./Theme";
import ProfileDropdown from "./ProfileDropdown";
import SidebarAndHeader from "./SidebarAndHeader";
import ErrorBoundary from "./ErrorBoundary";

messageHandler.init(store.dispatch, store.getState);


const useStyles = makeStyles((theme) => ({
  content: {
    flexGrow: 1,
    padding: theme.spacing(2),
    transition: theme.transitions.create("margin", {
      easing: theme.transitions.easing.sharp,
      duration: theme.transitions.duration.leavingScreen,
    }),
    marginTop: "6em", // top bar height
    marginLeft: isMobile ? "0" : "190px",
    "& a": {
      textDecoration: "none",
      color: "gray",
      fontWeight: "bold",
    },
  },
  contentShift: {
    transition: theme.transitions.create("margin", {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen,
    }),
    marginLeft: 0,
  },
  websocket: {
    display: "none",
  }
}));

const MainContent = ({ root }) => {
  const { open } = useSelector((state) => state.sidebar);

  const classes = useStyles();

  useEffect(() => {
    store.dispatch(hydrate());
    store.dispatch(rotateLogoActions.rotateLogo());
  }, []);

  const location = useLocation();
  useEffect(() => {
    document.title = "SkyPortal";
  }, [location]);

  return (
    <Theme >

      <div className={classes.websocket}>
        <WebSocket
          url={`${window.location.protocol === "https:" ? "wss" :
          "ws"}://${root}websocket`}
          auth_url={`${window.location.protocol}//${root}baselayer/socket_auth_token`}
          messageHandler={messageHandler}
          dispatch={store.dispatch}
        />
      </div>

      <MuiPickersUtilsProvider utils={DayJSUtils}>

        <SidebarAndHeader open={open} />

        <div
          role="main"
          className={clsx(classes.content, {
            [classes.contentShift]: !open,
          })}
        >

          <Notifications />

          <Switch>
            <PropsRoute exact path="/" component={HomePage} />
            <PropsRoute exact path="/source/:id" component={Source} />
            <PropsRoute exact path="/favorites" component={FavoritesPage} />
            <PropsRoute exact path="/gcn_events/:dateobs" component={GcnEventPage} />
            <PropsRoute exact path="/groups" component={Groups} />
            <PropsRoute exact path="/group/:id" component={Group} />
            <PropsRoute exact path="/profile" component={Profile} />
            <PropsRoute exact path="/candidates" component={CandidateList} />
            <PropsRoute exact path="/sources" component={SourceList} />
            <PropsRoute exact path="/user/:id" component={UserInfo} />
            <PropsRoute exact path="/upload_photometry/:id" component={UploadPhotometry} />
            <PropsRoute exact path="/about" component={About} />
            <PropsRoute exact path="/run/:id" component={RunSummary} />
            <PropsRoute exact path="/manage_data/:id" component={ManageDataForm} />
            <PropsRoute exact path="/filter/:fid" component={Filter} />
            <PropsRoute exact path="/runs" component={ObservingRunPage} />
            <PropsRoute exact path="/group_sources/:id" component={GroupSources} />
            <PropsRoute exact path="/user_management" component={UserManagement} />
            <PropsRoute exact path="/upload_spectrum/:id" component={UploadSpectrum} />
            <PropsRoute exact path="/observability/:id" component={Observability} />
            <PropsRoute exact path="/source/:id/finder" component={FindingChart} />
            <PropsRoute exact path="/source/:id/periodogram" component={Periodogram} />
            <PropsRoute exact path="/db_stats" component={DBStats} />
            <PropsRoute exact path="/gcn_events" component={GcnEvents} />
            <PropsRoute exact path="/dashboard_grandma" component={DashboardPage} />

            <PropsRoute component={NoMatchingRoute} />

          </Switch>

        </div>

      </MuiPickersUtilsProvider>
    </Theme>
  );
};

MainContent.propTypes = {
  root: PropTypes.string.isRequired
};

ReactDOM.render(
  <Provider store={store}>
    <ErrorBoundary key={location.pathname}>
      <BrowserRouter basename="/">
        <MainContent root={`${window.location.host}/`} />
      </BrowserRouter>
    </ErrorBoundary>
  </Provider>,
  document.getElementById("content")
);
