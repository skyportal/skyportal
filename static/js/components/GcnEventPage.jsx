import React, { useEffect, useState, useRef } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

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

import Drawer from "@mui/material/Drawer";

// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import Button from "./Button";

import * as gcnEventActions from "../ducks/gcnEvent";

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
  sidePanel: {
    width: "50vw",
    height: "100%",
    padding: "1rem",
  },
  header: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "1rem",
  },
  headerLeft: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-start",
    alignItems: "center",
    gap: "1rem",
  },
  headerRight: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "flex-end",
    alignItems: "center",
    alignContent: "center",
    gap: "1rem",
  },
  headerName: {
    fontSize: "2rem",
    fontWeight: "bold",
    color: theme.palette.primary.main,
    whiteSpace: "nowrap",
  },
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
    marginBottom: theme.spacing(1),
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

const GcnEventPage = ({ route }) => {
  const ref = useRef(null);
  const theme = useTheme();
  const styles = useStyles(theme);

  const gcnEvent = useSelector((state) => state.gcnEvent);
  const dispatch = useDispatch();
  const [selectedLocalizationName, setSelectedLocalizationName] =
    useState(null);
  const [fetchingCachedLocalization, setFetchingCachedLocalization] =
    useState(false);
  const currentUser = useSelector((state) => state.profile);
  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage GCNs");

  const cachedLocalization = useSelector((state) => state.localization.cached);

  const [leftPanelVisible, setLeftPanelVisible] = useState(false);
  const [rightPanelVisible, setRightPanelVisible] = useState(false);

  const toggleDrawer = (side, open) => (event) => {
    if (
      event.type === "keydown" &&
      (event.key === "Tab" || event.key === "Shift")
    ) {
      return;
    }
    if (side === "left") {
      setLeftPanelVisible(open);
    } else if (side === "right") {
      setRightPanelVisible(open);
    }
  };

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
        <Grid item xs={12}>
          <div className={styles.columnItem}>
            <div className={styles.header}>
              <div className={styles.headerLeft}>
                <Typography variant="h5" className={styles.headerName}>
                  {dayjs(gcnEvent.dateobs).format("YYMMDD HH:mm:ss")}
                </Typography>
                ({dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))})
                <GcnTags gcnEvent={gcnEvent} />
              </div>
              <div className={styles.headerRight}>
                <Button
                  secondary
                  onClick={() => setLeftPanelVisible(!leftPanelVisible)}
                  data-testid="hide-left-panel-button"
                >
                  Social Panel
                </Button>
                <Button
                  secondary
                  onClick={() => setRightPanelVisible(!rightPanelVisible)}
                  data-testid="hide-right-panel-button"
                >
                  Properties Panel
                </Button>
              </div>
            </div>
            <div>
              <GcnEventAllocationTriggers
                gcnEvent={gcnEvent}
                showPassed
                showUnset
                showTitle
              />
            </div>
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
                          selectedLocalizationName={selectedLocalizationName}
                          setSelectedLocalizationName={
                            setSelectedLocalizationName
                          }
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
      </Grid>
      <React.Fragment key="left">
        <Drawer
          anchor="left"
          open={leftPanelVisible}
          onClose={toggleDrawer("left", false)}
        >
          <div className={styles.sidePanel}>
            <div className={styles.columnItem}>
              <Accordion defaultExpanded>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  aria-controls="gcnEvent-content"
                  id="observations-header"
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
                      maxHeightList="60vh"
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
                  id="observations-header"
                >
                  <Typography className={styles.accordionHeading}>
                    Reminders
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {route?.dateobs === gcnEvent?.dateobs && route?.dateobs ? (
                    <Reminders
                      resourceId={gcnEvent.id.toString()}
                      resourceType="gcn_event"
                    />
                  ) : (
                    <p> Fetching event... </p>
                  )}
                </AccordionDetails>
              </Accordion>
            </div>
          </div>
        </Drawer>
      </React.Fragment>
      <React.Fragment key="right">
        <Drawer
          anchor="right"
          open={rightPanelVisible}
          onClose={toggleDrawer("right", false)}
        >
          <div className={styles.sidePanel}>
            {/* event properties */}
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
            {/* localization properties */}
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
          </div>
        </Drawer>
      </React.Fragment>
    </div>
  );
};

GcnEventPage.propTypes = {
  route: PropTypes.shape({
    dateobs: PropTypes.string,
  }).isRequired,
};

export default withRouter(GcnEventPage);
