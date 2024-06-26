import PropTypes from "prop-types";
import React, { Suspense, useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import Cancel from "@mui/icons-material/Cancel";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import GetAppIcon from "@mui/icons-material/GetApp";
import CircularProgress from "@mui/material/CircularProgress";
import useMediaQuery from "@mui/material/useMediaQuery";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Chip from "@mui/material/Chip";
import DialogTitle from "@mui/material/DialogTitle";
import Drawer from "@mui/material/Drawer";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import { useTheme } from "@mui/material/styles";
import Typography from "@mui/material/Typography";
import makeStyles from "@mui/styles/makeStyles";

// eslint-disable-next-line

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import * as gcnEventActions from "../../ducks/gcnEvent";

import GcnSelectionForm from "./GcnSelectionForm";
import Spinner from "../Spinner";

import ObservationPlanRequestForm from "../observation_plan/ObservationPlanRequestForm";
import ObservationPlanRequestLists from "../observation_plan/ObservationPlanRequestLists";

import CommentList from "../comment/CommentList";
import DisplayGraceDB from "./DisplayGraceDB";
import GcnAliases from "./GcnAliases";
import GcnCirculars from "./GcnCirculars";
import GcnEventAllocationTriggers from "./GcnEventAllocationTriggers";
import GcnLocalizationsTable from "./GcnLocalizationsTable";
import GcnProperties from "./GcnProperties";
import GcnTags from "./GcnTags";
import Reminders from "../Reminders";

import { postLocalizationFromNotice } from "../../ducks/localization";
import withRouter from "../withRouter";

dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  sidePanel: {
    width: "100%",
    height: "100%",
    "& > .MuiPaper-root": {
      width: "100%",
      height: "100%",
    },
  },
  sidePanelContent: {
    width: "100%",
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
    height: "2rem",
    fontSize: "2rem",
    fontWeight: "bold",
    color: theme.palette.primary.main,
    whiteSpace: "nowrap",
    verticalAlign: "bottom",
    lineHeight: "1.7rem",
  },
  headerDate: {
    height: "1rem",
    fontSize: "1rem",
    whiteSpace: "nowrap",
  },
  headerButtons: {
    display: "grid",
    // we want to have 2 columns when the screen is large enough, otherwise 1 using gridTemplateColumns
    gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))",
    gap: "0.5rem",
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
  const theme = useTheme();
  const styles = useStyles(theme);

  const gcnEvent = useSelector((state) => state.gcnEvent);
  const dispatch = useDispatch();
  const currentUser = useSelector((state) => state.profile);
  const permission =
    currentUser.permissions?.includes("System admin") ||
    currentUser.permissions?.includes("Manage GCNs");

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

  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  if (!gcnEvent) {
    return <Spinner />;
  }

  const handleUpdateAliasesCirculars = () => {
    dispatch(gcnEventActions.postGcnTach(gcnEvent.dateobs)).then((response) => {
      if (response.status === "success") {
        dispatch(
          showNotification(
            "Aliases and Circulars update started. Please wait...",
          ),
        );
        if (gcnEvent?.aliases?.length === 0) {
          dispatch(
            showNotification(
              "This has never been done for this event before. It may take few minutes.",
              "warning",
            ),
          );
        }
      } else {
        dispatch(showNotification("Error updating aliases", "error"));
      }
    });
  };

  const handleRetrieveGraceDB = () => {
    dispatch(gcnEventActions.postGcnGraceDB(gcnEvent.dateobs)).then(
      (response) => {
        if (response.status === "success") {
          dispatch(
            showNotification("GraceDB retrieval started. Please wait..."),
          );
        } else {
          dispatch(showNotification("Error retrieving GraceDB", "error"));
        }
      },
    );
  };

  return (
    <div>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <div className={styles.columnItem}>
            <Grid container spacing={2}>
              <Grid item xs={9}>
                <Grid container>
                  <Grid item md={12} lg={4}>
                    <Grid container alignItems="end" spacing={1}>
                      <Grid item>
                        <span className={styles.headerName}>
                          {dayjs(gcnEvent.dateobs).format("YYMMDD HH:mm:ss")}
                        </span>
                      </Grid>
                      <Grid item>
                        <span className={styles.headerDate}>
                          ({dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))})
                        </span>
                      </Grid>
                    </Grid>
                  </Grid>
                  <Grid item md={12} lg={8}>
                    <GcnTags gcnEvent={gcnEvent} />
                  </Grid>
                </Grid>
              </Grid>
              <Grid item xs={3}>
                <div className={styles.headerButtons}>
                  <Button
                    secondary
                    onClick={() => setLeftPanelVisible(!leftPanelVisible)}
                    data-testid="left-panel-button"
                    style={{
                      fontSize: isMobile ? "0.7rem" : "0.85rem",
                      marginRight: isMobile ? "1rem" : "0rem",
                    }}
                  >
                    Interactions
                  </Button>
                  <Button
                    secondary
                    onClick={() => setRightPanelVisible(!rightPanelVisible)}
                    data-testid="right-panel-button"
                    style={{
                      fontSize: isMobile ? "0.7rem" : "0.85rem",
                      marginRight: isMobile ? "1rem" : "0rem",
                    }}
                  >
                    Properties
                  </Button>
                </div>
              </Grid>
            </Grid>
            <GcnEventAllocationTriggers
              gcnEvent={gcnEvent}
              showPassed
              showUnset
              // we want to show the title if the breakpoint is over md
              showTitle={!isMobile}
            />
            <GcnAliases gcnEvent={gcnEvent} show_title />
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
                      <GcnSelectionForm dateobs={route.dateobs} />
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
          sm={12}
          md={8}
          lg={6}
          className={styles.sidePanel}
        >
          <DialogTitle disableTypography>
            <IconButton onClick={toggleDrawer("left", false)}>
              <Cancel />
            </IconButton>
          </DialogTitle>
          <div className={styles.sidePanelContent}>
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
                    <Suspense fallback={<CircularProgress />}>
                      <CommentList
                        associatedResourceType="gcn_event"
                        gcnEventID={gcnEvent.id}
                        maxHeightList="60vh"
                      />
                    </Suspense>
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
          sm={12}
          md={8}
          lg={6}
          className={styles.sidePanel}
        >
          <DialogTitle disableTypography>
            <IconButton onClick={toggleDrawer("right", false)}>
              <Cancel />
            </IconButton>
          </DialogTitle>
          <div className={styles.sidePanelContent}>
            <Grid container spacing={2}>
              {/* event properties */}
              <Grid item xs={12}>
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
                    <GcnProperties properties={gcnEvent.properties} />
                  </AccordionDetails>
                </Accordion>
              </Grid>
              {/* localization properties */}
              <Grid item xs={12}>
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
                    <GcnLocalizationsTable
                      localizations={gcnEvent.localizations}
                    />
                  </AccordionDetails>
                </Accordion>
              </Grid>
              <Grid item sm={12} lg={6}>
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
                      {route?.dateobs === gcnEvent?.dateobs &&
                      route?.dateobs ? (
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
              </Grid>
              <Grid item sm={12} lg={6}>
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
                                      "warning",
                                    ),
                                  );
                                  dispatch(
                                    postLocalizationFromNotice({
                                      dateobs: gcn_notice.dateobs,
                                      noticeID: gcn_notice.id,
                                    }),
                                  ).then((response) => {
                                    if (response.status === "success") {
                                      dispatch(
                                        showNotification(
                                          `Localization successfully ingested from notice ${gcn_notice.id}. Please wait for the contour to be generated. Default observation plans will be created shortly.`,
                                        ),
                                      );
                                    } else {
                                      dispatch(
                                        showNotification(
                                          `Error ingesting localization from notice ${gcn_notice.id}. It might not be available yet.`,
                                          "error",
                                        ),
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
              </Grid>
              <Grid item sm={12} lg={6}>
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
              </Grid>
              <Grid item sm={12} lg={6}>
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
              </Grid>
              <Grid item sm={12} lg={6}>
                <Accordion defaultExpanded>
                  <AccordionSummary
                    expandIcon={<ExpandMoreIcon />}
                    aria-controls="gcnEvent-content"
                    id="gracedb-header"
                  >
                    <Typography className={styles.accordionHeading}>
                      GraceDB
                    </Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <div className={styles.gcnEventContainer}>
                      <DisplayGraceDB gcnEvent={gcnEvent} />
                    </div>
                    {permission && (
                      <Button
                        secondary
                        onClick={() => handleRetrieveGraceDB()}
                        data-testid="retrieve-gracedb"
                      >
                        Retrieve
                      </Button>
                    )}
                  </AccordionDetails>
                </Accordion>
              </Grid>
            </Grid>
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
