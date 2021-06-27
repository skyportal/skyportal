import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";
import { makeStyles } from "@material-ui/core/styles";
import CircularProgress from "@material-ui/core/CircularProgress";
import IconButton from "@material-ui/core/IconButton";
import GetAppIcon from "@material-ui/icons/GetApp";
import { geoOrthographic, geoPath } from "d3-geo";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import * as gcnEventActions from "../ducks/gcnEvent";
import * as localizationActions from "../ducks/localization";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  header: {},
  gcnEventContainer: {
    height: "calc(100% - 5rem)",
    overflowY: "auto",
    marginTop: "0.625rem",
    paddingTop: "0.625rem",
  },
  gcnEvent: {
    display: "block",
    alignItems: "center",
    listStyleType: "none",
    paddingLeft: 0,
    marginTop: 0,
  },
  eventTags: {
    marginLeft: "1rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
  },
  BNS: {
    background: "#468847!important",
  },
  NSBH: {
    background: "#b94a48!important",
  },
  BBH: {
    background: "#333333!important",
  },
  GRB: {
    background: "#f89406!important",
  },
  AMON: {
    background: "#3a87ad!important",
  },
  Terrestrial: {
    background: "#999999!important",
  },
}));

const DownloadXMLButton = ({ gcn_notice }) => {
  const blob = new Blob([gcn_notice.content], { type: "text/plain" });

  return (
    <div>
      <Chip size="small" label={gcn_notice.ivorn} key={gcn_notice.ivorn} />
      <IconButton href={URL.createObjectURL(blob)} download={gcn_notice.ivorn}>
        <GetAppIcon />
      </IconButton>
    </div>
  );
};

const WorldMap = ({ localization, scale, cx, cy, rotation }) => {
  const projection = geoOrthographic()
    .scale(scale)
    .translate([cx, cy])
    .rotate([rotation, 0]);

  return (
    <>
      <Button size="medium" color="primary" />
      <svg width={scale * 3} height={scale * 3} viewBox="0 0 800 450">
        <g>
          <circle fill="#f2f2f2" cx={cx} cy={cy} r={scale} />
        </g>
        <g>
          <path
            d={geoPath().projection(projection)(localization.contour)}
            stroke="aliceblue"
          />
        </g>
      </svg>
    </>
  );
};

const Localization = ({ loc }) => {
  const localization = useSelector((state) => state.localization);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(
      localizationActions.fetchLocalization(loc.dateobs, loc.localization_name)
    );
  }, [loc, dispatch]);

  if (!localization) {
    return <CircularProgress />;
  }

  return (
    <>
      <WorldMap
        localization={localization}
        scale={200}
        cx={400}
        cy={150}
        initRotation={0}
      />
    </>
  );
};

const GcnEventPage = ({ route }) => {
  const gcnEvent = useSelector((state) => state.gcnEvent);
  const dispatch = useDispatch();
  const styles = useStyles();

  useEffect(() => {
    dispatch(gcnEventActions.fetchGcnEvent(route.dateobs));
  }, [route, dispatch]);

  if (!gcnEvent) {
    return <CircularProgress />;
  }

  return (
    <div className={styles.gcnEventContainer}>
      <ul className={styles.gcnEvent}>
        <h1 style={{ display: "inline-block" }}>Event Information</h1>
        <div>
          &nbsp; -&nbsp;
          <Link to={`/gcn_events/${gcnEvent.dateobs}`}>
            <Button color="primary">
              {dayjs(gcnEvent.dateobs).format("YYMMDD HH:mm:ss")}
            </Button>
          </Link>
          ({dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))})
        </div>
        {gcnEvent.lightcurve && (
          <div>
            {" "}
            <h3 style={{ display: "inline-block" }}>Light Curve</h3> &nbsp;
            -&nbsp; <img src={gcnEvent.lightcurve} alt="loading..." />{" "}
          </div>
        )}
        <h3 style={{ display: "inline-block" }}>Tags</h3>
        <div>
          &nbsp; -&nbsp;
          <div className={styles.eventTags}>
            {gcnEvent.tags?.map((tag) => (
              <Chip
                className={styles[tag]}
                size="small"
                label={tag}
                key={tag}
              />
            ))}
          </div>
        </div>
        <h3 style={{ display: "inline-block" }}>Skymaps</h3>
        <div>
          &nbsp; -&nbsp;
          {gcnEvent.localizations?.map((localization) => (
            <li key={localization.localization_name}>
              <Localization loc={localization} />
            </li>
          ))}
        </div>
        <h3 style={{ display: "inline-block" }}>GCN Notices</h3>
        <div>
          &nbsp; -&nbsp;
          {gcnEvent.gcn_notices?.map((gcn_notice) => (
            <li key={gcn_notice.ivorn}>
              <DownloadXMLButton gcn_notice={gcn_notice} />
            </li>
          ))}
        </div>
      </ul>
    </div>
  );
};

Localization.propTypes = {
  loc: PropTypes.shape({
    dateobs: PropTypes.string,
    localization_name: PropTypes.string,
  }).isRequired,
};

DownloadXMLButton.propTypes = {
  gcn_notice: PropTypes.shape({
    content: PropTypes.string,
    ivorn: PropTypes.string,
  }).isRequired,
};

GcnEventPage.propTypes = {
  route: PropTypes.shape({
    dateobs: PropTypes.string,
  }).isRequired,
};

WorldMap.propTypes = {
  localization: PropTypes.shape({
    contour: PropTypes.string,
  }).isRequired,
  scale: PropTypes.number.isRequired,
  cx: PropTypes.number.isRequired,
  cy: PropTypes.number.isRequired,
  rotation: PropTypes.number.isRequired,
};

export default GcnEventPage;
