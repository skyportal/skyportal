import React, { useEffect, useState, useRef } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Chip from "@mui/material/Chip";
import makeStyles from "@mui/styles/makeStyles";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import IconButton from "@mui/material/IconButton";
import GetAppIcon from "@mui/icons-material/GetApp";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import { showNotification } from "baselayer/components/Notifications";
import { useTheme } from "@mui/material/styles";

// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import Button from "./Button";

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
import GcnAliases from "./GcnAliases";
import GcnEventAllocationTriggers from "./GcnEventAllocationTriggers";
import GcnCirculars from "./GcnCirculars";
import GcnLocalizationsTable from "./GcnLocalizationsTable";
import GcnProperties from "./GcnProperties";
import Reminders from "./Reminders";

import withRouter from "./withRouter";
import { postLocalizationFromNotice } from "../ducks/localization";
import * as localizationActions from "../ducks/localization";

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
  noticeListElement: {
    display: "flex",
    flexDirection: "column",
  },
  noticeListElementHeader: {
    display: "flex",
    flexDirection: "row",
    // make sure to use the whole width of the parent
    width: "100%",
    justifyContent: "space-between",
    alignItems: "center",
  },
  noticeListElementIVORN: {
    width: "100%",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  noticeListDivider: {
    width: "100%",
    height: "1px",
    background: theme.palette.grey[300],
    margin: "0.5rem 0",
  },
}));

const DownloadXMLButton = ({ gcn_notice }) => {
  const blob = new Blob([gcn_notice.content], { type: "text/plain" });

  return (
    <IconButton
      href={URL.createObjectURL(blob)}
      download={gcn_notice.ivorn}
      size="large"
    >
      <GetAppIcon />
    </IconButton>
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

const sidebarWidth = 190;

const GcnEventPage = ({ route }) => {
  const ref = useRef(null);
  const theme = useTheme();
  const initialWidth =
    window.innerWidth - sidebarWidth - 2 * parseInt(theme.spacing(2), 10);
  const [width, setWidth] = useState(initialWidth);

  const gcnEvent = useSelector((state) => state.gcnEvent);
  const dispatch = useDispatch();
  const styles = useStyles();
  const [selectedLocalizationName, setSelectedLocalizationName] =
    useState(null);
  const [fetchingCachedLocalization, setFetchingCachedLocalization] =
    useState(false);
  const [sourceFilteringState, setSourceFilteringState] = useState({
    startDate: null,
    endDate: null,
    localizationCumprob: null,
  });
  const currentUser = useSelector((state) => state.profile);
  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage GCNs");

  const gcnEventSources = useSelector(
    (state) => state?.sources?.gcnEventSources
  );
  const gcnEventGalaxies = useSelector(
    (state) => state?.galaxies?.gcnEventGalaxies
  );

  const gcnEventObservations = useSelector(
    (state) => state?.observations?.gcnEventObservations
  );

  const cachedLocalization = useSelector((state) => state.localization.cached);

  useEffect(() => {
    const handleResize = () => {
      if (ref.current !== null) {
        setWidth(ref.current.offsetWidth);
      }
    };

    window.addEventListener("resize", handleResize);
  }, [ref]);

  useEffect(() => {
    const fetchGcnEvent = async (dateobs) => {
      await dispatch(gcnEventActions.fetchGcnEvent(dateobs));
      await dispatch(gcnEventActions.fetchGcnTach(dateobs));
    };
    if (route?.dateobs !== gcnEvent?.dateobs && route?.dateobs) {
      fetchGcnEvent(route?.dateobs);
    }
  }, [route, dispatch]);

  // if there is no cached localization, then we need to fetch it
  useEffect(() => {
    if (!gcnEvent || fetchingCachedLocalization) {
      return;
    }
    if (
      !cachedLocalization ||
      cachedLocalization?.dateobs !== gcnEvent?.dateobs
    ) {
      if (
        fetchingCachedLocalization === false &&
        gcnEvent?.localizations?.length > 0
      ) {
        dispatch(
          localizationActions.fetchLocalization(
            gcnEvent?.dateobs,
            gcnEvent.localizations[0]?.localization_name
          )
        ).then(() => {
          setFetchingCachedLocalization(false);
        });
      }
    }
  }, [gcnEvent, dispatch]);

  if (!gcnEvent) {
    return <Spinner />;
  }

  let xs = 7;
  if (width < 600) {
    xs = 14;
  }

  const handleUpdateAliasesCirculars = () => {
    dispatch(gcnEventActions.postGcnTach(gcnEvent.dateobs)).then((response) => {
      if (response.status === "success") {
        dispatch(
          showNotification(
            "Aliases and Circulars update started. Please wait..."
          )
        );
        if (gcnEvent?.aliases?.length === 0) {
          dispatch(
            showNotification(
              "This has never been done for this event before. It may take few minutes.",
              "warning"
            )
          );
        }
      } else {
        dispatch(showNotification("Error updating aliases", "error"));
      }
    });
  };

  return (
    <div ref={ref}>
      <Grid container spacing={2} className={styles.source}>
        <Grid item xs={xs}>
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
                    <Button>
                      {dayjs(gcnEvent.dateobs).format("YYMMDD HH:mm:ss")}
                    </Button>
                  </Link>
                  ({dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))})
                </div>
                <div>
                  <GcnTags gcnEvent={gcnEvent} show_title />
                </div>
                <div className={styles.gcnEventContainer}>
                  <GcnEventAllocationTriggers
                    gcnEvent={gcnEvent}
                    showPassed
                    showUnset
                    showTitle
                  />
                </div>
              </AccordionDetails>
            </Accordion>
          </div>
          <div className={styles.columnItem}>
            <Accordion defaultExpanded>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="gcnEvent-content"
                id="info-header"
              >
                <Typography className={styles.accordionHeading}>
                  Event Properties
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <div className={styles.eventTags}>
                  <GcnProperties properties={gcnEvent.properties} />
                </div>
              </AccordionDetails>
            </Accordion>
          </div>
          <div className={styles.columnItem}>
            <Accordion defaultExpanded>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="gcnEvent-content"
                id="info-header"
              >
                <Typography className={styles.accordionHeading}>
                  Localization Properties
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <div className={styles.eventTags}>
                  <GcnLocalizationsTable
                    localizations={gcnEvent.localizations}
                  />
                </div>
              </AccordionDetails>
            </Accordion>
          </div>
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
                  {route?.dateobs === gcnEvent?.dateobs &&
                    route?.dateobs &&
                    gcnEvent?.localizations?.length > 0 && (
                      <>
                        <GcnSelectionForm
                          dateobs={route.dateobs}
                          setSelectedLocalizationName={
                            setSelectedLocalizationName
                          }
                          setSourceFilteringState={setSourceFilteringState}
                        />
                      </>
                    )}
                  {route?.dateobs && !gcnEvent?.dateobs && (
                    <p> Fetching event... </p>
                  )}
                  {route?.dateobs &&
                    route?.dateobs === gcnEvent?.dateobs &&
                    (gcnEvent?.localizations?.length === 0 ||
                      !gcnEvent?.localizations) && (
                      <>
                        <p>
                          No localization available for this event (yet). Some
                          localizations are available after the notices.{" "}
                        </p>
                        <p>
                          You can try ingesting the localization from the
                          Notices menu on the right of this page
                        </p>
                      </>
                    )}
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
                  {route?.dateobs === gcnEvent?.dateobs &&
                    route?.dateobs &&
                    gcnEvent?.localizations?.length > 0 && (
                      <>
                        <ObservationPlanRequestForm
                          dateobs={route?.dateobs}
                          action="createNew"
                        />
                        <ObservationPlanRequestLists dateobs={route?.dateobs} />
                      </>
                    )}
                  {route?.dateobs && !gcnEvent?.dateobs && (
                    <p> Fetching event... </p>
                  )}
                  {route?.dateobs &&
                    route?.dateobs === gcnEvent?.dateobs &&
                    (gcnEvent?.localizations?.length === 0 ||
                      !gcnEvent?.localizations) && (
                      <>
                        <p>
                          No localization available for this event (yet). Some
                          localizations are available after the notices.{" "}
                        </p>
                        <p>
                          You can try ingesting the localization from the
                          Notices menu on the right of this page
                        </p>
                      </>
                    )}
                </div>
              </AccordionDetails>
            </Accordion>
          </div>
        </Grid>

        {width > 600 && (
          <Grid item xs={5}>
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
                  {route?.dateobs === gcnEvent?.dateobs && route?.dateobs ? (
                    <CommentList
                      associatedResourceType="gcn_event"
                      gcnEventID={gcnEvent.id}
                    />
                  ) : (
                    <p> Fetching event... </p>
                  )}
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
                    {route?.dateobs === gcnEvent?.dateobs && route?.dateobs ? (
                      <>
                        {gcnEvent?.lightcurve && (
                          <div>
                            <img src={gcnEvent.lightcurve} alt="loading..." />
                          </div>
                        )}
                      </>
                    ) : (
                      <p> Fetching event... </p>
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
                  id="gcnnotices-header"
                >
                  <Typography className={styles.accordionHeading}>
                    GCN Notices
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <div className={styles.gcnEventContainer}>
                    {gcnEvent.gcn_notices?.map((gcn_notice) => (
                      <li
                        key={gcn_notice.ivorn}
                        className={styles.noticeListElement}
                      >
                        <div className={styles.noticeListElementHeader}>
                          <Chip
                            size="small"
                            label={gcn_notice.ivorn}
                            key={gcn_notice.ivorn}
                            className={styles.noticeListElementIVORN}
                          />
                          <DownloadXMLButton gcn_notice={gcn_notice} />
                        </div>
                        {gcn_notice?.has_localization &&
                          gcn_notice?.localization_ingested === false && (
                            <Button
                              secondary
                              onClick={() => {
                                dispatch(
                                  showNotification(
                                    `Starting ingestion attempt for localization from notice ${gcn_notice.id}. Please wait...`,
                                    "warning"
                                  )
                                );
                                dispatch(
                                  postLocalizationFromNotice({
                                    dateobs: gcn_notice.dateobs,
                                    noticeID: gcn_notice.id,
                                  })
                                ).then((response) => {
                                  if (response.status === "success") {
                                    dispatch(
                                      showNotification(
                                        `Localization successfully ingested from notice ${gcn_notice.id}. Please wait for the contour to be generated. Default observation plans will be created shortly.`
                                      )
                                    );
                                  } else {
                                    dispatch(
                                      showNotification(
                                        `Error ingesting localization from notice ${gcn_notice.id}. It might not be available yet.`,
                                        "error"
                                      )
                                    );
                                  }
                                });
                              }}
                              data-testid="ingest-localization-from-notice"
                            >
                              Ingest Localization
                            </Button>
                          )}
                        <div className={styles.noticeListDivider} />
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
                  id="gcnnotices-header"
                >
                  <Typography className={styles.accordionHeading}>
                    GCN Aliases
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <div className={styles.gcnEventContainer}>
                    <GcnAliases gcnEvent={gcnEvent} />
                  </div>
                  {permission && (
                    <Button
                      secondary
                      onClick={() => handleUpdateAliasesCirculars()}
                      data-testid="update-aliases"
                    >
                      Update
                    </Button>
                  )}
                </AccordionDetails>
              </Accordion>
            </div>
            <div className={styles.columnItem}>
              <Accordion defaultExpanded>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  aria-controls="gcnEvent-content"
                  id="gcncirculars-header"
                >
                  <Typography className={styles.accordionHeading}>
                    GCN Circulars
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <div className={styles.gcnEventContainer}>
                    <GcnCirculars gcnEvent={gcnEvent} />
                  </div>
                  {permission && (
                    <Button
                      secondary
                      onClick={() => handleUpdateAliasesCirculars()}
                      data-testid="update-circulars"
                    >
                      Update
                    </Button>
                  )}
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
                    <Typography variant="h5">
                      Fetching observations...
                    </Typography>
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
                            showTitle
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
            <div className={styles.columnItem}>
              <Accordion defaultExpanded>
                <AccordionDetails>
                  <div className={styles.gcnEventContainer}>
                    {route?.dateobs === gcnEvent?.dateobs && route?.dateobs ? (
                      <Reminders
                        resourceId={gcnEvent.id.toString()}
                        resourceType="gcn_event"
                      />
                    ) : (
                      <p> Fetching event... </p>
                    )}
                  </div>
                </AccordionDetails>
              </Accordion>
            </div>
          </Grid>
        )}
      </Grid>
    </div>
  );
};

GcnEventPage.propTypes = {
  route: PropTypes.shape({
    dateobs: PropTypes.string,
  }).isRequired,
};

export default withRouter(GcnEventPage);
