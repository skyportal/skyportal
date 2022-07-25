import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import makeStyles from "@mui/styles/makeStyles";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import IconButton from "@mui/material/IconButton";
import GetAppIcon from "@mui/icons-material/GetApp";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";

// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as gcnEventActions from "../ducks/gcnEvent";
import * as sourcesActions from "../ducks/sources";

import SourceTable from "./SourceTable";
import GalaxyTable from "./GalaxyTable";
import ExecutedObservationsTable from "./ExecutedObservationsTable";
import GcnSelectionForm from "./GcnSelectionForm";
import Spinner from "./Spinner";

import ObservationPlanRequestForm from "./ObservationPlanRequestForm";
import ObservationPlanRequestLists from "./ObservationPlanRequestLists";

import CommentList from "./CommentList";
import GcnTags from "./GcnTags";

import withRouter from "./withRouter";

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
  comments: {
    width: "100%",
  },
  columnItem: {
    marginBottom: theme.spacing(2),
  },
  noSources: {
    padding: theme.spacing(2),
    display: "flex",
    flexDirection: "row",
  },
  sourceList: {
    padding: "0",
  },
}));

const DownloadXMLButton = ({ gcn_notice }) => {
  const blob = new Blob([gcn_notice.content], { type: "text/plain" });

  return (
    <div>
      <Chip size="small" label={gcn_notice.ivorn} key={gcn_notice.ivorn} />
      <IconButton
        href={URL.createObjectURL(blob)}
        download={gcn_notice.ivorn}
        size="large"
      >
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

const GcnEventSourcesPage = ({
  route,
  sources,
  localizationName,
  sourceFilteringState,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [sourcesRowsPerPage, setSourcesRowsPerPage] = useState(100);

  const handleSourcesTableSorting = (sortData, filterData) => {
    dispatch(
      sourcesActions.fetchGcnEventSources(route.dateobs, {
        ...filterData,
        localizationName,
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
      localizationName,
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
  if (!sources || sources?.sources?.length === 0) {
    return (
      <div className={classes.noSources}>
        <Typography variant="h5">Event sources</Typography>
        <br />
        <Typography variant="h5" align="center">
          No sources within localization.
        </Typography>
      </div>
    );
  }

  return (
    <div className={classes.sourceList}>
      <SourceTable
        sources={sources.sources}
        title="Event Sources"
        paginateCallback={handleSourcesTablePagination}
        pageNumber={sources.pageNumber}
        totalMatches={sources.totalMatches}
        numPerPage={sources.numPerPage}
        sortingCallback={handleSourcesTableSorting}
        favoritesRemoveButton
        hideTitle
        includeGcnStatus
        sourceInGcnFilter={sourceFilteringState}
      />
    </div>
  );
};

GcnEventSourcesPage.propTypes = {
  route: PropTypes.shape({
    dateobs: PropTypes.string,
  }).isRequired,
  sources: PropTypes.shape({
    pageNumber: PropTypes.number,
    totalMatches: PropTypes.number,
    numPerPage: PropTypes.number,
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
    ),
  }),
  localizationName: PropTypes.string.isRequired,
  sourceFilteringState: PropTypes.shape({
    startDate: PropTypes.string,
    endDate: PropTypes.string,
    localizationCumprob: PropTypes.number,
  }).isRequired,
};

GcnEventSourcesPage.defaultProps = {
  sources: null,
};

const GcnEventPage = ({ route }) => {
  const gcnEvent = useSelector((state) => state.gcnEvent);
  const dispatch = useDispatch();
  const styles = useStyles();
  const [selectedLocalizationName, setSelectedLocalizationName] =
    useState(null);
  const [sourceFilteringState, setSourceFilteringState] = useState({
    startDate: null,
    endDate: null,
    localizationCumprob: null,
  });

  const gcnEventSources = useSelector(
    (state) => state?.sources?.gcnEventSources
  );
  const gcnEventGalaxies = useSelector(
    (state) => state?.galaxies?.gcnEventGalaxies
  );

  const gcnEventObservations = useSelector(
    (state) => state?.observations?.gcnEventObservations
  );

  useEffect(() => {
    const fetchGcnEvent = async (dateobs) => {
      await dispatch(gcnEventActions.fetchGcnEvent(dateobs));
    };
    fetchGcnEvent(route.dateobs);
  }, [route, dispatch]);

  if (!gcnEvent) {
    return <Spinner />;
  }

  return (
    <Grid container spacing={2} className={styles.source}>
      <Grid item xs={7}>
        <div className={styles.columnItem}>
          <Accordion defaultExpanded>
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="gcnEvent-content"
              id="analysis-header"
            >
              <Typography className={styles.accordionHeading}>
                Analysis
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <div className={styles.gcnEventContainer}>
                <GcnSelectionForm
                  gcnEvent={gcnEvent}
                  setSelectedLocalizationName={setSelectedLocalizationName}
                  setSourceFilteringState={setSourceFilteringState}
                />
              </div>
            </AccordionDetails>
          </Accordion>
        </div>
        <div className={styles.columnItem}>
          <Accordion>
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
                <ObservationPlanRequestLists gcnEvent={gcnEvent} />
              </div>
            </AccordionDetails>
          </Accordion>
        </div>
      </Grid>
      <Grid item xs={5}>
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
          <Accordion
            defaultExpanded
            className={styles.comments}
            data-testid="comments-accordion"
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="comments-content"
              id="comments-header"
            >
              <Typography className={styles.accordionHeading}>
                Comments
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <CommentList
                associatedResourceType="gcn_event"
                gcnEventID={gcnEvent.id}
              />
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
                    <img src={gcnEvent.lightcurve} alt="loading..." />
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
              id="sources-header"
            >
              <Typography className={styles.accordionHeading}>
                Sources within localization
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              {gcnEventSources?.sources ? (
                <div>
                  {gcnEventSources?.sources.length === 0 ? (
                    <Typography variant="h5">None</Typography>
                  ) : (
                    <div className={styles.gcnEventContainer}>
                      {selectedLocalizationName && (
                        <GcnEventSourcesPage
                          route={route}
                          sources={gcnEventSources}
                          localizationName={selectedLocalizationName}
                          sourceFilteringState={sourceFilteringState}
                        />
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <Typography variant="h5">Fetching sources...</Typography>
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
              {gcnEventObservations?.observations ? (
                <div>
                  {gcnEventObservations?.observations.length === 0 ? (
                    <Typography variant="h5">None</Typography>
                  ) : (
                    <div className={styles.gcnEventContainer}>
                      <ExecutedObservationsTable
                        observations={gcnEventObservations.observations}
                        totalMatches={gcnEventObservations.totalMatches}
                        serverSide={false}
                      />
                    </div>
                  )}
                </div>
              ) : (
                <Typography variant="h5">Fetching observations...</Typography>
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
              {gcnEventGalaxies?.galaxies ? (
                <div>
                  {gcnEventGalaxies?.galaxies.length === 0 ? (
                    <Typography variant="h5">None</Typography>
                  ) : (
                    <div className={styles.gcnEventContainer}>
                      <GalaxyTable
                        galaxies={gcnEventGalaxies.galaxies}
                        totalMatches={gcnEventGalaxies.totalMatches}
                        serverSide={false}
                        hideTitle
                      />
                    </div>
                  )}
                </div>
              ) : (
                <Typography variant="h5">Fetching galaxies...</Typography>
              )}
            </AccordionDetails>
          </Accordion>
        </div>
      </Grid>
    </Grid>
  );
};

GcnEventPage.propTypes = {
  route: PropTypes.shape({
    dateobs: PropTypes.string,
  }).isRequired,
};

export default withRouter(GcnEventPage);
