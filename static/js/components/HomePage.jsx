import React from "react";
import { useSelector, useDispatch } from "react-redux";

import { Responsive, WidthProvider } from "react-grid-layout";
// eslint-disable-next-line import/no-extraneous-dependencies
import "reactgridlayoutcss/styles.css";
// eslint-disable-next-line import/no-extraneous-dependencies
import "reactresizablecss/styles.css";

import { makeStyles } from "@material-ui/core/styles";

import * as profileActions from "../ducks/profile";

import RecentSources from "./RecentSources";
import GroupList from "./GroupList";
import NewsFeed from "./NewsFeed";
import TopSources from "./TopSources";
import SourceCounts from "./SourceCounts";
import UninitializedDBMessage from "./UninitializedDBMessage";

const ResponsiveGridLayout = WidthProvider(Responsive);

const useStyles = makeStyles(() => ({
  widgetIcon: {
    float: "right",
    color: "gray",
    margin: "0.25rem 0.25rem 0.25rem 0.25rem",
    "&:hover": {
      cursor: "pointer",
    },
  },
  widgetPaperDiv: {
    padding: "1rem",
    height: "100%",
  },
  widgetPaperFillSpace: {
    height: "100%",
  },
}));

const xlgLayout = [
  { i: "sourceCounts", x: 14, y: 0, w: 2, h: 1, isResizable: false },
  { i: "recentSources", x: 0, y: 0, w: 5, h: 3, isResizable: false },
  { i: "newsFeed", x: 10, y: 0, w: 4, h: 3, isResizable: false },
  { i: "topSources", x: 5, y: 0, w: 5, h: 3, isResizable: false },
  { i: "groups", x: 14, y: 1, w: 2, h: 2, isResizable: false },
];

const lgLayout = [
  { i: "sourceCounts", x: 10, y: 0, w: 2, h: 1, isResizable: false },
  { i: "recentSources", x: 0, y: 0, w: 4, h: 3, isResizable: false },
  { i: "newsFeed", x: 7, y: 0, w: 3, h: 3, isResizable: false },
  { i: "topSources", x: 4, y: 3, w: 3, h: 3, isResizable: false },
  { i: "groups", x: 10, y: 1, w: 2, h: 2, isResizable: false },
];

const mdLayout = [
  { i: "sourceCounts", x: 8, y: 0, w: 2, h: 1, isResizable: false },
  { i: "recentSources", x: 0, y: 3, w: 5, h: 3, isResizable: false },
  { i: "newsFeed", x: 0, y: 0, w: 8, h: 3, isResizable: false },
  { i: "topSources", x: 5, y: 3, w: 5, h: 3, isResizable: false },
  { i: "groups", x: 8, y: 1, w: 2, h: 2, isResizable: false },
];

const smLayout = [
  { i: "sourceCounts", x: 4.5, y: 0, w: 1.5, h: 1, isResizable: false },
  { i: "recentSources", x: 0, y: 3, w: 3, h: 3, isResizable: false },
  { i: "newsFeed", x: 0, y: 0, w: 4.5, h: 3, isResizable: false },
  { i: "topSources", x: 3, y: 3, w: 3, h: 3, isResizable: false },
  { i: "groups", x: 4.5, y: 1, w: 1.5, h: 2, isResizable: false },
];

const xsLayout = [
  { i: "sourceCounts", x: 0, y: 0, w: 4, h: 1, isResizable: false },
  { i: "recentSources", x: 0, y: 4, w: 4, h: 3, isResizable: false },
  { i: "newsFeed", x: 0, y: 1, w: 4, h: 3, isResizable: false },
  { i: "topSources", x: 0, y: 7, w: 4, h: 3, isResizable: false },
  { i: "groups", x: 0, y: 10, w: 4, h: 2, isResizable: false },
];

const defaultLayouts = {
  xlg: xlgLayout,
  lg: lgLayout,
  md: mdLayout,
  sm: smLayout,
  xs: xsLayout,
};

const HomePage = () => {
  const classes = useStyles();

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
      margin={[10, 10]}
      onLayoutChange={LayoutChangeHandler}
      draggableHandle=".dragHandle"
    >
      <div key="sourceCounts">
        <SourceCounts classes={classes} />
      </div>
      <div key="recentSources">
        <RecentSources classes={classes} />
      </div>
      <div key="newsFeed">
        <NewsFeed classes={classes} />
      </div>
      <div key="topSources">
        <TopSources classes={classes} />
      </div>
      <div key="groups">
        <GroupList title="My Groups" groups={groups} classes={classes} />
      </div>
    </ResponsiveGridLayout>
  );
};

export default HomePage;
