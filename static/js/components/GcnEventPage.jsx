import React, { useRef, useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";
import { makeStyles } from "@material-ui/core/styles";
import CircularProgress from "@material-ui/core/CircularProgress";
import IconButton from "@material-ui/core/IconButton";
import GetAppIcon from "@material-ui/icons/GetApp";

// eslint-disable-next-line
import d3GeoZoom from "d3-geo-zoom";
// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import Aladin from "./Aladin";

import * as gcnEventActions from "../ducks/gcnEvent";
import * as localizationActions from "../ducks/localization";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  header: {},
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

// Create the skymap from Aladin and display the MOC Json
const CreateSkyMap = ({ loc }) => {
  // get the localization data to display in the skymap
  const localization = useSelector((state) => state.localization);
  const dispatch = useDispatch();

  // useEffect to fetch the data of localization
  useEffect(() => {
    dispatch(
      localizationActions.fetchLocalization(loc.dateobs, loc.localization_name)
    );
  }, [loc, dispatch]);

  // if you don't have data, display the loading icon
  if (!localization) {
    return <CircularProgress />;
  }

  // else return the Aladin Skymap
  return (
    <Aladin
      ra={13.623}
      dec={-23.8063}
      fov={180.0}
      height={400}
      width={700}
      feature_data={localization.contour}
      mode="P/Mellinger/color"
    />
  );
};

const GcnEventPage = ({ route }) => {
  const mapRef = useRef();
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
    <div>
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
            <Chip className={styles[tag]} size="small" label={tag} key={tag} />
          ))}
        </div>
      </div>
      <h3>Skymaps</h3>
      <div>
        &nbsp; -&nbsp;
        {gcnEvent.localizations?.map((localization) => (
          <li key={localization.localization_name}>
            <div id="map" ref={mapRef}>
              <CreateSkyMap loc={localization} />
            </div>
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
    </div>
  );
};

CreateSkyMap.propTypes = {
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

export default GcnEventPage;
