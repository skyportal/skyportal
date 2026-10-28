import { useGetProfileQuery } from "../../ducks/profile";
import React, { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { skipToken } from "@reduxjs/toolkit/query";
import { useAppDispatch } from "../../types/hooks";

import GetAppIcon from "@mui/icons-material/GetApp";
import LocationOffOutlined from "@mui/icons-material/LocationOffOutlined";
import useMediaQuery from "@mui/material/useMediaQuery";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Grid from "@mui/material/Grid";
import IconButton from "@mui/material/IconButton";
import Link from "@mui/material/Link";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import { useTheme } from "@mui/material/styles";
import Tooltip from "@mui/material/Tooltip";
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

const slug = (title: string) => title.toLowerCase().replace(/\s+/g, "-");

interface PropertiesSectionProps {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}

const PropertiesSection = ({
  title,
  action,
  children,
}: PropertiesSectionProps) => (
  <Paper>
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        mb: 1,
      }}
    >
      <Typography variant="h6">{title}</Typography>
      {action}
    </Box>
    {children}
  </Paper>
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
      from the External data tab.
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
  const [searchParams, setSearchParams] = useSearchParams();
  const [failedLightcurve, setFailedLightcurve] = useState<string | null>(null);
  useCommentTarget(
    gcnEvent?.id && gcnEvent?.dateobs === dateobs
      ? { type: "gcn_event", id: gcnEvent.id, dateobs: gcnEvent.dateobs }
      : null,
  );

  if (!dateobs || gcnEvent?.dateobs !== dateobs) return <Spinner />;

  const updateAliasesCirculars = permission && (
    <Button
      size="small"
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

  const ingestLocalization = (notice: any) => {
    dispatch(
      showNotification(
        `Starting ingestion attempt for localization from notice ${notice.id}. Please wait...`,
        "warning",
      ),
    );
    postLocalizationFromNotice({ dateobs: notice.dateobs, noticeID: notice.id })
      .unwrap()
      .then(() =>
        dispatch(
          showNotification(
            `Localization successfully ingested from notice ${notice.id}. Please wait for the contour to be generated. Default observation plans will be created shortly.`,
          ),
        ),
      )
      .catch(() =>
        dispatch(
          showNotification(
            `Error ingesting localization from notice ${notice.id}. It might not be available yet.`,
            "error",
          ),
        ),
      );
  };

  const retrieveGraceDB = () =>
    postGraceDB(dateobs)
      .unwrap()
      .then(() =>
        dispatch(showNotification("GraceDB retrieval started. Please wait...")),
      )
      .catch(() =>
        dispatch(showNotification("Error retrieving GraceDB", "error")),
      );

  const isGW =
    gcnEvent.aliases?.some((alias: string) => alias.startsWith("LVC#")) ||
    Object.keys(gcnEvent.gracedb_labels ?? {}).length > 0;

  const tabs = [
    {
      title: "Overview",
      content: (
        <Stack spacing={1}>
          <GcnEventAllocationTriggers
            gcnEvent={gcnEvent}
            showPassed
            showUnset
            showTitle={!isMobile}
          />
          <GcnEventAssociationSummary dateobs={dateobs} />
          <Paper
            sx={{
              p: gcnEvent.summary ? "0.25rem 0.25rem 0 0.25rem" : "0.5rem",
            }}
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
                          showNotification(
                            "Event summary successfully updated.",
                          ),
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
      ),
    },
    {
      title: "Properties",
      content: <GcnProperties properties={gcnEvent.properties} />,
    },
    {
      title: "Localizations",
      content: <GcnLocalizationsTable localizations={gcnEvent.localizations} />,
    },
    {
      title: "Reminders",
      content: (
        <Reminders
          resourceId={gcnEvent.id.toString()}
          resourceType="gcn_event"
        />
      ),
    },
    {
      title: "Analyses",
      content: (
        <Grid container spacing={2}>
          <Grid size={12}>
            <Paper>
              <AnalysisList obj_id={dateobs} analysisResourceType="gcn_event" />
            </Paper>
          </Grid>
          <Grid size={12}>
            <Paper>
              <AnalysisForm obj_id={dateobs} analysisResourceType="gcn_event" />
            </Paper>
          </Grid>
        </Grid>
      ),
    },
    {
      title: "External data",
      content: (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, lg: 6 }}>
            <Stack spacing={2}>
              <PropertiesSection title="GCN Notices">
                <Stack divider={<Divider />} spacing={1}>
                  {gcnEvent.gcn_notices?.map((notice: any) => (
                    <Box
                      key={notice.id}
                      sx={{ display: "flex", alignItems: "center", gap: 1 }}
                    >
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="body2">
                          {notice.notice_type}
                        </Typography>
                        <Typography
                          variant="caption"
                          sx={{
                            display: "block",
                            color: "text.secondary",
                            wordBreak: "break-all",
                          }}
                        >
                          {dayjs.utc(notice.date).format("YYYY-MM-DD HH:mm:ss")}{" "}
                          UTC · {notice.ivorn}
                        </Typography>
                      </Box>
                      {notice.has_localization &&
                        notice.localization_ingested === false && (
                          <Button
                            size="small"
                            onClick={() => ingestLocalization(notice)}
                          >
                            Ingest localization
                          </Button>
                        )}
                      <Tooltip title="Download notice">
                        <IconButton
                          href={`/api/gcn_event/${notice.dateobs}/notice/${notice.id}/download`}
                          download
                          size="small"
                          target="_blank"
                        >
                          <GetAppIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  ))}
                </Stack>
              </PropertiesSection>
              {gcnEvent.lightcurve && (
                <PropertiesSection title="Light curve">
                  {failedLightcurve === gcnEvent.lightcurve ? (
                    <Typography
                      variant="body2"
                      sx={{ color: "text.secondary" }}
                    >
                      HEASARC is unreachable, try again later.{" "}
                      <Link
                        href={gcnEvent.lightcurve}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open link
                      </Link>
                    </Typography>
                  ) : (
                    <Box
                      component="img"
                      src={gcnEvent.lightcurve}
                      alt="Light curve"
                      onError={() => setFailedLightcurve(gcnEvent.lightcurve)}
                      sx={{ maxWidth: "100%" }}
                    />
                  )}
                </PropertiesSection>
              )}
            </Stack>
          </Grid>
          <Grid size={{ xs: 12, lg: 6 }}>
            <Stack spacing={2}>
              <PropertiesSection
                title="GCN Circulars"
                action={updateAliasesCirculars}
              >
                <GcnCirculars gcnEvent={gcnEvent} />
              </PropertiesSection>
              {isGW && (
                <PropertiesSection
                  title="GraceDB"
                  action={
                    permission && (
                      <Button size="small" onClick={retrieveGraceDB}>
                        Retrieve
                      </Button>
                    )
                  }
                >
                  <DisplayGraceDB gcnEvent={gcnEvent} />
                </PropertiesSection>
              )}
            </Stack>
          </Grid>
        </Grid>
      ),
    },
  ];
  const current =
    tabs.find(({ title }) => slug(title) === searchParams.get("tab")) ??
    tabs[0]!;

  return (
    <Stack spacing={1}>
      <Stack spacing={0.5}>
        <Box sx={{ display: "flex", alignItems: "baseline", gap: 1.5 }}>
          <Box
            data-testid="tour-gcn-header"
            sx={{
              fontSize: "2rem",
              fontWeight: "bold",
              lineHeight: 1.1,
              color: "primary.main",
              whiteSpace: "nowrap",
            }}
          >
            {dayjs(gcnEvent.dateobs).format("YYMMDD HH:mm:ss")}
          </Box>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            {dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))}
          </Typography>
        </Box>
        <GcnTags gcnEvent={gcnEvent} />
      </Stack>
      <Tabs
        value={slug(current.title)}
        onChange={(_, value) =>
          setSearchParams({ tab: value }, { replace: true })
        }
        variant="scrollable"
        sx={{ borderBottom: 1, borderColor: "divider" }}
      >
        {tabs.map(({ title }) => (
          <Tab
            key={title}
            value={slug(title)}
            label={title}
            data-testid={`${slug(title)}-tab`}
          />
        ))}
      </Tabs>
      {current.content}
    </Stack>
  );
};

export default withRouter(GcnEventPage);
