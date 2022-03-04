import React, { useRef, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import Accordion from "@material-ui/core/Accordion";
import AccordionSummary from "@material-ui/core/AccordionSummary";
import AccordionDetails from "@material-ui/core/AccordionDetails";
import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";
import { makeStyles } from "@material-ui/core/styles";
import CircularProgress from "@material-ui/core/CircularProgress";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";
import IconButton from "@material-ui/core/IconButton";
import GetAppIcon from "@material-ui/icons/GetApp";
import Typography from "@material-ui/core/Typography";

// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import * as gcnEventActions from "../ducks/gcnEvent";
import * as localizationActions from "../ducks/localization";
import * as sourcesActions from "../ducks/sources";
import * as observationsActions from "../ducks/observations";
import * as galaxiesActions from "../ducks/galaxies";
import * as instrumentsActions from "../ducks/instruments";

import SourceTable from "./SourceTable";
import GalaxyTable from "./GalaxyTable";
import ExecutedObservationsTable from "./ExecutedObservationsTable";
import GcnSelectionForm from "./GcnSelectionForm";
import GeoJSONGlobePlot from "./GeoJSONGlobePlot";

import ObservationPlanRequestForm from "./ObservationPlanRequestForm";
import ObservationPlanRequestLists from "./ObservationPlanRequestLists";

import GcnTags from "./GcnTags";

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
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
  gcnEventContainer: {
    display: "flex",
    overflow: "hidden",
    flexDirection: "column",
  },
  columnItem: {
    marginBottom: theme.spacing(2),
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

DownloadXMLButton.propTypes = {
  gcn_notice: PropTypes.shape({
    content: PropTypes.string,
    ivorn: PropTypes.string,
  }).isRequired,
};

const Localization = ({ loc, sources, galaxies, instruments }) => {
  const cachedLocalization = useSelector((state) => state.localization);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(
      localizationActions.fetchLocalization(loc.dateobs, loc.localization_name)
    );
  }, [loc, dispatch]);

  const localization =
    loc.id === cachedLocalization?.id ? cachedLocalization : null;

  if (!localization || !instruments) {
    return <CircularProgress />;
  }

  const instruments_with_contour = [];
  instruments?.forEach((instrument) => {
    if (instrument?.fields.length > 0) {
      if (instrument.fields[0].contour_summary) {
        instruments_with_contour.push(instrument);
      }
    }
  });

  return (
    <>
      <Chip
        size="small"
        label={localization.localization_name}
        key={localization.localization_name}
      />
      {instruments_with_contour.length === 0 ? (
        <GeoJSONGlobePlot
          skymap={localization.contour}
          sources={sources.geojson}
          galaxies={galaxies.geojson}
        />
      ) : (
        <GeoJSONGlobePlot
          skymap={localization.contour}
          sources={sources.geojson}
          galaxies={galaxies.geojson}
          instrument={instruments_with_contour[0]}
        />
      )}
    </>
  );
};

Localization.propTypes = {
  loc: PropTypes.shape({
    id: PropTypes.number,
    dateobs: PropTypes.string,
    localization_name: PropTypes.string,
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
  galaxies: PropTypes.arrayOf(
    PropTypes.shape({
      catalog_name: PropTypes.string,
      name: PropTypes.String,
      alt_name: PropTypes.String,
      ra: PropTypes.number,
      dec: PropTypes.number,
      distmpc: PropTypes.number,
      distmpc_unc: PropTypes.number,
      redshift: PropTypes.number,
      redshift_error: PropTypes.number,
      sfr_fuv: PropTypes.number,
      mstar: PropTypes.number,
      magb: PropTypes.number,
      magk: PropTypes.number,
      a: PropTypes.number,
      b2a: PropTypes.number,
      pa: PropTypes.number,
      btc: PropTypes.number,
    })
  ).isRequired,
  instruments: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.String,
      type: PropTypes.String,
      band: PropTypes.String,
      fields: PropTypes.arrayOf(
        PropTypes.shape({
          ra: PropTypes.number,
          dec: PropTypes.number,
          id: PropTypes.number,
        })
      ),
    })
  ).isRequired,
};

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

  // eslint-disable-next-line
  if (sources?.sources.length === 0) {
    return (
      <div className={classes.source}>
        <Typography variant="h5">Event sources</Typography>
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
  data: PropTypes.shape({
    length: PropTypes.number,
    features: GeoPropTypes.FeatureCollection,
  }).isRequired,
};

GcnEventSourcesPage.defaultProps = {
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
};

const GcnEventPage = ({ route }) => {
  const mapRef = useRef();
  const gcnEvent = useSelector((state) => state.gcnEvent);
  const dispatch = useDispatch();
  const styles = useStyles();

  const gcnEventSources = useSelector(
    (state) => state?.sources?.gcnEventSources
  );
  const gcnEventGalaxies = useSelector(
    (state) => state?.galaxies?.gcnEventGalaxies
  );

  const gcnEventObservations = useSelector(
    (state) => state?.observations?.gcnEventObservations
  );

  const gcnEventInstruments = useSelector(
    (state) => state?.instruments?.gcnEventInstruments
  );

  useEffect(() => {
    dispatch(gcnEventActions.fetchGcnEvent(route.dateobs));
  }, [route, dispatch]);

  useEffect(() => {
    dispatch(sourcesActions.fetchGcnEventSources(route.dateobs));
  }, [route, dispatch]);

  useEffect(() => {
    dispatch(observationsActions.fetchGcnEventObservations(route.dateobs));
  }, [route, dispatch]);

  useEffect(() => {
    dispatch(galaxiesActions.fetchGcnEventGalaxies(route.dateobs));
  }, [route, dispatch]);

  useEffect(() => {
    dispatch(instrumentsActions.fetchGcnEventInstruments(route.dateobs));
  }, [route, dispatch]);

  if (
    !gcnEvent ||
    !gcnEventSources ||
    !gcnEventObservations ||
    !gcnEventGalaxies ||
    !gcnEventInstruments
  ) {
    return <CircularProgress />;
  }

  return (
    <div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="info-header"
          >
            <Typography className={styles.accordionHeading}>
              Event Information
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.gcnEventContainer}>
              <Link to={`/gcn_events/${gcnEvent.dateobs}`}>
                <Button color="primary">
                  {dayjs(gcnEvent.dateobs).format("YYMMDD HH:mm:ss")}
                </Button>
              </Link>
              ({dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))})
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="lightcurve-header"
          >
            <Typography className={styles.accordionHeading}>
              Light curve
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.gcnEventContainer}>
              {gcnEvent.lightcurve && (
                <div>
                  {" "}
                  <img src={gcnEvent.lightcurve} alt="loading..." />{" "}
                </div>
              )}
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="eventtags-header"
          >
            <Typography className={styles.accordionHeading}>
              Event Tags
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.eventTags}>
              <GcnTags gcnEvent={gcnEvent} />
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="gcnnotices-header"
          >
            <Typography className={styles.accordionHeading}>
              GCN Notices
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.gcnEventContainer}>
              {gcnEvent.gcn_notices?.map((gcn_notice) => (
                <li key={gcn_notice.ivorn}>
                  <DownloadXMLButton gcn_notice={gcn_notice} />
                </li>
              ))}
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="skymap-header"
          >
            <Typography className={styles.accordionHeading}>Skymaps</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.gcnEventContainer}>
              {gcnEvent.localizations?.map((localization) => (
                <li key={localization.localization_name}>
                  <div id="map" ref={mapRef}>
                    <Localization
                      loc={localization}
                      sources={gcnEventSources}
                      galaxies={gcnEventGalaxies}
                      instruments={gcnEventInstruments}
                    />
                  </div>
                </li>
              ))}
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary>
            <Typography className={styles.accordionHeading}>
              Modify Skymap Selection
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.gcnEventContainer}>
              <GcnSelectionForm gcnEvent={gcnEvent} />
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="sources-header"
          >
            <Typography className={styles.accordionHeading}>
              Sources within localization
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            {gcnEventSources?.sources.length === 0 ? (
              <Typography variant="h5">None             </Typography>
            ) : (
              <div className={styles.gcnEventContainer}>
                             {" "}
                <GcnEventSourcesPage route={route} sources={gcnEventSources} /> 
                         {" "}
              </div>
            )}
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="observations-header"
          >
            <Typography className={styles.accordionHeading}>
              Observations within localization
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            {gcnEventObservations?.length === 0 ? (
              <Typography variant="h5">None             </Typography>
            ) : (
              <div className={styles.gcnEventContainer}>
                             {" "}
                <ExecutedObservationsTable
                  observations={gcnEventObservations}
                />
                           {" "}
              </div>
            )}
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="galaxies-header"
          >
            <Typography className={styles.accordionHeading}>
              Galaxies within localization
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            {gcnEventGalaxies?.sources.length === 0 ? (
              <Typography variant="h5">None             </Typography>
            ) : (
              <div className={styles.gcnEventContainer}>
                             {" "}
                <GalaxyTable galaxies={gcnEventGalaxies.sources} />           {" "}
              </div>
            )}
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="observationplan-header"
          >
            <Typography className={styles.accordionHeading}>
              Observation Plans
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.gcnEventContainer}>
              <ObservationPlanRequestForm
                gcnevent={gcnEvent}
                action="createNew"
              />
              <ObservationPlanRequestLists
                observationplanRequests={gcnEvent.observationplan_requests}
              />
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
    </div>
  );
};

GcnEventPage.propTypes = {
  route: PropTypes.shape({
    dateobs: PropTypes.string,
  }).isRequired,
};

export default GcnEventPage;
