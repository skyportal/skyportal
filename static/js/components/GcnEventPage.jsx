import React, { useRef, useEffect,useState } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";
import { makeStyles } from "@material-ui/core/styles";
import CircularProgress from "@material-ui/core/CircularProgress";
import IconButton from "@material-ui/core/IconButton";
import GetAppIcon from "@material-ui/icons/GetApp";

import * as sourcesActions from "../ducks/sources";

import * as d3 from "d3";
// eslint-disable-next-line
import d3GeoZoom from "d3-geo-zoom";
// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

//import Aladin from "./Aladin";
import Aladin from './Aladin';

import * as gcnEventActions from "../ducks/gcnEvent";
import * as localizationActions from "../ducks/localization";
import Typography from "@material-ui/core/Typography";
import SourceTable from "./SourceTable";

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
const CreateSkyMap = ({ loc,sources }) => {
    console.log('sources ==',sources)
  // get the localization data to display in the skymap
  const localization = useSelector((state) => state.localization);
  const {instrumentList} = useSelector((state)=>state.instruments);
  console.log('instrumentList ==============================',instrumentList)
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

  console.log('localization 9282763 ===========',localization)

  // else return the Aladin Skymap
  if(instrumentList.length>0){
      console.log('instrumentList data bizarre ',instrumentList)
      return(<Aladin
        ra={13.623}
        dec={-23.8063}
        fov={180.0}
        height={400}
        width={700}
        data={instrumentList[0]?.fields[0]?.contour}
        sources={sources}
        mode="P/Mellinger/color"/>)
  }
  return (
    <Aladin
        ra={13.623}
        dec={-23.8063}
        fov={180.0}
        height={400}
        width={700}
        data={instrumentList[0]?.fields[0]?.contour}
        sources={sources}
        mode="P/Mellinger/color"/>
  );
}

const GcnEventSourcesPage = ({ route, sources }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [sourcesRowsPerPage, setSourcesRowsPerPage] = useState(100);

  const handleSourcesTableSorting = (sortData, filterData) => {
    dispatch(
      sourcesActions.fetchGcnEventSources(route.dateobs, {
        ...filterData,
        pageNumber: 1,
        numPerPage: sourcesRowsPerPage,
        sortBy: sortData.name,
        sortOrder: sortData.direction,
      })
    );
  };

  const handleSourcesTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData
  ) => {
    setSourcesRowsPerPage(numPerPage);
    const data = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(sourcesActions.fetchGcnEventSources(route.dateobs, data));
  };

  return <p>No Sources</p>

  // eslint-disable-next-line
  if (sources?.sources.length === 0) {
    return (
      <div className={classes.source}>
        <Typography variant="h4" gutterBottom align="center">
          Event sources
        </Typography>
        <br />
        <Typography variant="h5" align="center">
          No sources within localization.
        </Typography>
      </div>
    );
  }

  return (
    <div className={classes.source}>
      <Typography variant="h4" gutterBottom align="center">
        Event sources
      </Typography>
      <SourceTable
        sources={sources.sources}
        title="Event Sources"
        paginateCallback={handleSourcesTablePagination}
        pageNumber={sources.pageNumber}
        totalMatches={sources.totalMatches}
        numPerPage={sources.numPerPage}
        sortingCallback={handleSourcesTableSorting}
        favoritesRemoveButton
      />
    </div>
  );
};

const GcnEventPage = ({ route }) => {
  const mapRef = useRef();
  const gcnEvent = useSelector((state) => state?.gcnEvent);
  const dispatch = useDispatch();
  const styles = useStyles();
  const gcnEventSources = useSelector((state) => state?.sources?.gcnEventSources);


  useEffect(() => {
    dispatch(gcnEventActions.fetchGcnEvent(route.dateobs));
  }, [route, dispatch]);

   useEffect(() => {
    dispatch(sourcesActions.fetchGcnEventSources(route.dateobs));
  }, [route, dispatch]);

  if (!gcnEvent || !gcnEventSources) {
    return <CircularProgress />;
  }

  console.log('gcnEvent.localizations ====',gcnEvent.localizations)
  console.log('gcnEventSources == ',gcnEventSources)

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
              <CreateSkyMap loc={localization} sources={gcnEventSources?.geojson}/>
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
      <div>
        <GcnEventSourcesPage route={route} sources={gcnEventSources} />
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

GcnEventSourcesPage.propTypes = {
  route: PropTypes.shape({
    dateobs: PropTypes.string,
  }).isRequired,
  sources: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      ra: PropTypes.number,
      dec: PropTypes.number,
      origin: PropTypes.string,
      alias: PropTypes.arrayOf(PropTypes.string),
      redshift: PropTypes.number,
      classifications: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          classification: PropTypes.string,
          created_at: PropTypes.string,
          groups: PropTypes.arrayOf(
            PropTypes.shape({
              id: PropTypes.number,
              name: PropTypes.string,
            })
          ),
        })
      ),
      recent_comments: PropTypes.arrayOf(PropTypes.shape({})),
      altdata: PropTypes.shape({
        tns: PropTypes.shape({
          name: PropTypes.string,
        }),
      }),
      spectrum_exists: PropTypes.bool,
      last_detected_at: PropTypes.string,
      last_detected_mag: PropTypes.number,
      peak_detected_at: PropTypes.string,
      peak_detected_mag: PropTypes.number,
      groups: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          name: PropTypes.string,
        })
      ),
    })
  ).isRequired,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
};

GcnEventSourcesPage.defaultProps = {
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
};

export default GcnEventPage;