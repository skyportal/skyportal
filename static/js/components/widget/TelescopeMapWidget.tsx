import { lazy, Suspense, useState } from "react";
import { makeStyles } from "tss-react/mui";
import Paper from "@mui/material/Paper";
import CircularProgress from "@mui/material/CircularProgress";
import { Tooltip, IconButton } from "@mui/material";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
import ReplayIcon from "@mui/icons-material/Replay";

import { useAppSelector } from "../../types/hooks";

const TelescopeMap = lazy(() => import("../telescope/TelescopeMap"));

const useStyles = makeStyles()((_theme) => ({
  mapContainer: {
    position: "relative",
    width: "100%",
    height: "100%",
    minHeight: 0,
    overflow: "hidden",
  },
  overlayButtons: {
    position: "absolute",
    bottom: "0.3rem",
    right: "0.3rem",
    display: "flex",
    alignItems: "center",
    gap: "0.2rem",
  },
  tooltip: {
    maxWidth: "60rem",
    fontSize: "1.2rem",
  },
  tooltipContent: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    width: "100%",
  },
  legend: {
    width: "100%",
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    gap: "10px",
  },
  circle: {
    borderRadius: "50%",
    width: "25px",
    height: "25px",
    display: "inline-block",
  },
  rect: {
    width: "25px",
    height: "25px",
    display: "inline-block",
  },
}));

interface TitleProps {
  classes: Record<string, string>;
}

const Title = ({ classes }: TitleProps) => (
  <div className={classes["tooltipContent"]}>
    <div className={classes["legend"]}>
      <div style={{ background: "#f9d71c" }} className={classes["circle"]} />
      <p> Daytime</p>
    </div>
    <div className={classes["legend"]}>
      <div style={{ background: "#0c1445" }} className={classes["circle"]} />
      <p> Nighttime</p>
    </div>
    <div className={classes["legend"]}>
      <div style={{ background: "#5ca9d6" }} className={classes["rect"]} />
      <p> Networks and Space-based Instruments</p>
    </div>
  </div>
);

interface TelescopeToolTipProps {
  classes: Record<string, string>;
}

const TelescopeToolTip = ({ classes }: TelescopeToolTipProps) => (
  <Tooltip
    title={<Title classes={classes} />}
    placement="bottom-end"
    classes={{ tooltip: classes["tooltip"] ?? "" }}
  >
    <HelpOutlineOutlinedIcon color="action" />
  </Tooltip>
);

interface TelescopeMapWidgetProps {
  classes: Record<string, string>;
}

const TelescopeMapWidget = ({
  classes: parentClasses,
}: TelescopeMapWidgetProps) => {
  const { classes } = useStyles();
  const { telescopeList } = useAppSelector((state) => state["telescopes"]);
  const [mapKey, setMapKey] = useState(0);

  return (
    <Suspense fallback={<CircularProgress color="secondary" />}>
      <Paper elevation={1} className={parentClasses["widgetPaperFillSpace"]}>
        <div className={parentClasses["widgetPaperDiv"]}>
          <div className={classes.mapContainer}>
            <TelescopeMap key={mapKey} telescopes={telescopeList} />
            <div className={classes.overlayButtons}>
              <Tooltip title="Reset view" placement="top">
                <IconButton
                  size="small"
                  onClick={() => setMapKey((k) => k + 1)}
                >
                  <ReplayIcon color="action" fontSize="small" />
                </IconButton>
              </Tooltip>
              <TelescopeToolTip classes={classes} />
            </div>
          </div>
        </div>
      </Paper>
    </Suspense>
  );
};

export default TelescopeMapWidget;
