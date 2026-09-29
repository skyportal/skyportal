import { useGetProfileQuery } from "../../ducks/profile";
import React, { useState } from "react";
import { skipToken } from "@reduxjs/toolkit/query";
import { useAppDispatch } from "../../types/hooks";

import Cancel from "@mui/icons-material/Cancel";
import GetAppIcon from "@mui/icons-material/GetApp";
import LocationOffOutlined from "@mui/icons-material/LocationOffOutlined";
import useMediaQuery from "@mui/material/useMediaQuery";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import { useTheme } from "@mui/material/styles";
import Typography from "@mui/material/Typography";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";

import {
  useGetGcnEventQuery,
  useGetGcnTachQuery,
  usePostGcnTachMutation,
  usePostGcnGraceDBMutation,
  useUpdateGcnEventMutation,
} from "../../ducks/gcnEvent";

import GcnSelectionForm from "./GcnSelectionForm";
import Spinner from "../Spinner";

import ObservationPlanRequestForm from "../observation_plan/ObservationPlanRequestForm";
import ObservationPlanRequestLists from "../observation_plan/ObservationPlanRequestLists";
import AnalysisList from "../analysis/AnalysisList";
import AnalysisForm from "../analysis/AnalysisForm";

import { useCommentTarget } from "../../contexts/CommentPanelContext";
import DisplayGraceDB from "./DisplayGraceDB";
import GcnAdvocates from "./GcnAdvocates";
import GcnAliases from "./GcnAliases";
import GcnCirculars from "./GcnCirculars";
import GcnEventAllocationTriggers from "./GcnEventAllocationTriggers";
import GcnEventAssociationSummary from "./GcnEventAssociationSummary";
import GenerateGcnEventSummary from "./GenerateGcnEventSummary";
import ShowSummaries from "../summary/ShowSummaries";
import ShowSummaryHistory from "../summary/ShowSummaryHistory";
import UpdateSummary from "../summary/UpdateSummary";
import GcnLocalizationsTable from "./GcnLocalizationsTable";
import GcnProperties from "./GcnProperties";
import GcnTags from "./GcnTags";
import Reminders from "../Reminders";

import { usePostLocalizationFromNoticeMutation } from "../../ducks/localization";
import withRouter from "../withRouter";
import Paper from "../Paper";

dayjs.extend(utc);

interface PropertiesSectionProps {
  title: string;
  size?: number | Record<string, number>;
  children: React.ReactNode;
}

const PropertiesSection = ({
  title,
  size = 12,
  children,
}: PropertiesSectionProps) => (
  <Grid size={size}>
    <Paper>
      <Typography variant="h6">{title}</Typography>
      {children}
    </Paper>
  </Grid>
);

const noLocalization = (
  <Stack
    spacing={0.5}
    sx={{ alignItems: "center", textAlign: "center", py: 3 }}
  >
    <LocationOffOutlined sx={{ fontSize: 36, color: "text.disabled" }} />
    <Typography variant="subtitle1" sx={{ color: "text.secondary" }}>
      No localization available yet
    </Typography>
    <Typography variant="body2" sx={{ color: "text.disabled", maxWidth: 480 }}>
      Some only become available with later notices. You can try ingesting one
      from the GCN Notices section of the Properties panel.
    </Typography>
  </Stack>
);

interface GcnEventPageProps {
  route: {
    dateobs?: string;
  };
}

const GcnEventPage = ({ route }: GcnEventPageProps) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const dispatch = useAppDispatch();
  const [updateGcnEvent] = useUpdateGcnEventMutation();
  const dateobs = route?.dateobs;
  const { data: gcnEventData } = useGetGcnEventQuery(dateobs ?? skipToken) as {
    data: any;
  };
  const { data: tachData } = useGetGcnTachQuery(dateobs ?? skipToken);
  const gcnEvent = gcnEventData && {
    ...gcnEventData,
    circulars: tachData?.circulars,
  };
  const [postTach] = usePostGcnTachMutation();
  const [postGraceDB] = usePostGcnGraceDBMutation();
  const [postLocalizationFromNotice] = usePostLocalizationFromNoticeMutation();
  const { data: currentUser } = useGetProfileQuery();
  const permission =
    currentUser?.permissions?.includes("System admin") ||
    currentUser?.permissions?.includes("Manage GCNs");
  const [rightPanelVisible, setRightPanelVisible] = useState(false);
  useCommentTarget(
    gcnEvent?.id && gcnEvent?.dateobs === dateobs
      ? { type: "gcn_event", id: gcnEvent.id, dateobs: gcnEvent.dateobs }
      : null,
  );

  if (!dateobs || gcnEvent?.dateobs !== dateobs) return <Spinner />;

  const updateAliasesCirculars = permission && (
    <Button
      secondary
      data-testid="update-aliases"
      onClick={() =>
        postTach(dateobs)
          .unwrap()
          .then(() => {
            dispatch(
              showNotification(
                "Aliases and Circulars update started. Please wait...",
              ),
            );
            if (gcnEvent.aliases?.length === 0) {
              dispatch(
                showNotification(
                  "This has never been done for this event before. It may take few minutes.",
                  "warning",
                ),
              );
            }
          })
          .catch(() =>
            dispatch(showNotification("Error updating aliases", "error")),
          )
      }
    >
      Update
    </Button>
  );

  return (
    <>
      <Stack spacing={1}>
        <Grid container spacing={2}>
          <Grid size={9}>
            <Grid container>
              <Grid size={{ md: 12, lg: 4 }}>
                <Grid container spacing={1} sx={{ alignItems: "end" }}>
                  <Box
                    component="span"
                    data-testid="tour-gcn-header"
                    sx={{
                      height: "2rem",
                      fontSize: "2rem",
                      fontWeight: "bold",
                      lineHeight: "1.7rem",
                      color: "primary.main",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {dayjs(gcnEvent.dateobs).format("YYMMDD HH:mm:ss")}
                  </Box>
                  <Box
                    component="span"
                    sx={{ height: "1rem", whiteSpace: "nowrap" }}
                  >
                    ({dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))})
                  </Box>
                </Grid>
              </Grid>
              <Grid size={{ md: 12, lg: 8 }}>
                <GcnTags gcnEvent={gcnEvent} />
              </Grid>
            </Grid>
          </Grid>
          <Grid
            size={3}
            sx={{
              display: "flex",
              justifyContent: "flex-end",
              alignItems: "flex-start",
            }}
          >
            <Button
              secondary
              onClick={() => setRightPanelVisible(!rightPanelVisible)}
              data-testid="right-panel-button"
              sx={{ fontSize: isMobile ? "0.7rem" : "0.85rem" }}
            >
              Properties
            </Button>
          </Grid>
        </Grid>
        <GcnEventAllocationTriggers
          gcnEvent={gcnEvent}
          showPassed
          showUnset
          showTitle={!isMobile}
        />
        <GcnEventAssociationSummary dateobs={dateobs} />
        <Paper
          sx={{ p: gcnEvent.summary ? "0.25rem 0.25rem 0 0.25rem" : "0.5rem" }}
          variant={gcnEvent.summary ? "outlined" : undefined}
        >
          <ShowSummaries summaries={gcnEvent.summary_history || []} />
          <Box
            sx={{
              display: "flex",
              justifyContent: gcnEvent.summary ? "flex-end" : "space-between",
              alignItems: "center",
            }}
          >
            {!gcnEvent.summary && (
              <Typography variant="body2" sx={{ color: "text.disabled" }}>
                No summary yet.
              </Typography>
            )}
            <Box sx={{ display: "flex", alignItems: "center" }}>
              {permission && (
                <>
                  <UpdateSummary
                    summary={gcnEvent.summary}
                    summaryHistory={gcnEvent.summary_history}
                    onSave={async (summary) => {
                      await updateGcnEvent({
                        dateobs,
                        payload: { summary },
                      }).unwrap();
                      dispatch(
                        showNotification("Event summary successfully updated."),
                      );
                    }}
                  />
                  <GenerateGcnEventSummary dateobs={dateobs} />
                </>
              )}
              {gcnEvent.summary_history?.length > 0 && (
                <ShowSummaryHistory
                  summaries={gcnEvent.summary_history}
                  label={dateobs}
                />
              )}
            </Box>
          </Box>
        </Paper>
        <GcnAliases gcnEvent={gcnEvent} show_title />
        <GcnAdvocates gcnEvent={gcnEvent} show_title />
        <Paper>
          <Typography variant="h6">Analysis</Typography>
          {gcnEvent.localizations?.length > 0 ? (
            <GcnSelectionForm dateobs={dateobs} />
          ) : (
            noLocalization
          )}
        </Paper>
        <Paper>
          <Typography variant="h6" data-testid="tour-gcn-obsplan">
            Observation Plans
          </Typography>
          {gcnEvent.localizations?.length > 0 ? (
            <>
              <ObservationPlanRequestForm dateobs={dateobs} />
              <ObservationPlanRequestLists dateobs={dateobs} />
            </>
          ) : (
            noLocalization
          )}
        </Paper>
      </Stack>
      <Drawer
        anchor="right"
        open={rightPanelVisible}
        onClose={() => setRightPanelVisible(false)}
        slotProps={{ paper: { sx: { width: "100%" } } }}
      >
        <DialogTitle>
          <IconButton onClick={() => setRightPanelVisible(false)}>
            <Cancel />
          </IconButton>
        </DialogTitle>
        <Grid container spacing={2} sx={{ p: 2 }}>
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
          <Grid size={12}>
            <Typography variant="h6">Analyses</Typography>
            <AnalysisForm obj_id={dateobs} analysisResourceType="gcn_event" />
            <AnalysisList obj_id={dateobs} analysisResourceType="gcn_event" />
          </Grid>
          <PropertiesSection title="Light curve" size={{ sm: 12, lg: 6 }}>
            {gcnEvent.lightcurve && (
              <img src={gcnEvent.lightcurve} alt="loading..." />
            )}
          </PropertiesSection>
          <PropertiesSection title="GCN Notices" size={{ sm: 12, lg: 6 }}>
            <Stack
              divider={<Divider />}
              spacing={1}
              sx={{ overflow: "hidden" }}
            >
              {gcnEvent.gcn_notices?.map((gcn_notice: any) => (
                <Box key={gcn_notice.ivorn}>
                  <Box sx={{ display: "flex", alignItems: "center" }}>
                    <Chip
                      size="small"
                      label={gcn_notice.ivorn}
                      sx={{ width: "100%" }}
                    />
                    <IconButton
                      href={`/api/gcn_event/${gcn_notice.dateobs}/notice/${gcn_notice.id}/download`}
                      download
                      size="large"
                      target="_blank"
                    >
                      <GetAppIcon />
                    </IconButton>
                  </Box>
                  {gcn_notice.has_localization &&
                    gcn_notice.localization_ingested === false && (
                      <Button
                        secondary
                        onClick={() => {
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
                            .then(() =>
                              dispatch(
                                showNotification(
                                  `Localization successfully ingested from notice ${gcn_notice.id}. Please wait for the contour to be generated. Default observation plans will be created shortly.`,
                                ),
                              ),
                            )
                            .catch(() =>
                              dispatch(
                                showNotification(
                                  `Error ingesting localization from notice ${gcn_notice.id}. It might not be available yet.`,
                                  "error",
                                ),
                              ),
                            );
                        }}
                      >
                        Ingest Localization
                      </Button>
                    )}
                </Box>
              ))}
            </Stack>
          </PropertiesSection>
          <PropertiesSection title="GCN Aliases" size={{ sm: 12, lg: 6 }}>
            <GcnAliases gcnEvent={gcnEvent} />
            {updateAliasesCirculars}
          </PropertiesSection>
          <PropertiesSection title="GCN Circulars" size={{ sm: 12, lg: 6 }}>
            <GcnCirculars gcnEvent={gcnEvent} />
            {updateAliasesCirculars}
          </PropertiesSection>
          <PropertiesSection title="GraceDB" size={{ sm: 12, lg: 6 }}>
            <DisplayGraceDB gcnEvent={gcnEvent} />
            {permission && (
              <Button
                secondary
                onClick={() =>
                  postGraceDB(dateobs)
                    .unwrap()
                    .then(() =>
                      dispatch(
                        showNotification(
                          "GraceDB retrieval started. Please wait...",
                        ),
                      ),
                    )
                    .catch(() =>
                      dispatch(
                        showNotification("Error retrieving GraceDB", "error"),
                      ),
                    )
                }
              >
                Retrieve
              </Button>
            )}
          </PropertiesSection>
        </Grid>
      </Drawer>
    </>
  );
};

export default withRouter(GcnEventPage);
