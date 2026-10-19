import { Suspense, lazy, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import MuiLink from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowDownward from "@mui/icons-material/ArrowDownward";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import ArrowUpward from "@mui/icons-material/ArrowUpward";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import SortIcon from "@mui/icons-material/Sort";
import { Link } from "react-router-dom";
import { ViewportList } from "react-viewport-list";

import { showNotification } from "baselayer/components/Notifications";
import {
  useGetProfileQuery,
  useIsReadOnly,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import {
  setCandidatesAnnotationSortOptions,
  useGetCandidatesQuery,
} from "../../ducks/candidate/candidates";
import { photometryMinimalApi } from "../../ducks/photometry_minimal";
import { useCommentPanel } from "../../contexts/CommentPanelContext";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import type { Group } from "../../types";
import { dec_to_dms, ra_to_hours } from "../../units";
import { MAIN_CHANNEL } from "../comment/channels";
import ThumbnailList from "../thumbnail/ThumbnailList";
import EditSourceGroups from "../source/EditSourceGroups";
import UpdateSourceMPC from "../source/UpdateSourceMPC";
import DisplayPhotStats from "../source/DisplayPhotStats";
import ObjectTags from "../ObjectTags";
import RejectButton from "../RejectButton";
import VegaPhotometry from "../plot/VegaPhotometry";
import TrackCandidateSummary from "../moving_object/TrackCandidateSummary";
import Spinner from "../Spinner";
import ErrorBoundary from "../ErrorBoundary";
import Button from "../Button";
import SaveCandidateButton from "./SaveCandidateButton";
import FilterCandidateList from "./FilterCandidateList";
import ScanningPageCandidateAnnotations from "./ScanningPageCandidateAnnotations";
import AddClassificationsScanningPage from "./AddClassificationsScanningPage";
import CandidatePlugins from "./CandidatePlugins";
import GenerateReportForm from "./scan_reports/GenerateReportForm";

const TrackScanner = lazy(() => import("../superobj/TrackScanner"));
const CommentThread = lazy(() => import("../comment/CommentThread"));

const numPerPage = 50;
const appBarHeight = { xs: 56, sm: 64 };
const shownSavedGroups = 3;

const mostRecentClass = (classifications: any[]) =>
  classifications
    .filter((c) => c.probability > 0)
    .sort((a, b) => (a.modified < b.modified ? 1 : -1))[0]?.classification;

const trackIdFor = (obj: any): string | null => {
  for (const annotation of obj.annotations) {
    const found = annotation.data?.track_id ?? annotation.data?.track?.id;
    if (found) return String(found);
  }
  return null;
};

const InfoRow = ({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) => (
  <Box
    sx={{
      display: "flex",
      flexWrap: "wrap",
      alignItems: "center",
      gap: 0.5,
    }}
  >
    <b>{label}</b>
    {children}
  </Box>
);

interface CandidateTabsProps {
  candidate: any;
  filterGroups: Group[];
}

const CandidateTabs = ({ candidate, filterGroups }: CandidateTabsProps) => {
  const { scanningFirstTab = "comments", showBotComments } =
    (useGetProfileQuery().data?.preferences ?? {}) as any;
  const { setTarget, setOpen, setSpace, setChannel } = useCommentPanel();
  const [chosenTab, setChosenTab] = useState<string | null>(null);
  const commentCount =
    candidate.comment_count -
    (showBotComments ? 0 : candidate.bot_comment_count);
  const tab =
    chosenTab ??
    (scanningFirstTab === "comments" && commentCount > 0
      ? "comments"
      : "annotations");

  const openCommentPanel = () => {
    setTarget({ type: "source", id: candidate.id, origin: "scanning" });
    setSpace("comments");
    setChannel(MAIN_CHANNEL);
    setOpen(true);
  };

  return (
    <Box
      sx={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          mb: 1,
          borderBottom: 1,
          borderColor: "divider",
        }}
      >
        <Tabs
          value={tab}
          onChange={(_event, value) => setChosenTab(value)}
          variant="fullWidth"
          sx={{
            flex: 1,
            minHeight: 0,
            "& .MuiTab-root": {
              minHeight: 0,
              minWidth: 0,
              px: 1,
              py: 0.75,
              fontSize: "0.8rem",
              fontWeight: "bold",
              textTransform: "none",
            },
          }}
        >
          <Tab
            value="annotations"
            label={`Annotations (${candidate.annotations.length})`}
            data-testid={`annotations-tab-${candidate.id}`}
          />
          <Tab
            value="comments"
            label={`Comments (${commentCount})`}
            data-testid={`comments-tab-${candidate.id}`}
          />
        </Tabs>
        {tab === "comments" && (
          <Tooltip title="Open in the side panel">
            <IconButton
              size="small"
              onClick={openCommentPanel}
              data-testid={`comment-candidate-${candidate.id}`}
            >
              <OpenInNewIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>
      {tab === "comments" ? (
        <Box sx={{ flex: 1, position: "relative", minHeight: "14rem" }}>
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <Suspense fallback={<CircularProgress size={20} />}>
              <CommentThread
                objID={candidate.id}
                origin="scanning"
                isCandidate
                includeCommentsOnAllResourceTypes={false}
              />
            </Suspense>
          </Box>
        </Box>
      ) : candidate.annotations.length > 0 ? (
        <ScanningPageCandidateAnnotations
          annotations={candidate.annotations}
          filterGroups={filterGroups}
        />
      ) : (
        <Typography variant="body2" color="text.secondary">
          No annotations
        </Typography>
      )}
    </Box>
  );
};

const SavedGroupChips = ({ groups }: { groups: any[] }) => {
  const [expanded, setExpanded] = useState(false);
  const hiddenCount = groups.length - shownSavedGroups;
  return (
    <>
      {(expanded ? groups : groups.slice(0, shownSavedGroups)).map((group) => (
        <Chip
          key={group.id}
          size="small"
          label={(group.nickname || group.name).substring(0, 15)}
        />
      ))}
      {hiddenCount > 0 && (
        <Chip
          size="small"
          variant="outlined"
          color="primary"
          label={expanded ? "Show less" : `+${hiddenCount} more`}
          onClick={() => setExpanded(!expanded)}
        />
      )}
    </>
  );
};

interface CandidateInfoProps {
  candidate: any;
  filterGroups: Group[];
}

const CandidateInfo = ({ candidate, filterGroups }: CandidateInfoProps) => {
  const isReadOnly = useIsReadOnly();
  const { data: groups } = useGetGroupsQuery();
  const savedGroupIds = candidate.saved_groups?.map((g: any) => g.id) ?? [];
  const unsaved = (list: Group[]) =>
    list.filter((g) => !savedGroupIds.includes(g.id));
  const unsavedFilterGroups = unsaved(filterGroups);
  const humanClass = mostRecentClass(
    (candidate.classifications ?? []).filter((c: any) => !c.ml),
  );
  const mlClass = mostRecentClass(
    (candidate.classifications ?? []).filter((c: any) => c.ml),
  );
  const [lastDetectedDate, lastDetectedTime] = String(
    candidate.last_detected_at,
  )
    .slice(0, 19)
    .split("T");

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 0.25,
        fontSize: "0.875rem",
      }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <MuiLink
          href={`/source/${candidate.id}`}
          target="_blank"
          rel="noreferrer"
          data-testid={candidate.id}
          underline="hover"
          sx={{ fontWeight: "bold", fontSize: "1.05rem" }}
        >
          {candidate.id}
        </MuiLink>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          {candidate.photstats?.[0] && (
            <DisplayPhotStats photstats={candidate.photstats[0]} />
          )}
        </Box>
      </Box>
      <ObjectTags source={{ ...candidate, groups: candidate.saved_groups }} />
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 0.5,
        }}
      >
        <Chip
          size="small"
          label={candidate.is_source ? "Previously Saved" : "NOT SAVED"}
          color={candidate.is_source ? "primary" : "default"}
        />
        <RejectButton objID={candidate.id} />
        {!isReadOnly &&
          (!candidate.is_source || unsavedFilterGroups.length > 0) && (
            <Box data-testid="tour-candidate-save">
              <SaveCandidateButton
                candidate={candidate}
                userGroups={unsaved(groups?.userAccessible ?? [])}
                filterGroups={unsavedFilterGroups}
              />
            </Box>
          )}
      </Box>
      {candidate.is_source && (
        <InfoRow label="Saved groups:">
          <EditSourceGroups
            source={{ id: candidate.id, currentGroupIds: savedGroupIds }}
            groups={(groups?.all ?? []).filter((g) => !g["single_user_group"])}
            icon
          />
          <SavedGroupChips groups={candidate.saved_groups} />
        </InfoRow>
      )}
      {candidate.associated_objs?.length > 0 && (
        <InfoRow label="Matches with:">
          {candidate.associated_objs.map((a: any) => (
            <a
              key={a.obj_id}
              href={`/source/${a.obj_id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {a.obj_id}
            </a>
          ))}
        </InfoRow>
      )}
      {candidate.last_detected_at && (
        <InfoRow label="Last detected:">
          <span>
            {lastDetectedTime}&nbsp;&nbsp;{lastDetectedDate}
          </span>
        </InfoRow>
      )}
      <Box>
        <b>Coordinates:</b>
        <Box sx={{ fontWeight: "bold", fontSize: "105%" }}>
          {ra_to_hours(candidate.ra)} &nbsp;{dec_to_dms(candidate.dec)}
        </Box>
        <Box sx={{ display: "flex", flexWrap: "wrap", columnGap: 1 }}>
          <span>
            (&alpha;,&delta;= {candidate.ra.toFixed(3)}, &nbsp;
            {candidate.dec.toFixed(3)})
          </span>
          <span>
            (l,b= {candidate.gal_lon.toFixed(3)}, &nbsp;
            {candidate.gal_lat.toFixed(3)})
          </span>
        </Box>
      </Box>
      <InfoRow label="MPC:">
        {candidate.is_roid && (
          <Chip
            size="small"
            label={candidate.alias?.[0] ?? candidate.mpc_name}
          />
        )}
        {!isReadOnly && (
          <UpdateSourceMPC
            source={{
              id: candidate.id,
              mpc_name: candidate.mpc_name,
              first_detected: candidate.last_detected_at,
            }}
          />
        )}
      </InfoRow>
      <CandidatePlugins candidate={candidate} />
      <Box
        data-testid="tour-candidate-classifications"
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 0.5,
        }}
      >
        <b>Classification(s):</b>
        {humanClass && <Chip size="small" label={humanClass} color="primary" />}
        {mlClass && (
          <Tooltip title="classification from an ML classifier">
            <Chip size="small" label={`ML: ${mlClass}`} />
          </Tooltip>
        )}
        <AddClassificationsScanningPage obj_id={candidate.id} />
      </Box>
    </Box>
  );
};

interface CandidateProps {
  candidate: any;
  filterGroups: Group[];
  index: number;
  totalMatches: number;
}

const Candidate = ({
  candidate,
  filterGroups,
  index,
  totalMatches,
}: CandidateProps) => {
  const trackId = trackIdFor(candidate);

  return (
    <Paper
      variant="outlined"
      data-testid={`candidate-${index}`}
      sx={{
        borderWidth: 2,
        mb: 2,
        p: 1,
        display: "grid",
        rowGap: 1,
        justifyContent: "space-between",
        gridTemplateColumns: {
          xs: "100%",
          sm: "55% 45%",
          lg: "26% 22% 32% 20%",
        },
        gridTemplateAreas: {
          xs: `"info" "thumbnails" "photometry" "annotations"`,
          sm: `"thumbnails info" "photometry annotations"`,
          lg: `"thumbnails info photometry annotations"`,
        },
      }}
    >
      <Box sx={{ gridArea: "thumbnails" }}>
        <ThumbnailList
          ra={candidate.ra}
          dec={candidate.dec}
          thumbnails={candidate.thumbnails}
          objID={candidate.id}
          size="100%"
          minSize="6rem"
          maxSize="8.8rem"
          titleSize="0.7rem"
          useGrid={false}
          columns={3}
          noMargin
        />
      </Box>
      <Box sx={{ gridArea: "info", pl: 2 }}>
        <CandidateInfo candidate={candidate} filterGroups={filterGroups} />
      </Box>
      <Box sx={{ gridArea: "photometry" }}>
        <VegaPhotometry
          sourceId={candidate.id}
          style={{
            width: "68%",
            height: "100%",
            minHeight: "16rem",
            maxHeight: "16rem",
          }}
        />
        {trackId && (
          <TrackCandidateSummary
            trackId={trackId}
            brokerId={candidate.broker_id ?? 1}
          />
        )}
      </Box>
      <Box
        sx={{
          gridArea: "annotations",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          gap: 1,
          minHeight: "100%",
          pl: 0.5,
          overflowWrap: "break-word",
        }}
      >
        <CandidateTabs candidate={candidate} filterGroups={filterGroups} />
        <Typography
          sx={{ fontWeight: "bold", alignSelf: "flex-end", mt: "auto" }}
        >
          {`${index}/${totalMatches}`}
        </Typography>
      </Box>
    </Paper>
  );
};

type ScanMode = "objects" | "tracks";

const CandidateList = () => {
  const dispatch = useAppDispatch();
  const [scanMode, setScanMode] = useState<ScanMode>("objects");
  const [filterGroups, setFilterGroups] = useState<Group[]>([]);
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [searchParams, setSearchParams] = useState<Record<string, any> | null>(
    null,
  );
  const resultsRef = useRef<HTMLDivElement>(null);
  const sortOptions = useAppSelector(
    (state) => state.candidates.selectedAnnotationSortOptions,
  );
  const sortOrder = sortOptions?.order ?? null;
  const preferences = useGetProfileQuery().data?.preferences as any;
  const defaultScanningProfile = preferences?.scanningProfiles?.find(
    (profile: any) => profile.default,
  );
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();

  const { data, isFetching } = useGetCandidatesQuery(searchParams ?? {}, {
    skip: searchParams === null,
  });
  const {
    candidates = [],
    pageNumber = 1,
    totalMatches = 0,
    queryID = null,
  } = data ?? {};
  const pageCount = Math.max(1, Math.ceil(totalMatches / numPerPage));

  useEffect(() => {
    if (!defaultScanningProfile?.sortingOrder) return;
    dispatch(
      setCandidatesAnnotationSortOptions({
        origin: defaultScanningProfile.sortingOrigin,
        key: defaultScanningProfile.sortingKey,
        order: defaultScanningProfile.sortingOrder,
      }),
    );
  }, [dispatch, defaultScanningProfile]);

  useEffect(() => {
    dispatch(photometryMinimalApi.util.invalidateTags(["Photometry"]));
  }, [pageNumber, dispatch]);

  useEffect(() => {
    const results = resultsRef.current;
    if (results && results.getBoundingClientRect().top < 0)
      results.scrollIntoView();
  }, [searchParams]);

  const goToPage = (page: number) => {
    dispatch(showNotification("Loading more candidates..."));
    setSearchParams({ ...searchParams, pageNumber: page, numPerPage, queryID });
  };

  const sort = () => {
    const order =
      sortOrder === null ? "asc" : sortOrder === "asc" ? "desc" : null;
    dispatch(setCandidatesAnnotationSortOptions({ ...sortOptions, order }));
    setSearchParams({
      ...searchParams,
      pageNumber: 1,
      queryID: undefined,
      sortByAnnotationOrigin: order ? sortOptions.origin : null,
      sortByAnnotationKey: order ? sortOptions.key : null,
      sortByAnnotationOrder: order,
    });
  };

  return (
    <Box data-testid="tour-candidates-page">
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 2,
          mb: 1.5,
        }}
      >
        <Typography variant="h5" sx={{ fontWeight: "bold" }}>
          Scan candidates
        </Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={scanMode}
          onChange={(_event, value) => value && setScanMode(value)}
          data-testid="candidate-scan-mode"
        >
          <ToggleButton value="objects">Sources</ToggleButton>
          <ToggleButton value="tracks">Moving object tracks</ToggleButton>
        </ToggleButtonGroup>
        <Box sx={{ ml: "auto", display: "flex", gap: 1 }}>
          <Tooltip title="Generate a report of saved candidates">
            <Button
              secondary
              size="small"
              onClick={() => setReportDialogOpen(true)}
            >
              Generate report
            </Button>
          </Tooltip>
          <Tooltip title="View previously generated scanning reports">
            <Button
              secondary
              size="small"
              component={Link}
              to="/candidates/scan_reports"
            >
              View reports
            </Button>
          </Tooltip>
        </Box>
        <GenerateReportForm
          dialogOpen={reportDialogOpen}
          setDialogOpen={setReportDialogOpen}
        />
      </Box>
      {scanMode === "tracks" && (
        <Suspense fallback={<Spinner />}>
          <TrackScanner />
        </Suspense>
      )}
      <Box
        data-testid="tour-candidates-filter"
        sx={{ display: scanMode === "tracks" ? "none" : undefined }}
      >
        <FilterCandidateList
          setFilterGroups={setFilterGroups}
          numPerPage={numPerPage}
          setSearchParams={setSearchParams}
        />
        {searchParams ? (
          <Box ref={resultsRef} sx={{ mt: 1.5, scrollMarginTop: appBarHeight }}>
            <Paper
              variant="outlined"
              sx={{
                position: "sticky",
                top: appBarHeight,
                zIndex: 3,
                mb: 2,
                px: 2,
                py: 0.5,
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 1,
              }}
            >
              <Typography variant="h6">
                {isFetching
                  ? "Searching..."
                  : `Found ${totalMatches} candidates.`}
              </Typography>
              <Box
                sx={{
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  gap: 1,
                }}
              >
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Cards open on
                  </Typography>
                  <Tooltip title="Tab each card opens on. Comments only when the candidate has some.">
                    <ToggleButtonGroup
                      size="small"
                      exclusive
                      value={preferences?.scanningFirstTab ?? "comments"}
                      sx={{
                        "& .MuiToggleButton-root": {
                          textTransform: "none",
                          py: 0.25,
                        },
                      }}
                      onChange={(_event, value) =>
                        value &&
                        updateUserPreferences({ scanningFirstTab: value })
                      }
                    >
                      <ToggleButton value="annotations">
                        Annotations
                      </ToggleButton>
                      <ToggleButton value="comments">Comments</ToggleButton>
                    </ToggleButtonGroup>
                  </Tooltip>
                </Box>
                <Tooltip title="Sort on Selected Annotation">
                  <span>
                    <IconButton
                      onClick={sort}
                      disabled={!sortOptions || isFetching}
                      data-testid="sortOnAnnotationButton"
                      sx={{ "&:hover": { color: "primary.main" } }}
                    >
                      <SortIcon />
                      {sortOrder === "asc" && <ArrowUpward />}
                      {sortOrder === "desc" && <ArrowDownward />}
                    </IconButton>
                  </span>
                </Tooltip>
                <Button
                  primary
                  size="small"
                  onClick={() => goToPage(pageNumber - 1)}
                  disabled={pageNumber === 1 || isFetching}
                >
                  <ArrowBackIcon />
                  Previous
                </Button>
                <Typography variant="body2">
                  Page {pageNumber} of {pageCount}
                </Typography>
                <Button
                  primary
                  size="small"
                  onClick={() => goToPage(pageNumber + 1)}
                  disabled={pageNumber >= pageCount || isFetching}
                >
                  Next
                  <ArrowForwardIcon />
                </Button>
                <Button
                  primary
                  size="small"
                  onClick={() => window.scrollTo({ top: 0 })}
                >
                  Back to top <ArrowUpward />
                </Button>
              </Box>
            </Paper>
            {isFetching ? (
              <Spinner />
            ) : (
              <ViewportList items={candidates}>
                {(candidate: any, index: number) => (
                  <ErrorBoundary
                    key={candidate.id}
                    fallback={
                      <Typography color="error" sx={{ mb: 2 }}>
                        Could not display {candidate.id}.
                      </Typography>
                    }
                  >
                    <Candidate
                      candidate={candidate}
                      filterGroups={filterGroups}
                      index={(pageNumber - 1) * numPerPage + index + 1}
                      totalMatches={totalMatches}
                    />
                  </ErrorBoundary>
                )}
              </ViewportList>
            )}
          </Box>
        ) : (
          <Typography
            color="text.secondary"
            sx={{ mt: 4, textAlign: "center" }}
          >
            Select one or more groups, then click Search.
          </Typography>
        )}
      </Box>
    </Box>
  );
};

export default CandidateList;
