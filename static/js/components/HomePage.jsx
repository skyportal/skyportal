import React from "react";
import { useSelector, useDispatch } from "react-redux";

import { Responsive, WidthProvider } from "react-grid-layout";
// eslint-disable-next-line import/no-extraneous-dependencies
import "reactgridlayoutcss/styles.css";
// eslint-disable-next-line import/no-extraneous-dependencies
import "reactresizablecss/styles.css";

import * as profileActions from "../ducks/profile";

import RecentSources from "./RecentSources";
import GroupList from "./GroupList";
import NewsFeed from "./NewsFeed";
import TopSources from "./TopSources";
import UninitializedDBMessage from "./UninitializedDBMessage";
import styles from "./HomePage.css";

const ResponsiveGridLayout = WidthProvider(Responsive);

const xlgLayout = [
  { i: "recentSources", x: 0, y: 0, w: 5, h: 3, isResizable: false },
  { i: "newsFeed", x: 10, y: 0, w: 4, h: 3, isResizable: false },
  { i: "topSources", x: 5, y: 0, w: 5, h: 3, isResizable: false },
  { i: "groups", x: 14, y: 0, w: 2, h: 2, isResizable: false },
];

const lgLayout = [
  { i: "recentSources", x: 0, y: 0, w: 4, h: 3, isResizable: false },
  { i: "newsFeed", x: 8, y: 0, w: 4, h: 3, isResizable: false },
  { i: "topSources", x: 4, y: 0, w: 4, h: 3, isResizable: false },
  { i: "groups", x: 10, y: 3, w: 2, h: 2, isResizable: false },
];

const mdLayout = [
  { i: "recentSources", x: 0, y: 0, w: 4, h: 3, isResizable: false },
  { i: "newsFeed", x: 4, y: 0, w: 4, h: 3, isResizable: false },
  { i: "topSources", x: 0, y: 4, w: 4, h: 3, isResizable: false },
  { i: "groups", x: 8, y: 0, w: 2, h: 2, isResizable: false },
];

const smLayout = [
  { i: "recentSources", x: 0, y: 3, w: 3, h: 4, isResizable: false },
  { i: "newsFeed", x: 0, y: 0, w: 4, h: 3, isResizable: false },
  { i: "topSources", x: 3, y: 3, w: 3, h: 4, isResizable: false },
  { i: "groups", x: 4, y: 0, w: 2, h: 2, isResizable: false },
];

const xsLayout = [
  { i: "recentSources", x: 0, y: 3, w: 4, h: 3, isResizable: false },
  { i: "newsFeed", x: 0, y: 0, w: 4, h: 3, isResizable: false },
  { i: "topSources", x: 0, y: 7, w: 4, h: 3, isResizable: false },
  { i: "groups", x: 0, y: 10, w: 2, h: 2, isResizable: false },
];

const defaultLayouts = {
  xlg: xlgLayout,
  lg: lgLayout,
  md: mdLayout,
  sm: smLayout,
  xs: xsLayout,
};

const HomePage = () => {
  const groups = useSelector((state) => state.groups.user);

  const sourceTableEmpty = useSelector(
    (state) => state.dbInfo.source_table_empty
  );

  const preferredLayouts = useSelector(
    (state) => state.profile.preferences.layouts
  );

  const currentLayouts =
    preferredLayouts == null ? defaultLayouts : preferredLayouts;

  const dispatch = useDispatch();

  if (sourceTableEmpty) {
    return <UninitializedDBMessage />;
  }

  const LayoutChangeHandler = (currentLayout, allLayouts) => {
    const prefs = {
      layouts: allLayouts,
    };

    dispatch(profileActions.updateUserPreferences(prefs));
  };

  return (
    <ResponsiveGridLayout
      className="layout"
      layouts={currentLayouts}
      breakpoints={{ xlg: 1400, lg: 1150, md: 996, sm: 650, xs: 0 }}
      cols={{ xlg: 16, lg: 12, md: 10, sm: 6, xs: 4 }}
      onLayoutChange={LayoutChangeHandler}
    >
      <div key="recentSources" className={styles.homePageWidgetDiv}>
        <RecentSources />
      </div>
      <div key="newsFeed" className={styles.homePageWidgetDiv}>
        <NewsFeed />
      </div>
      <div key="topSources" className={styles.homePageWidgetDiv}>
        <TopSources />
      </div>
      <div key="groups" className={styles.homePageWidgetDiv}>
        <GroupList title="My Groups" groups={groups} />
      </div>
    </ResponsiveGridLayout>
  );
};

export default HomePage;
