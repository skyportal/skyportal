import React from "react";
import { useSelector, useDispatch } from "react-redux";

import { Responsive, WidthProvider } from "react-grid-layout";
// eslint-disable-next-line import/no-extraneous-dependencies
import "reactgridlayoutcss/styles.css";
// eslint-disable-next-line import/no-extraneous-dependencies
import "reactresizablecss/styles.css";

import * as profileActions from "../ducks/profile";
import SourceList from "./SourceList";
import GroupList from "./GroupList";
import NewsFeed from "./NewsFeed";
import TopSources from "./TopSources";
import SourceCounts from "./SourceCounts";

import styles from "./HomePage.css";

const ResponsiveGridLayout = WidthProvider(Responsive);

const xlgLayout = [
  { i: "sourceCounts", x: 0, y: 0, w: 2, h: 2, isResizable: false },
  { i: "sourceList", x: 0, y: 2, w: 8, h: 6, minW: 6, isResizable: false },
  { i: "newsFeed", x: 8, y: 0, w: 8, h: 3, isResizable: false },
  { i: "topSources", x: 8, y: 5, w: 8, h: 3, isResizable: false },
  { i: "groups", x: 2, y: 0, w: 2, h: 2, isResizable: true },
];

const lgLayout = [
  { i: "sourceCounts", x: 0, y: 0, w: 2, h: 2, isResizable: false },
  { i: "sourceList", x: 0, y: 2, w: 6, h: 6, minW: 6, isResizable: false },
  { i: "newsFeed", x: 6, y: 0, w: 6, h: 3, isResizable: false },
  { i: "topSources", x: 6, y: 3, w: 6, h: 3, isResizable: false },
  { i: "groups", x: 2, y: 0, w: 2, h: 2, isResizable: true },
];

const mdLayout = [
  { i: "sourceCounts", x: 0, y: 0, w: 1, h: 1, isResizable: false },
  { i: "sourceList", x: 0, y: 2, w: 10, h: 5, isResizable: false },
  { i: "newsFeed", x: 0, y: 4, w: 4, h: 3, isResizable: false },
  { i: "topSources", x: 0, y: 8, w: 10, h: 2, isResizable: false },
  { i: "groups", x: 1, y: 0, w: 1, h: 1, isResizable: false },
];

const smLayout = [
  { i: "sourceCounts", x: 0, y: 0, w: 1, h: 1, isResizable: false },
  { i: "sourceList", x: 0, y: 1, w: 6, h: 6, isResizable: false },
  { i: "newsFeed", x: 0, y: 7, w: 6, h: 3, isResizable: false },
  { i: "topSources", x: 3, y: 10, w: 6, h: 6, isResizable: false },
  { i: "groups", x: 1, y: 0, w: 1, h: 1, isResizable: false },
];

const xsLayout = [
  { i: "sourceCounts", x: 0, y: 0, w: 1, h: 1, isResizable: false },
  { i: "sourceList", x: 0, y: 1, w: 4, h: 6, isResizable: false },
  { i: "newsFeed", x: 0, y: 7, w: 5, h: 3, isResizable: false },
  { i: "topSources", x: 0, y: 10, w: 5, h: 2, isResizable: false },
  { i: "groups", x: 0, y: 1, w: 1, h: 1, isResizable: false },
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

  const preferredLayouts = useSelector(
    (state) => state.profile.preferences.layouts
  );

  const currentLayouts =
    preferredLayouts == null ? defaultLayouts : preferredLayouts;

  const dispatch = useDispatch();

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
      breakpoints={{ xlg: 1400, lg: 1150, md: 996, sm: 768, xs: 480 }}
      cols={{ xlg: 16, lg: 12, md: 10, sm: 6, xs: 4 }}
      margin={[10, 10]}
      onLayoutChange={LayoutChangeHandler}
    >
      <div key="sourceCounts" className={styles.homePageWidgetDiv}>
        <SourceCounts />
      </div>
      <div key="sourceList" className={styles.homePageWidgetDiv}>
        <SourceList />
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
