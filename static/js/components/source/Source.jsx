import React, { useEffect, useState, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import makeStyles from "@mui/styles/makeStyles";
import Grid from "@mui/material/Grid";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Typography from "@mui/material/Typography";
import { log10, abs, ceil } from "mathjs";

import CircularProgress from "@mui/material/CircularProgress";
import AddIcon from "@mui/icons-material/Add";
import RemoveIcon from "@mui/icons-material/Remove";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import useMediaQuery from "@mui/material/useMediaQuery";
import KeyboardArrowLeftIcon from "@mui/icons-material/KeyboardArrowLeft";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";

import withRouter from "../withRouter";

import ThumbnailsOnPage from "../thumbnail/ThumbnailsOnPage";
import CopyPhotometryDialog from "./CopyPhotometryDialog";
import ClassificationList from "../classification/ClassificationList";
import ClassificationForm from "../classification/ClassificationForm";
import ShowClassification from "../classification/ShowClassification";
import ShowSummaries from "../summary/ShowSummaries";
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
import SimilarSources from "./SimilarSources";
import UpdateSourceGCNCrossmatch from "./UpdateSourceGCNCrossmatch";
import UpdateSourceMPC from "./UpdateSourceMPC";
import UpdateSourceRedshift from "./UpdateSourceRedshift";
import UpdateSourceSummary from "./UpdateSourceSummary";
import UpdateSourceTNS from "./UpdateSourceTNS";
import StartBotSummary from "../StartBotSummary";
import SourceGCNCrossmatchList from "./SourceGCNCrossmatchList";
import SourceRedshiftHistory from "./SourceRedshiftHistory";
import SourceCandidatesHistory from "./SourceCandidatesHistory";
import ShowSummaryHistory from "../summary/ShowSummaryHistory";
import AnnotationsTable from "./AnnotationsTable";
import GcnNotesTable from "../gcn/GcnNotesTable";
import AnalysisList from "../analysis/AnalysisList";
import AnalysisForm from "../analysis/AnalysisForm";
import SourceSaveHistory from "./SourceSaveHistory";
import PhotometryTable from "../photometry/PhotometryTable";
import FavoritesButton from "../listing/FavoritesButton";
import SourceAnnotationButtons from "./SourceAnnotationButtons";
import TNSATForm from "../tns/TNSATForm";
import Reminders from "../Reminders";
import QuickSaveButton from "./QuickSaveSource";
import Spinner from "../Spinner";
import Button from "../Button";

import SourcePlugins from "./SourcePlugins";

import * as photometryActions from "../../ducks/photometry";
import * as spectraActions from "../../ducks/spectra";
import * as sourceActions from "../../ducks/source";

import PhotometryPlot from "../plot/PhotometryPlot";
import SpectraPlot from "../plot/SpectraPlot";
import PhotometryMagsys from "../photometry/PhotometryMagsys";
import SourcePublish from "./source_publish/SourcePublish";
import SourceCoordinates from "./SourceCoordinates";

const CommentList = React.lazy(() => import("../comment/CommentList"));
const CommentListMobile = React.lazy(
  () => import("../comment/CommentListMobile"),
);

const VegaHR = React.lazy(() => import("../plot/VegaHR"));

const CentroidPlot = React.lazy(
  () => import(/* webpackChunkName: "CentroidPlot" */ "../plot/CentroidPlot"),
);

export const useSourceStyles = makeStyles((theme) => ({
  header: {
    display: "flex",
    justifyContent: "space-between",
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
  noSpace: { padding: 0, margin: 0 },
  dropdownText: { textDecoration: "none", color: "black" },
  noWrapMargin: {
    marginRight: "0.5rem",
    textWrap: "nowrap",
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
  smallPlot: {
    width: "350px",
    overflow: "auto",
  },
  panelButton: {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.primary.contrastText,
    "&:hover": {
      color: theme.palette.primary.main,
    },
  },
  thumbnailGridDialog: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gap: "1rem",
  },
  comments: {
    width: "100%",
  },
  hr_diagram: {},
  container: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "0.25rem",
  },
  sourceInfo: {
    display: "flex",
    flexFlow: "row wrap",
    alignItems: "center",
  },
  infoLine: {
    // Get it's own line
    flexBasis: "100%",
    display: "flex",
    flexFlow: "row wrap",
    gap: "0.5rem",
  },
  rowInfo: {
    display: "flex",
    flexDirection: "row",
    alignItems: "center",
  },
  dmdlInfo: {
    alignSelf: "center",
    "&>div": {
      display: "inline",
      padding: "0.25rem 0.5rem 0.25rem 0",
    },
  },
  sourceCandidates: {
    marginLeft: "0.1rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
}));

const SourceContent = ({ source }) => {
  const dispatch = useDispatch();
  const classes = useSourceStyles();

  const currentUser = useSelector((state) => state.profile);
  const groups = (useSelector((state) => state.groups.all) || []).filter(
    (g) => !g.single_user_group,
  );
  const spectra = useSelector((state) => state.spectra)[source.id];
  const associatedGCNs = useSelector((state) => state.source.associatedGCNs);

  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments,
  );
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const { taxonomyList } = useSelector((state) => state.taxonomies);

  const [copyPhotometryDialogOpen, setCopyPhotometryDialogOpen] =
    useState(false);
  const [tnsDialogOpen, setTNSDialogOpen] = useState(false);

  // Needed for buttons that open popover menus, indicates where the popover should be anchored
  // (where it will appear on the screen)
  const [anchorElFindingChart, setAnchorElFindingChart] = React.useState(null);
  const [anchorElObservability, setAnchorElObservability] =
    React.useState(null);
  const openFindingChart = Boolean(anchorElFindingChart);
  const openObservability = Boolean(anchorElObservability);

  const [showStarList, setShowStarList] = useState(false);
  const [showPhotometry, setShowPhotometry] = useState(false);
  const [rightPanelVisible, setRightPanelVisible] = useState(true);
  const [magsys, setMagsys] = useState("ab");

  const downSm = useMediaQuery((theme) => theme.breakpoints.down("sm"));
  const downMd = useMediaQuery((theme) => theme.breakpoints.down("md"));
  const downLg = useMediaQuery((theme) => theme.breakpoints.down("lg"));

  const [hovering, setHovering] = useState(null);

  const spectrumAnnotations = [];
  if (spectra) {
    spectra.forEach((spec) => {
      spec.annotations.forEach((annotation) => {
        annotation.spectrum_observed_at = spec.observed_at;
        spectrumAnnotations.push(annotation);
      });
    });
  }

  const noSummary =
    source.summary_history?.length < 1 ||
    !source.summary_history ||
    source.summary_history.filter(
      (summary) => summary.summary !== null && summary.summary.trim() !== "",
    )?.length < 1;

  const noHumanSummary =
    source.summary_history?.length < 1 ||
    !source.summary_history ||
    source.summary_history[0].summary === null ||
    source.summary_history[0].summary === "" ||
    source.summary_history.filter(
      (summary) =>
        summary.summary !== null &&
        summary.summary.trim() !== "" &&
        summary.is_bot === false,
    )?.length < 1;

  // associatedGCNs is an array of dateobs
  // source.gcn_crossmatch is an array of objects with dateobs
  // we want to combine these two arrays into one array of dateobs deduplicated
  // and sorted by date in descending order
  const gcn_crossmatches = (associatedGCNs || [])
    .concat((source.gcn_crossmatch || []).map((gcn) => gcn.dateobs))
    .filter((gcn, index, self) => self.indexOf(gcn) === index)
    .sort((a, b) => new Date(b) - new Date(a));

  useEffect(() => {
    dispatch(photometryActions.fetchSourcePhotometry(source.id, { magsys }));
    dispatch(spectraActions.fetchSourceSpectra(source.id));
    dispatch(sourceActions.fetchPosition(source.id));
    dispatch(sourceActions.fetchAssociatedGCNs(source.id));
  }, [source.id, magsys, dispatch]);

  const getZRound = (redshift_error) =>
    redshift_error ? ceil(abs(log10(redshift_error))) : 4;

  const setHost = (galaxyName) => {
    dispatch(sourceActions.addHost(source.id, { galaxyName }));
  };

  const removeHost = () => {
    dispatch(sourceActions.removeHost(source.id));
  };

  const handleHover = (type) => {
    if (hovering !== type) {
      setHovering(type);
    }
  };

  const handleStopHover = (type) => {
    // here we only trigger if we stopped hovering the currently hovered item
    if (hovering === type) {
      setHovering(null);
    }
  };

  const rightPanelContent = (downLarge, isRightPanelVisible) => (
    <>
      <Grid item xs={12} lg={6} order={{ xs: 6, md: 4, lg: 3 }}>
        <Accordion
          defaultExpanded
          disableGutters
          className={classes.flexColumn}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="annotations-content"
            id="annotations-header"
          >
            <Typography className={classes.accordionHeading}>
              Auto-annotations
            </Typography>
          </AccordionSummary>
          <AccordionDetails
            style={{
              padding: 0,
              minHeight: !(downLarge || isRightPanelVisible) ? "60vh" : "52vh",
            }}
          >
            <AnnotationsTable
              annotations={source.annotations}
              spectrumAnnotations={spectrumAnnotations}
            />
          </AccordionDetails>
          <AccordionDetails style={{ padding: "0.5rem" }}>
            <SourceAnnotationButtons source={source} />
          </AccordionDetails>
        </Accordion>
      </Grid>
      {source?.gcn_notes?.length > 0 && (
        <Grid
          item
          xs={12}
          lg={12}
          order={{ xs: 7, md: 5, lg: !downLg && !rightPanelVisible ? 5 : 4 }}
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
                minHeight: !(downLarge || isRightPanelVisible)
                  ? "40vh"
                  : "30vh",
              }}
            >
              <GcnNotesTable gcnNotes={source.gcn_notes} />
            </AccordionDetails>
          </Accordion>
        </Grid>
      )}
      <Grid
        item
        xs={12}
        lg={6}
        order={{ xs: 3, md: 3, lg: !downLg && !rightPanelVisible ? 4 : 5 }}
      >
        <Accordion
          defaultExpanded
          className={classes.flexColumn}
          data-testid="comments-accordion"
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="comments-content"
            id="comments-header"
          >
            <Typography className={classes.accordionHeading}>
              Comments
            </Typography>
          </AccordionSummary>
          <AccordionDetails
            style={{
              minHeight: !(downLarge || isRightPanelVisible)
                ? "63.5vh"
                : "55.5vh",
            }}
          >
            <Suspense fallback={<CircularProgress />}>
              {downLarge ? (
                <CommentListMobile />
              ) : (
                <CommentList
                  maxHeightList={
                    !(downLarge || isRightPanelVisible) ? "28.5vh" : "350px"
                  }
                />
              )}
            </Suspense>
          </AccordionDetails>
        </Accordion>
      </Grid>
      <Grid item xs={12} lg={12} order={{ xs: 13, md: 10, lg: 8 }}>
        <Accordion
          defaultExpanded
          disableGutters
          className={classes.flexColumn}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="classifications-content"
            id="classifications-header"
          >
            <Typography className={classes.accordionHeading}>
              Classifications
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={classes.classifications}>
              <ClassificationList />
              <ClassificationForm
                obj_id={source.id}
                action="createNew"
                taxonomyList={taxonomyList}
              />
            </div>
          </AccordionDetails>
        </Accordion>
      </Grid>
      <Grid item xs={12} lg={6} order={{ xs: 8, md: 8, lg: 12 }}>
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
            <Suspense
              fallback={
                <div>
                  <CircularProgress color="secondary" />
                </div>
              }
            >
              <CentroidPlot
                sourceId={source.id}
                plotStyle={{
                  height: "50vh",
                }}
              />
            </Suspense>
          </AccordionDetails>
        </Accordion>
      </Grid>
      <Grid item xs={12} lg={6} order={{ xs: 9, md: 9, lg: 13 }}>
        <Accordion
          defaultExpanded
          disableGutters
          className={classes.classifications}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="hr-diagram-content"
            id="hr-diagram-header"
          >
            <Typography className={classes.accordionHeading}>
              HR Diagram
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div
              className={classes.hr_diagram}
              data-testid={`hr_diagram_${source.id}`}
            >
              {source.color_magnitude?.length > 0 ? (
                <Suspense
                  fallback={
                    <div>
                      <CircularProgress color="secondary" />
                    </div>
                  }
                >
                  <VegaHR
                    data={source.color_magnitude}
                    width={300}
                    height={300}
                  />
                </Suspense>
              ) : (
                <div>No color magnitude for this source</div>
              )}
            </div>
          </AccordionDetails>
        </Accordion>
      </Grid>
      <Grid
        item
        xs={14}
        lg={6}
        order={{ xs: 13, md: 13, lg: 13 }}
        style={{ overflow: "auto", paddingBottom: "1px", paddingRight: "1px" }}
      >
        <Accordion
          defaultExpanded
          disableGutters
          className={classes.flexColumn}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="analysis-content"
            id="analysis-header"
          >
            <Typography className={classes.accordionHeading}>
              External Analysis
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <AnalysisList obj_id={source.id} />
          </AccordionDetails>
          <AccordionDetails>
            <AnalysisForm obj_id={source.id} />
          </AccordionDetails>
        </Accordion>
      </Grid>
      <Grid item xs={12} lg={6} order={{ xs: 15, md: 15, lg: 15 }}>
        <Accordion
          defaultExpanded
          disableGutters
          className={classes.flexColumn}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="notifications-content"
            id="notifications-header"
          >
            <Typography className={classes.accordionHeading}>
              Source Notification
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <SourceNotification sourceId={source.id} />
          </AccordionDetails>
          <AccordionDetails>
            <Reminders resourceId={source.id} resourceType="source" />
          </AccordionDetails>
        </Accordion>
      </Grid>
    </>
  );

  return (
    <Grid container spacing={1.5}>
      <Grid
        container
        item
        spacing={1.5}
        xs={12}
        lg={rightPanelVisible && !downLg ? 7 : 12}
        style={{
          display: downLg || (!downLg && !rightPanelVisible) ? "flex" : "block",
        }}
      >
        <Grid item xs={12} order={{ xs: 1, md: 1, lg: 1 }}>
          <Paper style={{ padding: "0.5rem" }}>
            <div className={classes.container}>
              <div className={classes.header}>
                <FavoritesButton sourceID={source.id} />
                <h6 className={classes.name}>{source.id}</h6>
                <div className={classes.sourceCandidates}>
                  <SourceCandidatesHistory
                    candidates={source?.candidates || []}
                  />
                </div>
              </div>
              {!downLg && (
                <div className={classes.container}>
                  <IconButton
                    onClick={() => setRightPanelVisible(!rightPanelVisible)}
                    data-testid={`${
                      rightPanelVisible ? "hide" : "show"
                    }-right-panel-button`}
                    size="small"
                    variant="contained"
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
            <div style={{ marginBottom: "0.25rem" }}>
              <ShowClassification
                classifications={source.classifications}
                taxonomyList={taxonomyList}
                shortened
              />
            </div>
            <SourceCoordinates classes={classes} source={source} />
            <div
              className={classes.flexRow}
              style={{
                flexBasis: "100%",
                flexFlow: "wrap",
                alignItems: "baseline",
              }}
            >
              <div>
                <b>Redshift: &nbsp;</b>
                {source.redshift &&
                  source.redshift.toFixed(getZRound(source.redshift_error))}
                {source.redshift_error && <b>&nbsp; &plusmn; &nbsp;</b>}
                {source.redshift_error &&
                  source.redshift_error.toFixed(
                    getZRound(source.redshift_error),
                  )}
                <UpdateSourceRedshift source={source} />
                <SourceRedshiftHistory
                  redshiftHistory={source.redshift_history}
                />
              </div>
              <div className={classes.dmdlInfo}>
                {source.dm && (
                  <div>
                    <b>DM: &nbsp;</b>
                    {source.dm.toFixed(3)}
                    &nbsp; mag
                  </div>
                )}
                {source.luminosity_distance && (
                  <div>
                    <b>
                      <i>D</i>
                      <sub>L</sub>: &nbsp;
                    </b>
                    {source.luminosity_distance.toFixed(2)}
                    &nbsp; Mpc
                  </div>
                )}
              </div>
            </div>
            <div
              className={classes.flexRow}
              style={{
                justifyContent: "flex-start",
                alignItems: "baseline",
                flexFlow: "wrap",
                columnGap: "1rem",
              }}
            >
              <div
                className={classes.rowInfo}
                onMouseEnter={() => handleHover("tns")}
                onMouseLeave={() => handleStopHover("tns")}
              >
                <b>TNS Name: &nbsp;</b>
                {source.tns_name && (
                  <a
                    key={source.tns_name}
                    href={`https://www.wis-tns.org/object/${
                      source.tns_name.trim().includes(" ")
                        ? source.tns_name.split(" ")[1]
                        : source.tns_name
                    }`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {`${source.tns_name}`}
                  </a>
                )}
                {source.tns_info && (
                  <DisplayTNSInfo
                    tns_info={source.tns_info}
                    display_header={false}
                  />
                )}
                {hovering === "tns" && <UpdateSourceTNS source={source} />}
              </div>
              <div
                className={classes.rowInfo}
                onMouseEnter={() => handleHover("mpc")}
                onMouseLeave={() => handleStopHover("mpc")}
              >
                <b>MPC Name: &nbsp;</b>
                <div key="mpc_name"> {source.mpc_name} </div>
                {hovering === "mpc" && <UpdateSourceMPC source={source} />}
              </div>
              <div
                className={classes.rowInfo}
                onMouseEnter={() => handleHover("gcn")}
                onMouseLeave={() => handleStopHover("gcn")}
              >
                <b>GCN Crossmatches: &nbsp;</b>
                {source.gcn_crossmatch?.length > 0 && (
                  <SourceGCNCrossmatchList
                    gcn_crossmatches={gcn_crossmatches}
                  />
                )}
                {hovering === "gcn" && (
                  <UpdateSourceGCNCrossmatch source={source} />
                )}
              </div>
              {source.alias ? (
                <div className={classes.rowInfo}>
                  <b>Aliases: &nbsp;</b>
                  <div key="aliases"> {source.alias.join(", ")} </div>
                </div>
              ) : null}
            </div>
            {source.host && (
              <div className={classes.infoLine}>
                <div className={classes.sourceInfo}>
                  <b className={classes.noWrapMargin}>
                    {`Host galaxy: ${source.host.name}`}
                  </b>
                  <b className={classes.noWrapMargin}>
                    {`Offset: ${source.host_offset.toFixed(3)} [arcsec]`}
                  </b>
                  <b className={classes.noWrapMargin}>
                    {`Distance: ${source.host_distance.toFixed(1)} [kpc]`}
                  </b>
                  <IconButton
                    size="small"
                    name="removeHostGalaxyButton"
                    onClick={() => removeHost()}
                    className={classes.noSpace}
                  >
                    <RemoveIcon style={{ fontSize: "1rem" }} />
                  </IconButton>
                </div>
              </div>
            )}
            {source?.galaxies?.length > 0 &&
              !(
                source.galaxies?.length === 1 &&
                source.host?.name &&
                (source?.galaxies || []).includes(source.host?.name)
              ) && (
                <div className={classes.sourceInfo}>
                  <b className={classes.noWrapMargin}>
                    <font color="#457b9d">Possible host galaxies:</font>
                  </b>
                  <div
                    className={classes.flexRow}
                    style={{
                      width: "auto",
                      alignItems: "center",
                      flexFlow: "wrap",
                      columnGap: "0.25rem",
                    }}
                  >
                    {source.galaxies.map(
                      (galaxyName) =>
                        galaxyName !== source.host?.name && (
                          <div key={galaxyName}>
                            <Button
                              size="small"
                              className={classes.noSpace}
                              onClick={() => setHost(galaxyName)}
                            >
                              {galaxyName}
                            </Button>
                          </div>
                        ),
                    )}
                  </div>
                </div>
              )}
            {source?.duplicates?.length > 0 && (
              <div className={classes.sourceInfo}>
                <b className={classes.noWrapMargin}>
                  <font color="#457b9d">Possible duplicate of:</font>
                </b>
                <div
                  className={classes.flexRow}
                  style={{
                    width: "auto",
                    alignItems: "center",
                    flexFlow: "wrap",
                    columnGap: "0.25rem",
                  }}
                >
                  {source.duplicates.map((duplicate) => (
                    <div key={duplicate.obj_id}>
                      <Tooltip
                        title={`${duplicate.separation.toFixed(2)} arcsec`}
                      >
                        <Link
                          to={`/source/${duplicate.obj_id}`}
                          role="link"
                          key={duplicate.obj_id}
                          className={classes.noSpace}
                        >
                          <Button size="small" className={classes.noSpace}>
                            {duplicate.obj_id}
                          </Button>
                        </Link>
                      </Tooltip>
                      <IconButton
                        size="small"
                        name={`copySourceButton${duplicate.obj_id}`}
                        onClick={() => setCopyPhotometryDialogOpen(true)}
                        className={classes.noSpace}
                      >
                        <AddIcon style={{ fontSize: "1rem" }} />
                      </IconButton>
                      <CopyPhotometryDialog
                        source={source}
                        duplicate={duplicate}
                        dialogOpen={copyPhotometryDialogOpen}
                        closeDialog={setCopyPhotometryDialogOpen}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}
            {source.summary_history?.length > 0 &&
            currentUser?.preferences?.showSimilarSources === true ? (
              <SimilarSources source={source} min_score={0.9} k={3} />
            ) : null}
            <div className={classes.infoLine} style={{ marginTop: "0.25rem" }}>
              <SourcePlugins source={source} />
              <div className={classes.infoButton}>
                <Button
                  aria-controls={openFindingChart ? "basic-menu" : undefined}
                  aria-haspopup="true"
                  aria-expanded={openFindingChart ? "true" : undefined}
                  onClick={(e) => setAnchorElFindingChart(e.currentTarget)}
                  secondary
                  size="small"
                >
                  Finding Chart
                </Button>
                <Menu
                  transitionDuration={50}
                  id="finding-chart-menu"
                  anchorEl={anchorElFindingChart}
                  open={openFindingChart}
                  onClose={() => setAnchorElFindingChart(null)}
                  MenuListProps={{
                    "aria-labelledby": "basic-button",
                  }}
                >
                  <MenuItem onClick={() => setAnchorElFindingChart(null)}>
                    <a
                      href={`/api/sources/${source.id}/finder`}
                      download="finder-chart-pdf"
                      className={classes.dropdownText}
                    >
                      PDF
                    </a>
                  </MenuItem>
                  <MenuItem onClick={() => setAnchorElFindingChart(null)}>
                    <Link
                      to={`/source/${source.id}/finder`}
                      role="link"
                      className={classes.dropdownText}
                      target="_blank"
                    >
                      Interactive
                    </Link>
                  </MenuItem>
                </Menu>
              </div>
              <div className={classes.infoButton}>
                <Button
                  secondary
                  size="small"
                  onClick={() => setShowStarList(!showStarList)}
                >
                  {showStarList ? "Hide Starlist" : "Show Starlist"}
                </Button>
              </div>
              <div className={classes.infoButton}>
                <Button
                  aria-controls={openObservability ? "basic-menu" : undefined}
                  aria-haspopup="true"
                  aria-expanded={openObservability ? "true" : undefined}
                  onClick={(e) => setAnchorElObservability(e.currentTarget)}
                  secondary
                  size="small"
                >
                  Observability
                </Button>
                <Menu
                  transitionDuration={50}
                  id="observability-chart-menu"
                  anchorEl={anchorElObservability}
                  open={openObservability}
                  onClose={() => setAnchorElObservability(null)}
                  MenuListProps={{
                    "aria-labelledby": "basic-button",
                  }}
                >
                  <MenuItem onClick={() => setAnchorElObservability(null)}>
                    <a
                      href={`/api/sources/${source.id}/observability`}
                      download={`observabilityChartRequest-${source.id}`}
                      data-testid={`observabilityChartRequest_${source.id}`}
                      className={classes.dropdownText}
                    >
                      PDF
                    </a>
                  </MenuItem>
                  <MenuItem onClick={() => setAnchorElObservability(null)}>
                    <Link
                      to={`/observability/${source.id}`}
                      role="link"
                      className={classes.dropdownText}
                      target="_blank"
                    >
                      Interactive
                    </Link>
                  </MenuItem>
                </Menu>
              </div>
              <div className={classes.infoButton}>
                <Button
                  secondary
                  size="small"
                  data-testid={`tnsSubmissionForm_${source.id}`}
                  onClick={() => {
                    setTNSDialogOpen(true);
                  }}
                >
                  Submit to TNS
                </Button>
                <Dialog
                  open={tnsDialogOpen}
                  onClose={() => setTNSDialogOpen(false)}
                  style={{ position: "fixed" }}
                >
                  <DialogTitle>Submit to TNS</DialogTitle>
                  <DialogContent>
                    <TNSATForm
                      obj_id={source.id}
                      submitCallback={() => setTNSDialogOpen(false)}
                    />
                  </DialogContent>
                </Dialog>
              </div>
              {currentUser?.preferences?.hideSourceSummary === true ? (
                <div className={classes.infoButton}>
                  <ShowSummaryHistory
                    summaries={source.summary_history || []}
                    obj_id={source.id}
                    button
                  />
                </div>
              ) : null}
              <SourcePublish
                sourceId={source.id}
                isElements={{
                  summary: source.summary_history?.length > 0,
                  photometry: source.photometry_exists,
                  classifications: source.classifications?.length > 0,
                }}
              />
            </div>
            {/* checking if the id exists is a way to know if the user profile is loaded or not */}
            {currentUser?.id &&
              currentUser?.preferences?.hideSourceSummary !== true && (
                <Paper
                  className={classes.flexColumn}
                  style={{
                    marginTop: "0.5rem",
                    padding: noSummary
                      ? "0.5rem 0 0.5rem 0.5rem"
                      : "0.25rem 0.25rem 0 0.25rem",
                  }}
                  variant={noSummary ? "contained" : "outlined"}
                  elevation={noSummary ? 1 : 0}
                >
                  <ShowSummaries
                    summaries={source.summary_history || []}
                    showAISummaries={
                      currentUser?.preferences?.showAISourceSummary || false
                    }
                  />
                  <div
                    className={classes.flexRow}
                    style={{
                      justifyContent: noSummary ? "space-between" : "flex-end",
                      alignItems: "center",
                      maxHeight: "1rem",
                      width: "100%",
                    }}
                  >
                    {noSummary ? (
                      <p
                        className={classes.noSpace}
                        style={{
                          fontSize: "0.75rem",
                          color: "grey",
                          marginRight: "0.25rem",
                        }}
                      >
                        {`No${noHumanSummary ? " (human) " : " "}summary yet.`}
                      </p>
                    ) : null}
                    <div
                      className={classes.flexRow}
                      style={{
                        alignItems: "center",
                        width: "auto",
                        marginTop: noSummary ? "0.25rem" : 0,
                      }}
                    >
                      <UpdateSourceSummary
                        source={source}
                        showAISummaries={
                          currentUser?.preferences?.showAISourceSummary || false
                        }
                      />
                      {source.comments?.length > 0 ||
                      source.classifications?.length > 0 ? (
                        <StartBotSummary obj_id={source.id} />
                      ) : null}
                      {source.summary_history?.length > 0 ? (
                        <ShowSummaryHistory
                          summaries={source.summary_history}
                          obj_id={source.id}
                        />
                      ) : null}
                    </div>
                  </div>
                </Paper>
              )}
            <div
              className={classes.flexRow}
              style={{
                justifyContent: "flex-start",
                alignItems: "center",
                flexFlow: "wrap",
                gap: "0.5rem",
                paddingTop: "0.25rem",
              }}
            >
              <div
                className={classes.flexRow}
                style={{
                  alignItems: "center",
                  flexFlow: "wrap",
                  gap: "0.25rem",
                  width: "auto",
                }}
              >
                {source.groups?.map((group) => (
                  <Tooltip
                    title={`Saved at ${group.saved_at} by ${group.saved_by?.username}`}
                    key={group.id}
                  >
                    <Chip
                      label={
                        group.nickname
                          ? group.nickname.substring(0, 15)
                          : group.name.substring(0, 15)
                      }
                      size="small"
                      className={classes.noSpace}
                      data-testid={`groupChip_${group.id}`}
                    />
                  </Tooltip>
                ))}
              </div>
              <div
                className={classes.flexRow}
                style={{ alignItems: "center", width: "auto" }}
              >
                <EditSourceGroups
                  source={{
                    id: source.id,
                    currentGroupIds: source.groups?.map((g) => g.id),
                  }}
                  groups={groups}
                  icon
                />
                <SourceSaveHistory groups={source.groups} />
                <QuickSaveButton
                  sourceId={source.id}
                  alreadySavedGroups={source.groups?.map((g) => g.id)}
                />
              </div>
            </div>
            {showStarList && (
              <div style={{ paddingTop: "0.5rem" }}>
                <StarList sourceId={source.id} />
              </div>
            )}
            <div style={{ paddingTop: "0.25rem" }}>
              <ThumbnailsOnPage
                ra={source.ra}
                dec={source.dec}
                thumbnails={source.thumbnails}
                rightPanelVisible={rightPanelVisible}
                downSmall={downSm}
                downLarge={downLg}
              />
            </div>
          </Paper>
        </Grid>
        <Grid item xs={12} order={{ xs: 2, md: 2, lg: 2 }}>
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
        <Grid item xs={12} order={{ xs: 4, md: 6, lg: 6 }}>
          <Accordion
            defaultExpanded
            disableGutters
            className={classes.flexColumn}
          >
            <AccordionSummary
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
                  <DisplayPhotStats
                    photstats={source.photstats[0]}
                    display_header={false}
                  />
                  <PhotometryMagsys magsys={magsys} setMagsys={setMagsys} />
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
                      magsys={magsys}
                      plotStyle={{
                        height: rightPanelVisible ? "65vh" : "75vh",
                      }}
                      mode={downMd ? "mobile" : "desktop"}
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
                  >
                    Photometry Table
                  </Button>
                  <Link to={`/share_data/${source.id}`} role="link">
                    <Button secondary>Share data</Button>
                  </Link>
                  <Link to={`/upload_photometry/${source.id}`} role="link">
                    <Button secondary>Upload photometry</Button>
                  </Link>
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
        <Grid item xs={12} order={{ xs: 5, md: 7, lg: 7 }}>
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
                    (!spectra || spectra?.length === 0) && (
                      <div style={{ marginLeft: "1rem" }}>
                        {" "}
                        No spectrum exists{" "}
                      </div>
                    )}
                  {source.spectrum_exists &&
                    (!spectra || spectra?.length === 0) && (
                      <CircularProgress color="secondary" />
                    )}
                  {source?.spectrum_exists && spectra?.length > 0 && (
                    <Suspense
                      fallback={
                        <div>
                          <CircularProgress color="secondary" />
                        </div>
                      }
                    >
                      <SpectraPlot
                        spectra={spectra}
                        redshift={source.redshift || 0}
                        plotStyle={{
                          height: rightPanelVisible ? "55vh" : "70vh",
                        }}
                        mode={downMd ? "mobile" : "desktop"}
                      />
                    </Suspense>
                  )}
                </div>
                <div className={classes.buttonContainer}>
                  <Link to={`/share_data/${source.id}`} role="link">
                    <Button secondary>Share data</Button>
                  </Link>
                  <Link to={`/upload_spectrum/${source.id}`} role="link">
                    <Button secondary>Upload spectroscopy</Button>
                  </Link>
                </div>
              </Grid>
            </AccordionDetails>
          </Accordion>
        </Grid>
        <Grid item xs={12} order={{ xs: 10, md: 11, lg: 9 }}>
          <Accordion
            defaultExpanded
            disableGutters
            className={classes.flexColumn}
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
                <FollowupRequestForm
                  obj_id={source.id}
                  action="createNew"
                  instrumentList={instrumentList}
                  instrumentFormParams={instrumentFormParams}
                />
                <FollowupRequestLists
                  followupRequests={source.followup_requests}
                  instrumentList={instrumentList}
                  instrumentFormParams={instrumentFormParams}
                  totalMatches={source.followup_requests.length}
                />
              </div>
            </AccordionDetails>
          </Accordion>
        </Grid>
        <Grid item xs={12} order={{ xs: 11, md: 12, lg: 10 }}>
          <Accordion>
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
                <FollowupRequestForm
                  obj_id={source.id}
                  action="createNew"
                  instrumentList={instrumentList}
                  instrumentFormParams={instrumentFormParams}
                  requestType="forced_photometry"
                />
                <FollowupRequestLists
                  followupRequests={source.followup_requests}
                  instrumentList={instrumentList}
                  instrumentFormParams={instrumentFormParams}
                  totalMatches={source.followup_requests.length}
                  requestType="forced_photometry"
                />
              </div>
            </AccordionDetails>
          </Accordion>
        </Grid>
        <Grid item xs={12} order={{ xs: 12, md: 13, lg: 11 }}>
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
                <AssignmentForm
                  obj_id={source.id}
                  observingRunList={observingRunList}
                />
                <AssignmentList assignments={source.assignments} />
              </div>
            </AccordionDetails>
          </Accordion>
        </Grid>
        {downLg || !rightPanelVisible
          ? rightPanelContent(downLg, rightPanelVisible)
          : null}
      </Grid>
      <Grid item xs={rightPanelVisible && !downLg ? 5 : 12}>
        <Grid container spacing={1.5} columns={{ xs: 6 }}>
          {rightPanelVisible && !downLg
            ? rightPanelContent(downLg, rightPanelVisible)
            : null}
        </Grid>
        <PhotometryTable
          obj_id={source.id}
          open={showPhotometry}
          onClose={() => {
            setShowPhotometry(false);
          }}
          magsys={magsys}
          setMagsys={setMagsys}
        />
      </Grid>
    </Grid>
  );
};

SourceContent.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string.isRequired,
    ra: PropTypes.number,
    dec: PropTypes.number,
    loadError: PropTypes.oneOfType([PropTypes.string, PropTypes.bool]),
    thumbnails: PropTypes.arrayOf(PropTypes.shape({})),
    redshift: PropTypes.number,
    redshift_error: PropTypes.number,
    summary_history: PropTypes.arrayOf(
      PropTypes.shape({
        summary: PropTypes.string,
      }),
    ),
    comments: PropTypes.arrayOf(PropTypes.shape({})),
    groups: PropTypes.arrayOf(PropTypes.shape({})),
    gal_lon: PropTypes.number,
    gal_lat: PropTypes.number,
    dm: PropTypes.number,
    ebv: PropTypes.number,
    tns_name: PropTypes.string,
    tns_info: PropTypes.arrayOf(PropTypes.shape(Object)),
    mpc_name: PropTypes.string,
    luminosity_distance: PropTypes.number,
    annotations: PropTypes.arrayOf(
      PropTypes.shape({
        origin: PropTypes.string.isRequired,
        data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
      }),
    ),
    host: PropTypes.shape({
      catalog_name: PropTypes.string,
      name: PropTypes.string,
      alt_name: PropTypes.string,
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
    }),
    host_offset: PropTypes.number,
    host_distance: PropTypes.number,
    galaxies: PropTypes.arrayOf(
      PropTypes.shape({
        catalog_name: PropTypes.string,
        name: PropTypes.string,
        alt_name: PropTypes.string,
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
      }),
    ),
    classifications: PropTypes.arrayOf(
      PropTypes.shape({
        author_name: PropTypes.string,
        probability: PropTypes.number,
        modified: PropTypes.string,
        classification: PropTypes.string,
        id: PropTypes.number,
        obj_id: PropTypes.string,
        author_id: PropTypes.number,
        taxonomy_id: PropTypes.number,
        created_at: PropTypes.string,
      }),
    ),
    followup_requests: PropTypes.arrayOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    assignments: PropTypes.arrayOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    redshift_history: PropTypes.arrayOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    color_magnitude: PropTypes.arrayOf(
      PropTypes.shape({
        abs_mag: PropTypes.number,
        color: PropTypes.number,
        origin: PropTypes.string,
      }),
    ),
    duplicates: PropTypes.arrayOf(
      PropTypes.shape({
        obj_id: PropTypes.string,
        ra: PropTypes.number,
        dec: PropTypes.number,
        separation: PropTypes.number,
      }),
    ),
    alias: PropTypes.arrayOf(PropTypes.string),
    gcn_crossmatch: PropTypes.arrayOf(PropTypes.string),
    gcn_notes: PropTypes.arrayOf(
      PropTypes.shape({
        dateobs: PropTypes.string,
        explanation: PropTypes.string,
        notes: PropTypes.string,
      }),
    ),
    photometry_exists: PropTypes.bool,
    spectrum_exists: PropTypes.bool,
    photstats: PropTypes.arrayOf(PropTypes.shape(Object)),
    candidates: PropTypes.arrayOf(PropTypes.shape(Object)),
  }).isRequired,
};

const Source = ({ route }) => {
  const dispatch = useDispatch();
  const source = useSelector((state) => state.source);
  const cachedSourceId = source ? source.id : null;
  const isCached = route.id === cachedSourceId;

  useEffect(() => {
    const fetchSource = async () => {
      const data = await dispatch(sourceActions.fetchSource(route.id));
      if (data.status === "success") {
        dispatch(sourceActions.addSourceView(route.id));
      }
    };

    if (!isCached) {
      fetchSource();
    }
  }, [dispatch, isCached, route.id]);

  if (source.loadError) {
    return <div>{source.loadError}</div>;
  }
  if (!isCached) {
    return (
      <div>
        <Spinner />
      </div>
    );
  }
  if (source.id === undefined) {
    return <div>Source not found</div>;
  }
  document.title = source.id;

  return (
    <div>
      <SourceContent source={source} />
    </div>
  );
};

Source.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default withRouter(Source);
