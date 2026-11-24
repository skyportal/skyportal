import { lazy, Suspense, useState } from "react";
import { makeStyles } from "tss-react/mui";
import { Tooltip, IconButton } from "@mui/material";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
import ReplayIcon from "@mui/icons-material/Replay";

import { useGetTelescopesQuery } from "../../ducks/telescopes";
import WidgetCard from "./WidgetCard";
import WidgetLoading from "./WidgetLoading";

const TelescopeMap = lazy(() => import("../telescope/TelescopeMap"));

const useStyles = makeStyles()((_theme) => ({
  mapContainer: {
    position: "relative",
    width: "100%",
    height: "100%",
    minHeight: 0,
    overflow: "hidden",
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
    <IconButton size="small" aria-label="Legend">
      <HelpOutlineOutlinedIcon color="action" fontSize="small" />
    </IconButton>
  </Tooltip>
);

const TelescopeMapWidget = () => {
  const { classes } = useStyles();
  const { data: telescopeList = [] } = useGetTelescopesQuery();
  const [mapKey, setMapKey] = useState(0);

  return (
    <WidgetCard
      title="Telescopes"
      actions={
        <>
          <Tooltip title="Reset view">
            <IconButton size="small" onClick={() => setMapKey((k) => k + 1)}>
              <ReplayIcon color="action" fontSize="small" />
            </IconButton>
          </Tooltip>
          <TelescopeToolTip classes={classes} />
        </>
      }
      bodySx={{ p: 0, overflow: "hidden" }}
    >
      <div className={classes.mapContainer}>
        <Suspense fallback={<WidgetLoading />}>
          <TelescopeMap key={mapKey} telescopes={telescopeList} />
        </Suspense>
      </div>
    </WidgetCard>
  );
};

export default TelescopeMapWidget;
