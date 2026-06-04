import { Responsive, WidthProvider } from "react-grid-layout";
import "reactgridlayoutcss/styles.css";
import "reactresizablecss/styles.css";

import { useTheme } from "@mui/material/styles";
import { makeStyles } from "tss-react/mui";
import IconButton from "@mui/material/IconButton";
import CachedIcon from "@mui/icons-material/Cached";
import Tooltip from "@mui/material/Tooltip";
import convertLength from "convert-css-length";

import { useAppSelector, useAppDispatch } from "../../types/hooks";
import * as profileActions from "../../ducks/profile";

import WeatherWidget from "../widget/WeatherWidget";
import SourceCounts from "../widget/SourceCounts";
import RecentSources from "../widget/RecentSources";
import NewsFeed from "../widget/NewsFeed";
import TopSources from "../widget/TopSources";
import TopSavers from "../widget/TopSavers";
import RecentGcnEvents from "../widget/RecentGcnEvents";
import GroupList from "../group/GroupList";

const ResponsiveGridLayout = WidthProvider(Responsive);

const useStyles = makeStyles()(() => ({
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
    display: "flex",
    flexFlow: "column nowrap",
  },
  widgetPaperFillSpace: {
    height: "100%",
  },
  resetButton: {
    position: "fixed",
    bottom: "1rem",
    right: "1rem",
  },
}));

const defaultLayouts: any = {
  xlg: [
    { i: "WeatherWidget", x: 12, y: 3, w: 4, h: 2, isResizable: true, minW: 2 },
    {
      i: "SourceCounts",
      x: 14,
      y: 0,
      w: 2,
      h: 1,
      isResizable: true,
      minW: 1.5,
    },
    { i: "RecentSources", x: 0, y: 0, w: 5, h: 3, isResizable: true, minW: 2 },
    { i: "NewsFeed", x: 10, y: 0, w: 4, h: 3, isResizable: true, minW: 2 },
    { i: "TopSources", x: 5, y: 0, w: 5, h: 3, isResizable: true, minW: 2 },
    { i: "TopSavers", x: 7, y: 3, w: 5, h: 3, isResizable: true, minW: 3 },
    {
      i: "RecentGcnEvents",
      x: 0,
      y: 3,
      w: 7,
      h: 3,
      isResizable: true,
      minW: 3,
    },
    { i: "GroupList", x: 14, y: 1, w: 2, h: 2, isResizable: true, minW: 1.5 },
  ],
  lg: [
    { i: "WeatherWidget", x: 9, y: 3, w: 3, h: 2, isResizable: true, minW: 2 },
    {
      i: "SourceCounts",
      x: 10,
      y: 0,
      w: 2,
      h: 1,
      isResizable: true,
      minW: 1.5,
    },
    { i: "RecentSources", x: 0, y: 0, w: 4, h: 3, isResizable: true, minW: 2 },
    { i: "NewsFeed", x: 7, y: 0, w: 3, h: 3, isResizable: true, minW: 2 },
    { i: "TopSources", x: 4, y: 0, w: 3, h: 3, isResizable: true, minW: 2 },
    { i: "TopSavers", x: 5, y: 3, w: 4, h: 2, isResizable: true, minW: 3 },
    {
      i: "RecentGcnEvents",
      x: 0,
      y: 3,
      w: 5,
      h: 2,
      isResizable: true,
      minW: 3,
    },
    { i: "GroupList", x: 10, y: 1, w: 2, h: 2, isResizable: true, minW: 1.5 },
  ],
  md: [
    { i: "WeatherWidget", x: 6, y: 6, w: 4, h: 3, isResizable: true, minW: 2 },
    { i: "SourceCounts", x: 8, y: 0, w: 2, h: 1, isResizable: true, minW: 1.5 },
    { i: "RecentSources", x: 0, y: 0, w: 4, h: 3, isResizable: true, minW: 2 },
    { i: "NewsFeed", x: 4, y: 0, w: 4, h: 3, isResizable: true, minW: 2 },
    { i: "TopSources", x: 0, y: 3, w: 4, h: 3, isResizable: true, minW: 2 },
    { i: "TopSavers", x: 0, y: 6, w: 6, h: 3, isResizable: true, minW: 3 },
    {
      i: "RecentGcnEvents",
      x: 4,
      y: 3,
      w: 6,
      h: 3,
      isResizable: true,
      minW: 3,
    },
    { i: "GroupList", x: 8, y: 1, w: 2, h: 2, isResizable: true, minW: 1.5 },
  ],
  sm: [
    { i: "WeatherWidget", x: 0, y: 9, w: 6, h: 1, isResizable: true, minW: 2 },
    {
      i: "SourceCounts",
      x: 4.5,
      y: 0,
      w: 1.5,
      h: 1,
      isResizable: true,
      minW: 1.5,
    },
    { i: "RecentSources", x: 0, y: 3, w: 3, h: 3, isResizable: true, minW: 2 },
    { i: "NewsFeed", x: 0, y: 0, w: 4.5, h: 3, isResizable: true, minW: 2 },
    { i: "TopSources", x: 3, y: 3, w: 3, h: 3, isResizable: true, minW: 2 },
    { i: "TopSavers", x: 0, y: 10, w: 6, h: 3, isResizable: true, minW: 3 },
    {
      i: "RecentGcnEvents",
      x: 0,
      y: 6,
      w: 6,
      h: 3,
      isResizable: true,
      minW: 3,
    },
    {
      i: "GroupList",
      x: 4.5,
      y: 1,
      w: 1.5,
      h: 2,
      isResizable: true,
      minW: 1.5,
    },
  ],
  xs: [
    { i: "WeatherWidget", x: 0, y: 19, w: 5, h: 1, isResizable: true, minW: 2 },
    { i: "SourceCounts", x: 0, y: 0, w: 4, h: 1, isResizable: true, minW: 1.5 },
    { i: "RecentSources", x: 0, y: 4, w: 4, h: 3, isResizable: true, minW: 2 },
    { i: "NewsFeed", x: 0, y: 1, w: 4, h: 3, isResizable: true, minW: 2 },
    { i: "TopSources", x: 0, y: 7, w: 4, h: 3, isResizable: true, minW: 2 },
    { i: "TopSavers", x: 0, y: 14, w: 4, h: 3, isResizable: true, minW: 3 },
    {
      i: "RecentGcnEvents",
      x: 0,
      y: 10,
      w: 4,
      h: 4,
      isResizable: true,
      minW: 3,
    },
    { i: "GroupList", x: 0, y: 17, w: 4, h: 2, isResizable: true, minW: 1.5 },
  ],
};

const HomePage = () => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();

  // Taken from configs
  const rem = "9.375rem";

  const theme = useTheme();
  const rootFont = theme.typography.htmlFontSize;
  const convert = convertLength(rootFont);
  const gridRowHeight = parseFloat(convert(rem, "px"));
  const groups = useAppSelector((state) => (state as any).groups.user);
  const profile = useAppSelector((state) => (state as any).profile);
  const currentLayouts = profile?.preferences?.layouts ?? defaultLayouts;

  const layoutChangeHandler = (_: any, allLayouts: any) => {
    const prefs = { layouts: allLayouts };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  const resetLayouts = () => {
    const prefs = { layouts: defaultLayouts };
    dispatch(profileActions.updateUserPreferences(prefs));
  };

  return (
    profile?.username && (
      <div>
        <ResponsiveGridLayout
          className="layout"
          layouts={currentLayouts}
          breakpoints={{ lg: 1150, md: 996, sm: 650, xlg: 1400, xs: 0 }}
          cols={{ lg: 12, md: 10, sm: 6, xlg: 16, xs: 4 }}
          margin={[10, 10]}
          onLayoutChange={layoutChangeHandler}
          draggableHandle=".dragHandle"
          rowHeight={gridRowHeight}
        >
          <div key="WeatherWidget">
            <WeatherWidget classes={classes} />
          </div>
          <div key="SourceCounts">
            <SourceCounts classes={classes} sinceDaysAgo={7} />
          </div>
          <div key="RecentSources">
            <RecentSources classes={classes} />
          </div>
          <div key="NewsFeed">
            <NewsFeed classes={classes} />
          </div>
          <div key="TopSources">
            <TopSources classes={classes} />
          </div>
          <div key="TopSavers">
            <TopSavers classes={classes} />
          </div>
          <div key="RecentGcnEvents">
            <RecentGcnEvents classes={classes} />
          </div>
          <div key="GroupList">
            <GroupList groups={groups} classes={classes} title={"My Groups"} />
          </div>
        </ResponsiveGridLayout>
        <div className={classes.resetButton}>
          <Tooltip title="Reset page layout" placement="left">
            <IconButton onClick={resetLayouts}>
              <CachedIcon />
            </IconButton>
          </Tooltip>
        </div>
      </div>
    )
  );
};

export default HomePage;
