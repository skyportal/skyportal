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
import styles from "./HomePage.css";

const ResponsiveGridLayout = WidthProvider(Responsive);

const xlgLayout = [
  { i: "sourceList", x: 0, y: 0, w: 9, h: 6, minW: 9, isResizable: false },
  { i: "newsFeed", x: 9, y: 0, w: 7, h: 3, isResizable: false },
  { i: "topSources", x: 9, y: 0, w: 4, h: 2, isResizable: false },
  { i: "groups", x: 13, y: 0, w: 2, h: 2, isResizable: false },
];

const lgLayout = [
  { i: "sourceList", x: 0, y: 0, w: 7, h: 6, isResizable: false },
  { i: "newsFeed", x: 7, y: 0, w: 5, h: 3, isResizable: false },
  { i: "topSources", x: 7, y: 0, w: 3, h: 2, isResizable: false },
  { i: "groups", x: 10, y: 0, w: 2, h: 2, isResizable: false },
];

const mdLayout = [
  { i: "sourceList", x: 0, y: 0, w: 10, h: 6, isResizable: false },
  { i: "newsFeed", x: 0, y: 6, w: 5, h: 3, isResizable: false },
  { i: "topSources", x: 5, y: 6, w: 3, h: 2, isResizable: false },
  { i: "groups", x: 8, y: 6, w: 2, h: 2, isResizable: false },
];

const smLayout = [
  { i: "sourceList", x: 0, y: 0, w: 6, h: 6, isResizable: false },
  { i: "newsFeed", x: 0, y: 6, w: 3, h: 3, isResizable: false },
  { i: "topSources", x: 3, y: 6, w: 2, h: 2, isResizable: false },
  { i: "groups", x: 5, y: 6, w: 1, h: 2, isResizable: false },
];

const xsLayout = [
  { i: "sourceList", x: 0, y: 0, w: 4, h: 6, isResizable: false },
  { i: "newsFeed", x: 0, y: 6, w: 4, h: 3, isResizable: false },
  { i: "topSources", x: 0, y: 9, w: 2, h: 2, isResizable: false },
  { i: "groups", x: 2, y: 9, w: 2, h: 2, isResizable: false },
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
      margin={[15, 15]}
      onLayoutChange={LayoutChangeHandler}
    >
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
