import { useGetProfileQuery, useIsReadOnly } from "../../ducks/profile";
import { useGetGroupsQuery } from "../../ducks/groups";
import { useGetTaxonomiesQuery } from "../../ducks/taxonomies";
import { useGetObservingRunsQuery } from "../../ducks/observingRuns";
import React, {
  useEffect,
  useState,
  useMemo,
  useCallback,
  Suspense,
} from "react";
import { Link } from "react-router-dom";

import { makeStyles } from "tss-react/mui";
import Box from "@mui/material/Box";
import { alpha } from "@mui/material/styles";
import { deepPurple, teal } from "@mui/material/colors";
import SendOutlinedIcon from "@mui/icons-material/SendOutlined";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import Tooltip from "@mui/material/Tooltip";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Typography from "@mui/material/Typography";

import CircularProgress from "@mui/material/CircularProgress";
import AddIcon from "@mui/icons-material/Add";
import Menu from "@mui/material/Menu";
import Divider from "@mui/material/Divider";
import ListItemIcon from "@mui/material/ListItemIcon";
import SearchIcon from "@mui/icons-material/Search";
import ImageOutlinedIcon from "@mui/icons-material/ImageOutlined";
import PictureAsPdfOutlinedIcon from "@mui/icons-material/PictureAsPdfOutlined";
import ShowChartOutlinedIcon from "@mui/icons-material/ShowChartOutlined";
import FormatListBulletedOutlinedIcon from "@mui/icons-material/FormatListBulletedOutlined";
import MenuItem from "@mui/material/MenuItem";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import useMediaQuery from "@mui/material/useMediaQuery";
import KeyboardArrowLeftIcon from "@mui/icons-material/KeyboardArrowLeft";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";

import withRouter from "../withRouter";

import CopyPhotometryDialog from "./CopyPhotometryDialog";
import ClassificationList from "../classification/ClassificationList";
import ClassificationForm from "../classification/ClassificationForm";
import ShowClassification from "../classification/ShowClassification";
import ShowSummaries, { latestSummary } from "../summary/ShowSummaries";
import SurveyLinkList from "./SurveyLinkList";
import StarList from "../StarList";
import FollowupRequestForm from "../followup_request/FollowupRequestForm";
import FollowupRequestLists from "../followup_request/FollowupRequestLists";
import AssignmentForm from "../observing_run/AssignmentForm";
import AssignmentList from "../observing_run/AssignmentList";
import SourceNotification from "./SourceNotification";
import DisplayPhotStats from "./DisplayPhotStats";
import DisplayTNSInfo from "./DisplayTNSInfo";
import EditSourceGroups from "./EditSourceGroups";
import SavedGroupChips from "../group/SavedGroupChips";
import SimilarSources from "./SimilarSources";
import SimilarObjects from "./SimilarObjects";
import SourceAcknowledgment from "./SourceAcknowledgment";
import SourceAlias from "./SourceAlias";
import UpdateSourceGCNCrossmatch from "./UpdateSourceGCNCrossmatch";
import UpdateSourceMPC from "./UpdateSourceMPC";
import UpdateSourceSummary from "./UpdateSourceSummary";
import UpdateSourceT0 from "./UpdateSourceT0";
import UpdateSourceTNS from "./UpdateSourceTNS";
import WithholdFromTNS from "./WithholdFromTNS";
import StartBotSummary from "../StartBotSummary";
import SourceGCNCrossmatchList from "./SourceGCNCrossmatchList";
import SourceRedshift from "./SourceRedshift";
import SourceCandidatesHistory from "./SourceCandidatesHistory";
import CommentPanel from "../comment/CommentPanel";
import { INTERESTED_CHANNEL } from "../comment/channels";
import {
  useCommentPanel,
  useCommentTarget,
} from "../../contexts/CommentPanelContext";
import SourceInterests from "./SourceInterests";
import RequestDataAccess from "./RequestDataAccess";
import UnsharedSpectra from "./UnsharedSpectra";
import { useGetDataAvailabilityQuery } from "../../ducks/dataAccessRequests";
import ShowSummaryHistory from "../summary/ShowSummaryHistory";
import AnnotationsTable from "./AnnotationsTable";
import GcnNotesTable from "../gcn/GcnNotesTable";
import AnalysisList from "../analysis/AnalysisList";
import AnalysisForm from "../analysis/AnalysisForm";
import SourceSaveHistory from "./SourceSaveHistory";
import PhotometryTable from "../photometry/PhotometryTable";
import FavoritesButton from "../listing/FavoritesButton";
import SourceAnnotationButtons from "./SourceAnnotationButtons";
import Reminders from "../Reminders";
import QuickSaveButtons from "./QuickSaveSource";
import SourceSkeleton from "./SourceSkeleton";
import Button from "../Button";

import ObjectTags from "../ObjectTags";
import { useFetchSourceSpectraQuery } from "../../ducks/spectra";
import {
  useGetSourceQuery,
  useGetAssociatedGcnsQuery,
  useGetSourcePositionQuery,
  useAddSourceViewMutation,
} from "../../ducks/source";

import PhotometryPlot from "../plot/PhotometryPlot";
import SpectraPlot from "../plot/SpectraPlot";
import PhotometryMagsys from "../photometry/PhotometryMagsys";
import SourcePublish from "./source_publish/SourcePublish";
import SourceCoordinates from "./SourceCoordinates";
import SharingServicesDialog from "../sharing_service/SharingServicesForm";
import ThumbnailList from "../thumbnail/ThumbnailList";
import {
  useGetInstrumentFormsQuery,
  useGetInstrumentsQuery,
} from "../../ducks/instruments";
import {
  useGetBrokerHostsQuery,
  useGetBrokersQuery,
} from "../../ducks/brokers";
import SourceHost from "./SourceHost";
import FieldLabel from "./FieldLabel";
import softButtonsSx from "../softButtons";

const VegaHR = React.lazy(() => import("../plot/VegaHR"));

const CentroidPlot = React.lazy(
  () => import(/* webpackChunkName: "CentroidPlot" */ "../plot/CentroidPlot"),
);

export const useSourceStyles = makeStyles()((theme) => ({
  header: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    columnGap: "0.25rem",
    marginBottom: "0.25rem",
  },
  name: {
    lineHeight: "1em",
    fontSize: "200%",
    fontWeight: "900",
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
    display: "inline-block",
    padding: 0,
    margin: 0,
  },
  flexRow: {
    display: "flex",
    flexDirection: "row",
    width: "100%",
  },
  flexColumn: {
    display: "flex",
    flexDirection: "column",
    width: "100%",
  },
  accordionSummary: {
    "&>div": {
      display: "flex",
      justifyContent: "flex-start",
      gap: "0.5rem",
      alignItems: "center",
    },
  },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
  accordionPlot: {
    padding: 0,
    margin: 0,
    width: "100%",
  },
  buttonContainer: {
    display: "flex",
    flexFlow: "wrap",
    alignItems: "center",
    gap: "0.5rem",
    padding: "0.5rem 1rem 1rem 1rem",
  },
  plotContainer: {
    padding: 0,
    minWidth: "100%",
    height: "100%",
    paddingBottom: "0.75rem",
  },
  panelButton: {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.primary.contrastText,
    "&:hover": {
      color: theme.palette.primary.main,
    },
  },
  container: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "0.25rem",
  },
  fieldRow: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    columnGap: "1rem",
  },
  rowInfo: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
    minHeight: theme.spacing(4),
    "& > .MuiChip-root + *": { marginLeft: theme.spacing(0.5) },
  },
  lineRow: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    columnGap: "0.5rem",
    "& > div": {
      display: "flex",
      alignItems: "center",
      minHeight: theme.spacing(4),
    },
  },
  linkedObjs: {
    flexBasis: "100%",
    display: "flex",
    alignItems: "center",
    minHeight: theme.spacing(4),
  },
  linkedObjList: {
    display: "flex",
    flexWrap: "wrap",
    alignItems: "center",
    gap: "0.25rem 0.5rem",
  },
  dmdlInfo: {
    flexWrap: "wrap",
    columnGap: "0.5rem",
    "& > div": {
      display: "flex",
      alignItems: "center",
      minHeight: theme.spacing(4),
    },
  },
  sourceCandidates: {
    marginLeft: "0.1rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
}));

const HoverAction = ({ children }: { children: React.ReactNode }) => (
  <Box
    component="span"
    sx={{
      position: "absolute",
      left: "100%",
      top: "50%",
      transform: "translateY(-50%)",
      ml: "-1px",
      display: "flex",
      opacity: 0,
      transition: "opacity 0.15s",
      "*:hover > &, *:focus-within > &": { opacity: 1 },
      "@media (hover: none)": { opacity: 1 },
      "& .MuiIconButton-root": {
        p: "1px",
        color: "text.secondary",
        "&:hover": { color: "primary.main" },
      },
      "& .MuiSvgIcon-root": { fontSize: "0.75rem" },
    }}
  >
    {children}
  </Box>
);

interface SourceContentProps {
  source: any;
}

const SourceContent = ({ source }: SourceContentProps) => {
  const { classes } = useSourceStyles() as { classes: any };

  const { data: currentUser } = useGetProfileQuery();
  const isReadOnly = useIsReadOnly();
  const groups = ((useGetGroupsQuery().data?.all ?? null) || []).filter(
    (g: any) => !g.single_user_group,
  );
  const { data: spectra } = useFetchSourceSpectraQuery({ id: source.id });
  // Spectra exist that the viewer cannot open: "no spectrum exists" would be
  // the wrong thing to say, and there is something to ask for.
  const { data: dataAvailability } = useGetDataAvailabilityQuery(source.id, {
    skip: !source.id,
  });
  const unsharedSpectraCount = dataAvailability?.spectra?.length ?? 0;
  const { data: associatedGcnsData } = useGetAssociatedGcnsQuery(source.id);
  const associatedGCNs = associatedGcnsData?.["gcns"];

  const { data: brokers = [] } = useGetBrokersQuery();
  const { data: brokerHosts } = useGetBrokerHostsQuery([source.id], {
    skip: source.is_roid,
  });
  const { data: instrumentList = [] } = useGetInstrumentsQuery();
  const { data: instrumentFormParams = {} } = useGetInstrumentFormsQuery();
  // Only runs a target can still be assigned to; the full history is a couple
  // of megabytes and nothing on this page shows it.
  const { data: observingRunList = [] } = useGetObservingRunsQuery({
    upcomingOnly: true,
  });
  const { data: taxonomyList = [] } = useGetTaxonomiesQuery();

  const [copyPhotometryDialogOpen, setCopyPhotometryDialogOpen] =
    useState(false);
  const [sendToDialogOpen, setSendToDialogOpen] = useState(false);

  // Needed for buttons that open popover menus, indicates where the popover should be anchored
  // (where it will appear on the screen)
  const [anchorElObserving, setAnchorElObserving] =
    useState<HTMLElement | null>(null);

  const [showStarList, setShowStarList] = useState(false);
  const [showPhotometry, setShowPhotometry] = useState(false);
  const closePhotometryTable = useCallback(() => setShowPhotometry(false), []);
  const [rightPanelVisible, setRightPanelVisible] = useState(true);
  const [analysisDialogOpen, setAnalysisDialogOpen] = useState(false);
  const commentPanel = useCommentPanel();
  useCommentTarget(isReadOnly ? null : { type: "source", id: source.id });
  const [magsys, setMagsys] = useState("ab");
  const [showExtinctionCorrection, setShowExtinctionCorrection] =
    useState(false);

  const downSm = useMediaQuery((theme: any) => theme.breakpoints.down("sm"));
  const downMd = useMediaQuery((theme: any) => theme.breakpoints.down("md"));
  const downLg = useMediaQuery((theme: any) => theme.breakpoints.down("lg"));

  const alertBroker = brokers.find(
    (b) =>
      b.active && b.capabilities?.["query_alerts"] && b.default_alert_search,
  );
  const hostBroker = brokers.find((b) => b.active && b.default_crossmatch);
  const hasSimilarityBroker = brokers.some(
    (b) => b.active && b.capabilities?.["similar_objects"],
  );

  const sourceDuplicatesWithoutAssociatedObjs = useMemo(
    () =>
      source.duplicates?.filter(
        (d: any) =>
          !(source.associated_objs || []).some(
            (a: any) => a.obj_id === d.obj_id,
          ),
      ) ?? [],
    [source.duplicates, source.associated_objs],
  );

  const spectrumAnnotations: any[] = [];
  if (spectra) {
    spectra.forEach((spec: any) => {
      spec.annotations.forEach((annotation: any) => {
        // `annotation` is frozen RTK Query cache data — build a new object with
        // the extra field rather than mutating it (`Object is not extensible`).
        spectrumAnnotations.push({
          ...annotation,
          spectrum_observed_at: spec.observed_at,
        });
      });
    });
  }

  const showSummary =
    currentUser?.id && !currentUser?.preferences?.["hideSourceSummary"];
  const showAISummaries = (currentUser?.preferences?.["showAISourceSummary"] ||
    false) as any;
  const noSummary = !latestSummary(source.summary_history, showAISummaries);
  const summaryActions = (chip = false) => (
    <>
      {!isReadOnly && (
        <UpdateSourceSummary
          source={source}
          showAISummaries={showAISummaries}
          chip={chip}
        />
      )}
      {!isReadOnly &&
        (source.comments?.length > 0 || source.classifications?.length > 0) && (
          <StartBotSummary obj_id={source.id} />
        )}
      {source.summary_history?.length > 0 && (
        <ShowSummaryHistory
          summaries={source.summary_history}
          obj_id={source.id}
        />
      )}
    </>
  );

  // associatedGCNs is an array of dateobs
  // source.gcn_crossmatch is an array of objects with dateobs
  // we want to combine these two arrays into one array of dateobs deduplicated
  // and sorted by date in descending order
  const gcn_crossmatches = (associatedGCNs || [])
    .concat((source.gcn_crossmatch || []).map((gcn: any) => gcn.dateobs))
    .filter(
      (gcn: any, index: number, self: any[]) => self.indexOf(gcn) === index,
    )
    .sort((a: any, b: any) => new Date(b).getTime() - new Date(a).getTime());

  const { data: adjustedPosition } = useGetSourcePositionQuery(source.id);
  const sourceWithPosition = useMemo(
    () => ({ ...source, adjusted_position: adjustedPosition }),
    [source, adjustedPosition],
  );

  const rightPanelContent = (
    downLarge: boolean,
    isRightPanelVisible: boolean,
  ) => (
    <>
      <Grid
        size={{ xs: 12, lg: 6 }}
        sx={{
          order: { xs: 6, md: 4, lg: 3 },
        }}
      >
        <Paper id="annotations-content" className={classes.flexColumn}>
          <AnnotationsTable
            title="Auto-annotations"
            annotations={source.annotations}
            spectrumAnnotations={spectrumAnnotations}
          />
          {!isReadOnly && (
            <div style={{ padding: "0.5rem" }}>
              <SourceAnnotationButtons source={source} />
            </div>
          )}
        </Paper>
      </Grid>
      {source?.gcn_notes?.length > 0 && (
        <Grid
          size={12}
          sx={{
            order: { xs: 7, md: 5, lg: !downLg && !rightPanelVisible ? 5 : 4 },
          }}
        >
          <Accordion
            defaultExpanded
            disableGutters
            className={classes.flexColumn}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="gcnNotes-content"
              id="gcnNotes-header"
            >
              <Typography className={classes.accordionHeading}>
                GCN Notes
              </Typography>
            </AccordionSummary>
            <AccordionDetails
              style={{
                padding: 0,
                display: "flex",
                flexDirection: "column",
                minHeight: downLarge || isRightPanelVisible ? "30vh" : "40vh",
              }}
            >
              <GcnNotesTable gcnNotes={source.gcn_notes} />
            </AccordionDetails>
          </Accordion>
        </Grid>
      )}
      {!isReadOnly && commentPanel.inline && (
        <Grid
          size={{ xs: 12, lg: 6 }}
          sx={{
            order: {
              xs: 3,
              md: 3,
              lg: downLarge || isRightPanelVisible ? 5 : 4,
            },
          }}
        >
          <CommentPanel inline />
        </Grid>
      )}
      <Grid
        size={12}
        sx={{
          order: { xs: 13, md: 10, lg: 8 },
        }}
      >
        <Accordion
          defaultExpanded
          disableGutters
          className={classes.flexColumn}
          data-testid="source-classifications"
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="classifications-content"
          >
            <Typography className={classes.accordionHeading}>
              Classifications
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <ClassificationList obj={source} />
            {!isReadOnly && (
              <ClassificationForm
                obj_id={source.id}
                taxonomyList={taxonomyList}
                {...({ action: "createNew" } as any)}
              />
            )}
          </AccordionDetails>
        </Accordion>
      </Grid>
      <Grid
        size={{ xs: 12, lg: 6 }}
        sx={{
          order: { xs: 8, lg: 12 },
        }}
      >
        <Accordion
          defaultExpanded
          disableGutters
          className={classes.flexColumn}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="centroidplot-content"
            id="centroidplot-header"
          >
            <Typography className={classes.accordionHeading}>
              Centroid Plot
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Suspense fallback={<CircularProgress color="secondary" />}>
              <CentroidPlot
                sourceId={source.id}
                plotStyle={{ height: "50vh" }}
              />
            </Suspense>
          </AccordionDetails>
        </Accordion>
      </Grid>
      {hasSimilarityBroker && (
        <Grid
          size={{ xs: 12, lg: 6 }}
          sx={{
            order: { xs: 14, lg: 12 },
          }}
        >
          <Accordion
            defaultExpanded
            disableGutters
            className={classes.flexColumn}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="similar-objects-content"
              id="similar-objects-header"
            >
              <Typography className={classes.accordionHeading}>
                Similar Objects
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <SimilarObjects objId={source.id} />
            </AccordionDetails>
          </Accordion>
        </Grid>
      )}
      <Grid
        size={{ xs: 12, lg: 6 }}
        sx={{
          order: { xs: 9, lg: 13 },
        }}
      >
        <Paper className={classes.flexColumn} sx={{ p: 2, gap: 1.5 }}>
          <Typography
            id="hr-diagram-header"
            className={classes.accordionHeading}
          >
            HR Diagram
          </Typography>
          <div data-testid={`hr_diagram_${source.id}`}>
            {source.color_magnitude?.length ? (
              <Suspense fallback={<CircularProgress color="secondary" />}>
                <VegaHR
                  data={source.color_magnitude}
                  width={300}
                  height={300}
                />
              </Suspense>
            ) : (
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                No color magnitude for this source
              </Typography>
            )}
          </div>
        </Paper>
      </Grid>
      <Grid
        size={{ xs: 12, lg: 6 }}
        sx={{
          order: 15,
        }}
      >
        <Paper className={classes.flexColumn} sx={{ p: 2, gap: 1.5 }}>
          <Typography
            id="notifications-header"
            className={classes.accordionHeading}
          >
            Source Notification
          </Typography>
          {!isReadOnly && <SourceNotification sourceId={source.id} />}
          {!isReadOnly && (
            <Reminders resourceId={source.id} resourceType="source" />
          )}
        </Paper>
      </Grid>
    </>
  );

  return (
    <Grid container spacing={1.5}>
      <Grid
        container
        size={{ xs: 12, lg: rightPanelVisible && !downLg ? 7 : 12 }}
        spacing={1.5}
        sx={{ alignContent: "flex-start" }}
      >
        <Grid
          size={12}
          sx={{
            order: 1,
          }}
        >
          <Paper style={{ padding: "0.5rem" }}>
            <div className={classes.container}>
              <div className={classes.header}>
                {!isReadOnly && <FavoritesButton sourceID={source.id} />}
                <h6 className={classes.name}>{source.id}</h6>
                <SourceAcknowledgment obj_id={source.id} />
                <div className={classes.sourceCandidates}>
                  <SourceCandidatesHistory
                    candidates={source?.candidates || []}
                  />
                </div>
                {!isReadOnly && (
                  <Box sx={{ ml: 1 }}>
                    <ObjectTags source={source} />
                  </Box>
                )}
              </div>
              {!downLg && (
                <div className={classes.container}>
                  <IconButton
                    onClick={() => setRightPanelVisible(!rightPanelVisible)}
                    size="small"
                    className={classes.panelButton}
                  >
                    {rightPanelVisible ? (
                      <KeyboardArrowRightIcon />
                    ) : (
                      <KeyboardArrowLeftIcon />
                    )}
                  </IconButton>
                </div>
              )}
            </div>
            {source.classifications?.length > 0 && (
              <Box sx={{ mb: 0.5 }}>
                <ShowClassification
                  classifications={source.classifications}
                  taxonomyList={taxonomyList}
                  shortened
                />
              </Box>
            )}
            <SourceCoordinates source={sourceWithPosition} />
            <div className={classes.lineRow}>
              {/* Meaningless for a solar-system object. DM and luminosity
                  distance derive from it, so they drop out on their own. */}
              {!source.is_roid && (
                <div>
                  <FieldLabel>Redshift</FieldLabel>
                  <SourceRedshift source={source} readOnly={isReadOnly} />
                </div>
              )}
              <div className={classes.dmdlInfo}>
                {source.dm && (
                  <div>
                    <FieldLabel>DM</FieldLabel>
                    {source.dm.toFixed(3)} mag
                  </div>
                )}
                {source.luminosity_distance && (
                  <div>
                    <FieldLabel>
                      <i>D</i>
                      <sub>L</sub>
                    </FieldLabel>
                    {source.luminosity_distance.toFixed(2)} Mpc
                  </div>
                )}
                <div>
                  <FieldLabel>T0</FieldLabel>
                  <UpdateSourceT0 source={source} readOnly={isReadOnly} />
                </div>
              </div>
            </div>
            <div className={classes.fieldRow}>
              <Box className={classes.rowInfo} data-testid="tour-source-tns">
                <Tooltip title="Transient reported at this position, from the Transient Name Server">
                  <FieldLabel>TNS</FieldLabel>
                </Tooltip>
                {source.tns_name && (
                  <Chip
                    size="small"
                    label={source.tns_name}
                    component="a"
                    href={`https://www.wis-tns.org/object/${
                      source.tns_name.trim().includes(" ")
                        ? source.tns_name.split(" ")[1]
                        : source.tns_name
                    }`}
                    target="_blank"
                    rel="noopener noreferrer"
                    clickable
                  />
                )}
                {source.tns_info && (
                  <DisplayTNSInfo
                    tns_info={source.tns_info}
                    display_header={false}
                  />
                )}
                {!source.tns_name && !isReadOnly && (
                  <UpdateSourceTNS sourceId={source.id} />
                )}
                {(!source.tns_name || source.withhold_from_tns) && (
                  <WithholdFromTNS source={source} readOnly={isReadOnly} />
                )}
              </Box>
              <Box className={classes.rowInfo} sx={{ position: "relative" }}>
                <Tooltip title="Known solar system object at this position, from the Minor Planet Center">
                  <FieldLabel>MPC</FieldLabel>
                </Tooltip>
                {source.mpc_name && (
                  <Chip size="small" label={source.mpc_name} />
                )}
                {!isReadOnly && <UpdateSourceMPC source={source} />}
              </Box>
              <Box className={classes.rowInfo} sx={{ position: "relative" }}>
                <Tooltip title="Events this object was matched to by the GCN crossmatch or by hand">
                  <FieldLabel>GCN matches</FieldLabel>
                </Tooltip>
                {source.gcn_crossmatch?.length > 0 && (
                  <SourceGCNCrossmatchList
                    gcn_crossmatches={gcn_crossmatches}
                    source={source}
                    matchedLocalizations={Object.fromEntries(
                      (source.gcn_crossmatch || []).map((gcn: any) => [
                        gcn.dateobs.replace(" ", "T"),
                        gcn.matched_localization_name,
                      ]),
                    )}
                  />
                )}
                {!isReadOnly && (
                  <HoverAction>
                    <UpdateSourceGCNCrossmatch source={source} />
                  </HoverAction>
                )}
              </Box>
            </div>
            <div className={classes.fieldRow}>
              <div className={classes.rowInfo}>
                <SourceAlias source={source} />
              </div>
            </div>
            <SourceHost
              source={source}
              brokerHosts={brokerHosts}
              brokerName={hostBroker?.name}
              isReadOnly={isReadOnly}
            />
            {sourceDuplicatesWithoutAssociatedObjs.length > 0 && (
              <Box className={classes.linkedObjs}>
                <FieldLabel>Possible duplicate of</FieldLabel>
                <Box className={classes.linkedObjList}>
                  {sourceDuplicatesWithoutAssociatedObjs.map(
                    (duplicate: any) => (
                      <Box
                        key={duplicate.obj_id}
                        sx={{ display: "inline-flex", alignItems: "center" }}
                      >
                        <Tooltip
                          title={`${duplicate.separation.toFixed(2)}″ away`}
                        >
                          <Chip
                            size="small"
                            variant="outlined"
                            clickable
                            component={Link}
                            to={`/source/${duplicate.obj_id}`}
                            label={duplicate.obj_id}
                          />
                        </Tooltip>
                        {!isReadOnly && (
                          <>
                            <Tooltip title="Copy its photometry here">
                              <IconButton
                                size="small"
                                name={`copySourceButton${duplicate.obj_id}`}
                                onClick={() =>
                                  setCopyPhotometryDialogOpen(true)
                                }
                              >
                                <AddIcon sx={{ fontSize: "1rem" }} />
                              </IconButton>
                            </Tooltip>
                            <CopyPhotometryDialog
                              source={source}
                              duplicate={duplicate}
                              dialogOpen={copyPhotometryDialogOpen}
                              closeDialog={() =>
                                setCopyPhotometryDialogOpen(false)
                              }
                            />
                          </>
                        )}
                      </Box>
                    ),
                  )}
                </Box>
              </Box>
            )}
            {source?.associated_objs?.length > 0 && (
              <Box className={classes.linkedObjs}>
                <FieldLabel>Associated with</FieldLabel>
                <Box className={classes.linkedObjList}>
                  {source.associated_objs.map((associatedObj: any) => (
                    <Tooltip
                      key={associatedObj.obj_id}
                      title={`${associatedObj.separation.toFixed(2)}″ away`}
                    >
                      <Chip
                        size="small"
                        variant="outlined"
                        clickable
                        component={Link}
                        to={`/source/${associatedObj.obj_id}`}
                        label={associatedObj.obj_id}
                        sx={{
                          fontWeight: 600,
                          color: (theme) =>
                            theme.palette.mode === "dark"
                              ? theme.palette.secondary.main
                              : theme.palette.primary.main,
                        }}
                      />
                    </Tooltip>
                  ))}
                </Box>
              </Box>
            )}
            {source.summary_history?.length > 0 &&
            currentUser?.preferences?.["showSimilarSources"] === true ? (
              <SimilarSources source={source} k={3} />
            ) : null}
            <Box
              sx={(theme) => {
                const { success, primary, secondary } = theme.palette;
                const dark = theme.palette.mode === "dark";
                const tint = (color: string) => ({
                  bgcolor: alpha(color, 0.14),
                  color,
                  "&:hover": { bgcolor: alpha(color, 0.22) },
                });
                return {
                  ...softButtonsSx(theme),
                  flexBasis: "100%",
                  display: "flex",
                  flexWrap: "wrap",
                  alignItems: "center",
                  gap: 0.75,
                  mt: 0.75,
                  "& [data-testid=interested-button].MuiButton-colorSuccess": {
                    bgcolor: alpha(success.main, 0.16),
                    color:
                      theme.palette.mode === "dark"
                        ? success.light
                        : success.dark,
                    "&:hover": { bgcolor: alpha(success.main, 0.24) },
                  },
                  "& [data-testid=observing-button]": tint(
                    dark ? secondary.main : primary.main,
                  ),
                  "& [data-testid=send-to-button]": tint(
                    dark ? deepPurple[200] : deepPurple[500],
                  ),
                  "& [data-testid=search-alerts-button]": tint(
                    dark ? teal[200] : teal[700],
                  ),
                };
              }}
            >
              <Tooltip title="Finding chart, observability and starlist">
                <Button
                  secondary
                  color="primary"
                  size="small"
                  endIcon={<ExpandMoreIcon />}
                  data-testid="observing-button"
                  aria-haspopup="true"
                  aria-expanded={Boolean(anchorElObserving)}
                  onClick={(e: any) => setAnchorElObserving(e.currentTarget)}
                >
                  Observing
                </Button>
              </Tooltip>
              <Menu
                transitionDuration={50}
                anchorEl={anchorElObserving}
                open={Boolean(anchorElObserving)}
                onClose={() => setAnchorElObserving(null)}
                slotProps={{ list: { dense: true } }}
              >
                <MenuItem
                  component={Link}
                  to={`/source/${source.id}/finder`}
                  target="_blank"
                  onClick={() => setAnchorElObserving(null)}
                >
                  <ListItemIcon>
                    <ImageOutlinedIcon fontSize="small" />
                  </ListItemIcon>
                  Finding chart
                </MenuItem>
                <MenuItem
                  component="a"
                  href={`/api/sources/${source.id}/finder`}
                  download="finder-chart"
                  onClick={() => setAnchorElObserving(null)}
                >
                  <ListItemIcon>
                    <PictureAsPdfOutlinedIcon fontSize="small" />
                  </ListItemIcon>
                  Finding chart PDF
                </MenuItem>
                <Divider />
                <MenuItem
                  component={Link}
                  to={`/observability/${source.id}`}
                  target="_blank"
                  onClick={() => setAnchorElObserving(null)}
                >
                  <ListItemIcon>
                    <ShowChartOutlinedIcon fontSize="small" />
                  </ListItemIcon>
                  Observability
                </MenuItem>
                <MenuItem
                  component="a"
                  href={`/api/sources/${source.id}/observability`}
                  download={`observabilityChartRequest-${source.id}`}
                  data-testid={`observabilityChartRequest_${source.id}`}
                  onClick={() => setAnchorElObserving(null)}
                >
                  <ListItemIcon>
                    <PictureAsPdfOutlinedIcon fontSize="small" />
                  </ListItemIcon>
                  Observability PDF
                </MenuItem>
                <Divider />
                <MenuItem
                  onClick={() => {
                    setShowStarList(!showStarList);
                    setAnchorElObserving(null);
                  }}
                >
                  <ListItemIcon>
                    <FormatListBulletedOutlinedIcon fontSize="small" />
                  </ListItemIcon>
                  {showStarList ? "Hide starlist" : "Show starlist"}
                </MenuItem>
              </Menu>
              {!isReadOnly && (
                <>
                  <Tooltip title="Send to TNS, Hermes or TROVE, or make a public page">
                    <Button
                      secondary
                      color="primary"
                      size="small"
                      endIcon={<SendOutlinedIcon />}
                      data-testid="send-to-button"
                      onClick={() => setSendToDialogOpen(true)}
                    >
                      Send to
                    </Button>
                  </Tooltip>
                  <SharingServicesDialog
                    obj_id={source.id}
                    dialogOpen={sendToDialogOpen}
                    setDialogOpen={setSendToDialogOpen}
                    publicPage={
                      <SourcePublish
                        sourceId={source.id}
                        isElements={{
                          summary: source.summary_history?.length > 0,
                          photometry: source.photometry_exists,
                          spectroscopy: source.spectrum_exists,
                          classifications: source.classifications?.length > 0,
                        }}
                      />
                    }
                  />
                </>
              )}
              {alertBroker ? (
                <Tooltip
                  title={`Alerts for this object in ${alertBroker.name}`}
                >
                  <Link
                    to={`/brokers/${alertBroker.id}?${new URLSearchParams({
                      objectId: source.id,
                      ...(source.ra != null && source.dec != null
                        ? {
                            ra: String(source.ra),
                            dec: String(source.dec),
                            radius: "3",
                          }
                        : {}),
                    })}`}
                    target="_blank"
                  >
                    <Button
                      secondary
                      color="primary"
                      size="small"
                      endIcon={<SearchIcon />}
                      data-testid="search-alerts-button"
                    >
                      Search alerts
                    </Button>
                  </Link>
                </Tooltip>
              ) : (
                <Tooltip title="No broker is set as the default for alert search">
                  <span>
                    <Button
                      secondary
                      size="small"
                      disabled
                      endIcon={<SearchIcon />}
                    >
                      Search alerts
                    </Button>
                  </span>
                </Tooltip>
              )}
              {currentUser?.preferences?.["hideSourceSummary"] === true && (
                <ShowSummaryHistory
                  summaries={source.summary_history || []}
                  obj_id={source.id}
                  button
                />
              )}
              {!isReadOnly && (
                <SourceInterests
                  sourceID={source.id}
                  onDiscuss={() => commentPanel.openChannel(INTERESTED_CHANNEL)}
                />
              )}
              {!isReadOnly && <RequestDataAccess sourceID={source.id} />}
            </Box>
            {showStarList && <StarList sourceId={source.id} />}
            {/* checking if the id exists is a way to know if the user profile is loaded or not */}
            {showSummary && noSummary && !isReadOnly && (
              <Box
                sx={{
                  mt: 0.75,
                  display: "flex",
                  alignItems: "center",
                  gap: 0.5,
                }}
              >
                {summaryActions(true)}
              </Box>
            )}
            {showSummary && !noSummary && (
              <Box
                sx={(theme) => ({
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 1,
                  mt: 0.75,
                  py: 1,
                  pl: 1.5,
                  pr: 0.5,
                  borderRadius: "8px",
                  bgcolor: alpha(theme.palette.text.primary, 0.035),
                })}
              >
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box
                    sx={{
                      fontSize: "0.65rem",
                      fontWeight: 600,
                      letterSpacing: "0.06em",
                      textTransform: "uppercase",
                      color: "text.secondary",
                      mb: 0.25,
                    }}
                  >
                    Summary
                  </Box>
                  <Box
                    sx={{
                      "& p": { fontSize: "0.9rem", lineHeight: 1.5 },
                      "& > div > div": { p: 0 },
                    }}
                  >
                    <ShowSummaries
                      summaries={source.summary_history || []}
                      showAISummaries={showAISummaries}
                    />
                  </Box>
                </Box>
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    flexShrink: 0,
                  }}
                >
                  {summaryActions()}
                </Box>
              </Box>
            )}
            <Box
              sx={(theme) => ({
                ...softButtonsSx(theme),
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap: 0.75,
                py: 0.5,
                mt: 1,
              })}
            >
              <SavedGroupChips groups={source.groups ?? []} max={5} />
              {!isReadOnly && (
                <EditSourceGroups
                  source={{
                    id: source.id,
                    currentGroupIds: source.groups?.map((g: any) => g.id),
                  }}
                  groups={groups}
                />
              )}
              {!isReadOnly && (
                <QuickSaveButtons
                  sourceId={source.id}
                  alreadySavedGroups={source.groups?.map((g: any) => g.id)}
                />
              )}
              <SourceSaveHistory groups={source.groups} />
            </Box>
            <ThumbnailList
              ra={source.ra}
              dec={source.dec}
              thumbnails={source.thumbnails}
              objID={source.id}
              size="100%"
              minSize={rightPanelVisible || downLg ? "6rem" : "10rem"}
              titleSize={downSm ? "0.55rem" : undefined}
              useGrid={false}
              columns={rightPanelVisible || downLg ? 3 : 6}
              noMargin
            />
          </Paper>
        </Grid>
        <Grid
          size={12}
          sx={{
            order: 2,
          }}
        >
          <Paper>
            <Typography
              variant="h6"
              style={{
                padding: "0.5rem 0 0 0.5rem",
                fontWeight: "normal",
              }}
            >
              Surveys
            </Typography>
            <div style={{ padding: "0.5rem", paddingTop: 0 }}>
              <SurveyLinkList id={source.id} ra={source.ra} dec={source.dec} />
            </div>
          </Paper>
        </Grid>
        <Grid
          size={12}
          sx={{
            order: { xs: 4, md: 6 },
          }}
        >
          <Accordion
            defaultExpanded
            disableGutters
            className={classes.flexColumn}
          >
            <AccordionSummary
              component="div"
              expandIcon={<ExpandMoreIcon />}
              aria-controls="photometry-content"
              id="photometry-header"
              className={classes.accordionSummary}
              style={{ justifyContent: "space-between" }}
            >
              <div
                className={classes.flexRow}
                style={{
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "0.5rem",
                  width: "100%",
                  marginRight: "0.5rem",
                }}
              >
                <Typography className={classes.accordionHeading}>
                  Photometry
                </Typography>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    flexDirection: "row",
                    gap: "0.5rem",
                  }}
                >
                  <DisplayPhotStats photstats={source.photstats[0]} />
                  <PhotometryMagsys magsys={magsys} setMagsys={setMagsys} />
                  <div
                    style={{
                      display: "flex",
                      gap: "0.25rem",
                      alignItems: "center",
                    }}
                  >
                    <Tooltip
                      title={`On click, correct photometry for extinction, using G23 extinction law with Rv=3.1 (currently ${
                        showExtinctionCorrection ? "" : "NOT"
                      } corrected)`}
                    >
                      <div className={classes.switchContainer}>
                        <Button
                          size="small"
                          variant={
                            showExtinctionCorrection ? "contained" : "outlined"
                          }
                          style={{
                            height: "1.5rem",
                            fontSize: "0.75rem",
                            marginTop: "-0.2rem",
                          }}
                          onClick={(e: any) => {
                            e.stopPropagation();
                            setShowExtinctionCorrection(
                              !showExtinctionCorrection,
                            );
                          }}
                        >
                          Extinction
                        </Button>
                      </div>
                    </Tooltip>
                  </div>
                </div>
              </div>
            </AccordionSummary>
            <AccordionDetails className={classes.accordionPlot}>
              <Grid container id="photometry-container">
                <div className={classes.plotContainer}>
                  {!source.photometry_exists && (
                    <div style={{ marginLeft: "1rem" }}>
                      {" "}
                      No photometry exists{" "}
                    </div>
                  )}
                  {source.photometry_exists && (
                    <PhotometryPlot
                      obj_id={source.id}
                      dm={source.dm}
                      annotations={source?.annotations || []}
                      spectra={spectra || []}
                      gcn_events={source.gcn_crossmatch || []}
                      duplicates={source.duplicates || []}
                      associated_objs={source.associated_objs || []}
                      magsys={magsys}
                      plotStyle={{
                        height: rightPanelVisible ? "65vh" : "75vh",
                      }}
                      mode={downMd ? "mobile" : "desktop"}
                      t0={source.t0}
                      showExtinctionCorrection={showExtinctionCorrection}
                      is_roid={source.is_roid}
                    />
                  )}
                </div>
                <div className={classes.buttonContainer}>
                  <Button
                    secondary
                    onClick={() => {
                      setShowPhotometry(true);
                    }}
                    data-testid="show-photometry-table-button"
                    disabled={source?.photometry_exists === false}
                  >
                    Photometry Table
                  </Button>
                  {!isReadOnly && (
                    <Link to={`/share_data/${source.id}`} role="link">
                      <Button secondary data-testid="tour-source-share">
                        Share data
                      </Button>
                    </Link>
                  )}
                  {!isReadOnly && (
                    <Link to={`/upload_photometry/${source.id}`} role="link">
                      <Button secondary data-testid="tour-source-upload">
                        Upload photometry
                      </Button>
                    </Link>
                  )}
                  {source?.photometry_exists && (
                    <Link to={`/source/${source.id}/periodogram`} role="link">
                      <Button secondary>Periodogram Analysis</Button>
                    </Link>
                  )}
                </div>
              </Grid>
            </AccordionDetails>
          </Accordion>
        </Grid>
        <Grid
          size={12}
          sx={{
            order: { xs: 5, md: 7 },
          }}
        >
          <Accordion
            defaultExpanded
            disableGutters
            className={classes.flexColumn}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="spectroscopy-content"
              id="spectroscopy-header"
            >
              <Typography className={classes.accordionHeading}>
                Spectroscopy
              </Typography>
            </AccordionSummary>
            <AccordionDetails className={classes.accordionPlot}>
              <Grid container id="spectroscopy-container">
                <div className={classes.plotContainer}>
                  {!source.spectrum_exists &&
                    (!spectra || spectra?.length === 0) &&
                    unsharedSpectraCount === 0 && (
                      <div style={{ marginLeft: "1rem" }}>
                        {" "}
                        No spectrum exists{" "}
                      </div>
                    )}
                  {source.spectrum_exists &&
                    (!spectra || spectra?.length === 0) && (
                      <CircularProgress color="secondary" />
                    )}
                  {source?.spectrum_exists && (spectra?.length ?? 0) > 0 && (
                    <Suspense
                      fallback={
                        <div>
                          <CircularProgress color="secondary" />
                        </div>
                      }
                    >
                      <SpectraPlot
                        spectra={spectra ?? []}
                        redshift={source.redshift || 0}
                        plotStyle={{
                          height: rightPanelVisible ? "55vh" : "70vh",
                        }}
                        mode={downMd ? "mobile" : "desktop"}
                      />
                    </Suspense>
                  )}
                  {!isReadOnly && <UnsharedSpectra sourceID={source.id} />}
                </div>
                <div className={classes.buttonContainer}>
                  {!isReadOnly && (
                    <Link to={`/share_data/${source.id}`} role="link">
                      <Button secondary>Share data</Button>
                    </Link>
                  )}
                  {!isReadOnly && (
                    <Link to={`/upload_spectrum/${source.id}`} role="link">
                      <Button secondary>Upload spectroscopy</Button>
                    </Link>
                  )}
                </div>
              </Grid>
            </AccordionDetails>
          </Accordion>
        </Grid>
        <Grid
          size={12}
          sx={{
            order: { xs: 10, md: 11, lg: 9 },
          }}
        >
          <Accordion
            defaultExpanded
            disableGutters
            className={classes.flexColumn}
            data-testid="tour-source-followup"
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="followup-content"
              id="followup-header"
            >
              <Typography className={classes.accordionHeading}>
                Follow-up
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <div
                className={classes.flexColumn}
                style={{ overflow: "hidden" }}
              >
                {!isReadOnly && (
                  <FollowupRequestForm
                    obj_id={source.id}
                    instrumentList={instrumentList}
                    instrumentFormParams={instrumentFormParams}
                    vlaRubinAlert={source.vla_rubin_alert}
                    {...({ action: "createNew" } as any)}
                  />
                )}
                <FollowupRequestLists
                  followupRequests={source.followup_requests}
                  instrumentList={instrumentList}
                  instrumentFormParams={instrumentFormParams}
                  showEmptyMessage={isReadOnly}
                />
              </div>
            </AccordionDetails>
          </Accordion>
        </Grid>
        <Grid
          size={12}
          sx={{
            order: { xs: 11, md: 12, lg: 10 },
          }}
        >
          <Accordion disableGutters className={classes.flexColumn}>
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="followup-content"
              id="forced-photometry-header"
            >
              <Typography className={classes.accordionHeading}>
                Forced Photometry
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <div
                className={classes.flexColumn}
                style={{ overflow: "hidden" }}
              >
                {!isReadOnly && (
                  <FollowupRequestForm
                    obj_id={source.id}
                    instrumentList={instrumentList}
                    instrumentFormParams={instrumentFormParams}
                    requestType="forced_photometry"
                    {...({ action: "createNew" } as any)}
                  />
                )}
                <FollowupRequestLists
                  followupRequests={source.followup_requests}
                  instrumentList={instrumentList}
                  instrumentFormParams={instrumentFormParams}
                  requestType="forced_photometry"
                  showEmptyMessage={isReadOnly}
                />
              </div>
            </AccordionDetails>
          </Accordion>
        </Grid>
        <Grid
          size={12}
          sx={{
            order: { xs: 12, md: 13, lg: 11 },
          }}
        >
          <Accordion
            defaultExpanded
            disableGutters
            className={classes.flexColumn}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="followup-content"
              id="observing-run-header"
            >
              <Typography className={classes.accordionHeading}>
                Assign Target to Observing Run
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <div
                className={classes.flexColumn}
                style={{ overflow: "hidden" }}
              >
                {!isReadOnly && (
                  <AssignmentForm
                    obj_id={source.id}
                    observingRunList={observingRunList}
                  />
                )}
                <AssignmentList
                  assignments={source.assignments}
                  showEmptyMessage={isReadOnly}
                />
              </div>
            </AccordionDetails>
          </Accordion>
        </Grid>
        <Grid
          size={12}
          sx={{
            order: 16,
          }}
        >
          <Paper className={classes.flexColumn} sx={{ p: 2, gap: 1.5 }}>
            <Typography
              id="analysis-header"
              className={classes.accordionHeading}
            >
              External Analysis
            </Typography>
            <AnalysisList
              obj_id={source.id}
              onAdd={isReadOnly ? undefined : () => setAnalysisDialogOpen(true)}
            />
            {!isReadOnly && (
              <Dialog
                open={analysisDialogOpen}
                onClose={() => setAnalysisDialogOpen(false)}
                maxWidth="md"
                fullWidth
              >
                <DialogTitle>New analysis</DialogTitle>
                <DialogContent>
                  <div style={{ paddingTop: 8 }}>
                    <AnalysisForm
                      obj_id={source.id}
                      onStarted={() => setAnalysisDialogOpen(false)}
                    />
                  </div>
                </DialogContent>
              </Dialog>
            )}
          </Paper>
        </Grid>
        {downLg || !rightPanelVisible
          ? rightPanelContent(downLg, rightPanelVisible)
          : null}
      </Grid>
      <Grid size={rightPanelVisible && !downLg ? 5 : 12}>
        <Grid container spacing={1.5} columns={{ xs: 6 }}>
          {rightPanelVisible && !downLg
            ? rightPanelContent(downLg, rightPanelVisible)
            : null}
        </Grid>
        <PhotometryTable
          obj_id={source.id}
          open={showPhotometry}
          onClose={closePhotometryTable}
          magsys={magsys}
          setMagsys={setMagsys}
          t0={source.t0}
        />
      </Grid>
    </Grid>
  );
};

interface SourceProps {
  route: any;
}

const Source = ({ route }: SourceProps) => {
  const {
    data: source,
    isError,
    error,
    isLoading,
    isSuccess,
  } = useGetSourceQuery(route.id);
  const [addSourceView] = useAddSourceViewMutation();

  useEffect(() => {
    if (isSuccess && source?.id !== undefined) {
      addSourceView(route.id);
    }
  }, [isSuccess, source?.id, route.id, addSourceView]);

  if (isError) return (error as any)?.error ?? "Error while loading source";
  // The name is known from the route, so the page keeps its shape while the
  // rest arrives instead of going blank behind a whole-page spinner.
  if (isLoading || !source) return <SourceSkeleton objId={route.id} />;
  if (source.id === undefined) return "Source not found";
  // eslint-disable-next-line react-hooks/immutability
  document.title = source.id;

  return <SourceContent source={source} />;
};

export default withRouter(Source);
