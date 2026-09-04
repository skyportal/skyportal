import { useGetProfileQuery } from "../../ducks/profile";
import React, { useState } from "react";
import { skipToken } from "@reduxjs/toolkit/query";
import { useAppDispatch } from "../../types/hooks";

import Cancel from "@mui/icons-material/Cancel";
import GetAppIcon from "@mui/icons-material/GetApp";
import useMediaQuery from "@mui/material/useMediaQuery";
import Chip from "@mui/material/Chip";
import DialogTitle from "@mui/material/DialogTitle";
import Drawer from "@mui/material/Drawer";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import { useTheme } from "@mui/material/styles";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import {
  useGetGcnEventQuery,
  useGetGcnTachQuery,
  usePostGcnTachMutation,
  usePostGcnGraceDBMutation,
} from "../../ducks/gcnEvent";

import GcnSelectionForm from "./GcnSelectionForm";
import Spinner from "../Spinner";

import ObservationPlanRequestForm from "../observation_plan/ObservationPlanRequestForm";
import ObservationPlanRequestLists from "../observation_plan/ObservationPlanRequestLists";

import CommentPanel from "../comment/CommentPanel";
import DisplayGraceDB from "./DisplayGraceDB";
import GcnAdvocates from "./GcnAdvocates";
import GcnAliases from "./GcnAliases";
import GcnCirculars from "./GcnCirculars";
import GcnEventAllocationTriggers from "./GcnEventAllocationTriggers";
import GcnEventAssociationSummary from "./GcnEventAssociationSummary";
import UpdateGcnEventSummary from "./UpdateGcnEventSummary";
import GenerateGcnEventSummary from "./GenerateGcnEventSummary";
import ShowSummaries from "../summary/ShowSummaries";
import ShowSummaryHistory from "../summary/ShowSummaryHistory";
import GcnLocalizationsTable from "./GcnLocalizationsTable";
import GcnProperties from "./GcnProperties";
import GcnTags from "./GcnTags";
import Reminders from "../Reminders";

import { usePostLocalizationFromNoticeMutation } from "../../ducks/localization";
import withRouter from "../withRouter";
import Paper from "../Paper";

dayjs.extend(utc);

const useStyles = makeStyles()((theme) => ({
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
    display: "flex",
    justifyContent: "flex-end",
    gap: "0.5rem",
  },
  sectionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
  gcnEventContainer: {
    display: "flex",
    overflow: "hidden",
    flexDirection: "column",
  },
  columnItem: {
    marginBottom: theme.spacing(1),
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

interface PropertiesSectionProps {
  title: string;
  size?: number | Record<string, number>;
  children: React.ReactNode;
}

const PropertiesSection = ({
  title,
  size = 12,
  children,
}: PropertiesSectionProps) => {
  const { classes: styles } = useStyles();
  return (
    <Grid size={size}>
      <Paper>
        <Typography className={styles.sectionHeading}>{title}</Typography>
        {children}
      </Paper>
    </Grid>
  );
};

interface DownloadNoticeButtonProps {
  gcn_notice: {
    dateobs?: string;
    id?: number;
    [key: string]: any;
  };
}

const noLocalization = (
  <>
    <Typography variant="body2">
      No localization available for this event (yet). Some localizations are
      available after the notices.
    </Typography>
    <Typography variant="body2">
      You can try ingesting the localization from the Notices menu on the right
      of this page
    </Typography>
  </>
);

const DownloadNoticeButton = ({ gcn_notice }: DownloadNoticeButtonProps) => {
  return (
    <IconButton
      href={`/api/gcn_event/${gcn_notice.dateobs}/notice/${gcn_notice.id}/download`}
      download
      size="large"
      target="_blank"
    >
      <GetAppIcon />
    </IconButton>
  );
};

interface GcnEventPageProps {
  route: {
    dateobs?: string;
  };
}

const GcnEventPage = ({ route }: GcnEventPageProps) => {
  const theme = useTheme();
  const { classes: styles } = useStyles();

  const dispatch = useAppDispatch();
  const { data: gcnEventData } = useGetGcnEventQuery(
    route?.dateobs ?? skipToken,
  ) as { data: any };
  const { data: tachData } = useGetGcnTachQuery(
    route?.dateobs ?? skipToken,
  ) as {
    data: any;
  };
  // Recompose the single `gcnEvent` object the old store slice exposed: the
  // main event payload merged with the tach circulars sub-fetch.
  const gcnEvent = gcnEventData
    ? { ...gcnEventData, circulars: tachData?.circulars }
    : gcnEventData;
  const [postTach] = usePostGcnTachMutation();
  const [postGraceDB] = usePostGcnGraceDBMutation();
  const [postLocalizationFromNotice] = usePostLocalizationFromNoticeMutation();
  const { data: currentUser } = useGetProfileQuery();
  const permission =
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes("Manage GCNs");

  const [rightPanelVisible, setRightPanelVisible] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  const toggleDrawer = (open: boolean) => (event: any) => {
    if (
      event.type === "keydown" &&
      (event.key === "Tab" || event.key === "Shift")
    ) {
      return;
    }
    setRightPanelVisible(open);
  };

  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  const dateobs = route?.dateobs;
  if (!dateobs || gcnEvent?.dateobs !== dateobs) {
    return <Spinner />;
  }

  const handleUpdateAliasesCirculars = () => {
    postTach(gcnEvent.dateobs)
      .unwrap()
      .then(() => {
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
      })
      .catch(() => {
        dispatch(showNotification("Error updating aliases", "error"));
      });
  };

  const handleIngestLocalization = (gcn_notice: any) => {
    dispatch(
      showNotification(
        `Starting ingestion attempt for localization from notice ${gcn_notice.id}. Please wait...`,
        "warning",
      ),
    );
    postLocalizationFromNotice({
      dateobs: gcn_notice.dateobs,
      noticeID: gcn_notice.id,
    })
      .unwrap()
      .then(() => {
        dispatch(
          showNotification(
            `Localization successfully ingested from notice ${gcn_notice.id}. Please wait for the contour to be generated. Default observation plans will be created shortly.`,
          ),
        );
      })
      .catch(() => {
        dispatch(
          showNotification(
            `Error ingesting localization from notice ${gcn_notice.id}. It might not be available yet.`,
            "error",
          ),
        );
      });
  };

  const handleRetrieveGraceDB = () => {
    postGraceDB(gcnEvent.dateobs)
      .unwrap()
      .then(() => {
        dispatch(showNotification("GraceDB retrieval started. Please wait..."));
      })
      .catch(() => {
        dispatch(showNotification("Error retrieving GraceDB", "error"));
      });
  };

  return (
    <div>
      <Grid container spacing={2}>
        <Grid size={12}>
          <div className={styles.columnItem}>
            <Grid container spacing={2}>
              <Grid size={9}>
                <Grid container>
                  <Grid size={{ md: 12, lg: 4 }}>
                    <Grid
                      container
                      spacing={1}
                      sx={{
                        alignItems: "end",
                      }}
                    >
                      <Grid>
                        <span
                          className={styles.headerName}
                          data-testid="tour-gcn-header"
                        >
                          {dayjs(gcnEvent.dateobs).format("YYMMDD HH:mm:ss")}
                        </span>
                      </Grid>
                      <Grid>
                        <span className={styles.headerDate}>
                          ({dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))})
                        </span>
                      </Grid>
                    </Grid>
                  </Grid>
                  <Grid size={{ md: 12, lg: 8 }}>
                    <GcnTags gcnEvent={gcnEvent} />
                  </Grid>
                </Grid>
              </Grid>
              <Grid size={3}>
                <div className={styles.headerButtons}>
                  <Button
                    secondary
                    onClick={() => setRightPanelVisible(!rightPanelVisible)}
                    data-testid="right-panel-button"
                    style={{ fontSize: isMobile ? "0.7rem" : "0.85rem" }}
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
            <GcnEventAssociationSummary dateobs={dateobs} />
            <Paper
              style={{
                marginTop: "0.5rem",
                padding: gcnEvent.summary
                  ? "0.25rem 0.25rem 0 0.25rem"
                  : "0.5rem",
              }}
              variant={gcnEvent.summary ? "outlined" : undefined}
            >
              <ShowSummaries summaries={gcnEvent.summary_history || []} />
              <div
                style={{
                  display: "flex",
                  flexDirection: "row",
                  justifyContent: gcnEvent.summary
                    ? "flex-end"
                    : "space-between",
                  alignItems: "center",
                  width: "100%",
                }}
              >
                {!gcnEvent.summary && (
                  <p style={{ fontSize: "0.75rem", color: "grey", margin: 0 }}>
                    No summary yet.
                  </p>
                )}
                <div style={{ display: "flex", alignItems: "center" }}>
                  {permission && (
                    <UpdateGcnEventSummary
                      dateobs={dateobs}
                      summary={gcnEvent.summary}
                      summaryHistory={gcnEvent.summary_history}
                    />
                  )}
                  {permission && <GenerateGcnEventSummary dateobs={dateobs} />}
                  {gcnEvent.summary_history?.length > 0 && (
                    <ShowSummaryHistory
                      summaries={gcnEvent.summary_history}
                      label={dateobs}
                    />
                  )}
                </div>
              </div>
            </Paper>
            <GcnAliases gcnEvent={gcnEvent} show_title />
            <GcnAdvocates gcnEvent={gcnEvent} show_title />
          </div>
          <div className={styles.columnItem}>
            <Paper>
              <Typography className={styles.sectionHeading}>
                Analysis
              </Typography>
              {gcnEvent.localizations?.length > 0 ? (
                <GcnSelectionForm dateobs={dateobs} />
              ) : (
                noLocalization
              )}
            </Paper>
          </div>
          <div className={styles.columnItem}>
            <Paper>
              <Typography
                className={styles.sectionHeading}
                data-testid="tour-gcn-obsplan"
              >
                Observation Plans
              </Typography>
              {gcnEvent.localizations?.length > 0 ? (
                <>
                  <ObservationPlanRequestForm
                    {...({ dateobs, action: "createNew" } as any)}
                  />
                  <ObservationPlanRequestLists {...({ dateobs } as any)} />
                </>
              ) : (
                noLocalization
              )}
            </Paper>
          </div>
        </Grid>
      </Grid>
      <React.Fragment key="right">
        <Drawer
          anchor="right"
          open={rightPanelVisible}
          onClose={toggleDrawer(false)}
          className={styles.sidePanel}
        >
          <DialogTitle>
            <IconButton onClick={toggleDrawer(false)}>
              <Cancel />
            </IconButton>
          </DialogTitle>
          <div className={styles.sidePanelContent}>
            <Grid container spacing={2}>
              <Grid size={12}>
                <GcnProperties properties={gcnEvent.properties} />
              </Grid>
              <Grid size={12}>
                <GcnLocalizationsTable localizations={gcnEvent.localizations} />
              </Grid>
              <Grid size={12}>
                <Reminders
                  resourceId={gcnEvent.id.toString()}
                  resourceType="gcn_event"
                />
              </Grid>
              <PropertiesSection title="Light curve" size={{ sm: 12, lg: 6 }}>
                {gcnEvent.lightcurve && (
                  <img src={gcnEvent.lightcurve} alt="loading..." />
                )}
              </PropertiesSection>
              <PropertiesSection title="GCN Notices" size={{ sm: 12, lg: 6 }}>
                <div className={styles.gcnEventContainer}>
                  {gcnEvent.gcn_notices?.map((gcn_notice: any) => (
                    <li
                      key={gcn_notice.ivorn}
                      className={styles.noticeListElement}
                    >
                      <div className={styles.noticeListElementHeader}>
                        <Chip
                          size="small"
                          label={gcn_notice.ivorn}
                          className={styles.noticeListElementIVORN}
                        />
                        <DownloadNoticeButton gcn_notice={gcn_notice} />
                      </div>
                      {gcn_notice?.has_localization &&
                        gcn_notice?.localization_ingested === false && (
                          <Button
                            secondary
                            onClick={() => handleIngestLocalization(gcn_notice)}
                            data-testid="ingest-localization-from-notice"
                          >
                            Ingest Localization
                          </Button>
                        )}
                      <div className={styles.noticeListDivider} />
                    </li>
                  ))}
                </div>
              </PropertiesSection>
              <PropertiesSection title="GCN Aliases" size={{ sm: 12, lg: 6 }}>
                <GcnAliases gcnEvent={gcnEvent} />
                {permission && (
                  <Button
                    secondary
                    onClick={() => handleUpdateAliasesCirculars()}
                    data-testid="update-aliases"
                  >
                    Update
                  </Button>
                )}
              </PropertiesSection>
              <PropertiesSection title="GCN Circulars" size={{ sm: 12, lg: 6 }}>
                <GcnCirculars gcnEvent={gcnEvent} />
                {permission && (
                  <Button
                    secondary
                    onClick={() => handleUpdateAliasesCirculars()}
                    data-testid="update-circulars"
                  >
                    Update
                  </Button>
                )}
              </PropertiesSection>
              <PropertiesSection title="GraceDB" size={{ sm: 12, lg: 6 }}>
                <DisplayGraceDB gcnEvent={gcnEvent} />
                {permission && (
                  <Button
                    secondary
                    onClick={() => handleRetrieveGraceDB()}
                    data-testid="retrieve-gracedb"
                  >
                    Retrieve
                  </Button>
                )}
              </PropertiesSection>
            </Grid>
          </div>
        </Drawer>
      </React.Fragment>
      <CommentPanel
        target={{ type: "gcn_event", id: gcnEvent.id, dateobs }}
        inline={false}
        open={chatOpen}
        setOpen={setChatOpen}
      />
    </div>
  );
};

export default withRouter(GcnEventPage);
