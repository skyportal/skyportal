import React, { useEffect, useState, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import makeStyles from "@mui/styles/makeStyles";
import useMediaQuery from "@mui/material/useMediaQuery";
import Grid from "@mui/material/Grid";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import CircularProgress from "@mui/material/CircularProgress";
import Popover from "@mui/material/Popover";
import AddIcon from "@mui/icons-material/Add";
import IconButton from "@mui/material/IconButton";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

import {
  isBrowser,
  isMobileOnly,
  isTablet,
  withOrientationChange,
} from "react-device-detect";
import { WidthProvider } from "react-grid-layout";
import { log10, abs, ceil } from "mathjs";
import RemoveIcon from "@mui/icons-material/Remove";
import Button from "./Button";

import CommentListMobile from "./CommentListMobile";
import CopyPhotometryDialog from "./CopyPhotometryDialog";
import ClassificationList from "./ClassificationList";
import ClassificationForm from "./ClassificationForm";
import ShowClassification from "./ShowClassification";
import ShowSummaries from "./ShowSummaries";
import ThumbnailList from "./ThumbnailList";
import SurveyLinkList from "./SurveyLinkList";
import StarList from "./StarList";
import { ra_to_hours, dec_to_dms } from "../units";
import FollowupRequestForm from "./FollowupRequestForm";
import FollowupRequestLists from "./FollowupRequestLists";
import SharePage from "./SharePage";
import AssignmentForm from "./AssignmentForm";
import AssignmentList from "./AssignmentList";
import DisplayPhotStats from "./DisplayPhotStats";
import EditSourceGroups from "./EditSourceGroups";
import ShowSummaryHistory from "./ShowSummaryHistory";
import SourceNotification from "./SourceNotification";
import UpdateSourceCoordinates from "./UpdateSourceCoordinates";
import UpdateSourceGCNCrossmatch from "./UpdateSourceGCNCrossmatch";
import UpdateSourceMPC from "./UpdateSourceMPC";
import UpdateSourceRedshift from "./UpdateSourceRedshift";
import UpdateSourceSummary from "./UpdateSourceSummary";
import StartBotSummary from "./StartBotSummary";
import SourceRedshiftHistory from "./SourceRedshiftHistory";
import AnnotationsTable from "./AnnotationsTable";
import SourceSaveHistory from "./SourceSaveHistory";
import PhotometryTable from "./PhotometryTable";
import FavoritesButton from "./FavoritesButton";
import SourceAnnotationButtons from "./SourceAnnotationButtons";
import TNSATForm from "./TNSATForm";

import SourcePlugins from "./SourcePlugins";

import * as spectraActions from "../ducks/spectra";
import * as sourceActions from "../ducks/source";

const VegaHR = React.lazy(() => import("./VegaHR"));

const Plot = React.lazy(() => import(/* webpackChunkName: "Bokeh" */ "./Plot"));

const CentroidPlot = React.lazy(() =>
  import(/* webpackChunkName: "CentroidPlot" */ "./CentroidPlot")
);

const green = "#359d73";

export const useSourceStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
  source: {
    padding: "1rem",
    display: "flex",
    flexDirection: "row",
  },
  column: {
    display: "flex",
    flexFlow: "column nowrap",
    width: "100%",
    "&>div": {
      width: "100%",
    },
  },
  mainColumn: {
    display: "flex",
    flexFlow: "column nowrap",
    verticalAlign: "top",
    paddingRight: "1em",
    minWidth: 0,
    "& > div": {
      margin: "0.5rem 0",
    },
  },
  topRow: {
    display: "flex",
    flexFlow: "row wrap",
    justifyContent: "space-around",
  },
  name: {
    fontSize: "200%",
    fontWeight: "900",
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
    paddingBottom: "0.25em",
    display: "inline-block",
  },
  smallPlot: {
    width: "350px",
    overflow: "auto",
  },
  photometryContainer: {
    display: "flex",
    flexDirection: "column",
    paddingBottom: "0.5rem",
    overflowX: "scroll",
  },
  plotButtons: {
    display: "flex",
    flexFlow: "row wrap",
    "& button": {
      margin: "0.5rem",
    },
  },
  comments: {
    marginLeft: "1rem",
    padding: "1rem",
    width: "100%",
  },
  classifications: {
    display: "flex",
    flexDirection: "column",
    margin: "auto",
    width: "100%",
  },
  tns: {
    display: "flex",
    flexDirection: "column",
    margin: "auto",
    width: "100%",
  },
  thumbnails: {
    "& > div": {
      justifyContent: "center",
    },
  },
  centroidPlot: {
    margin: "auto",
  },
  alignRight: {
    display: "inline-block",
    verticalAlign: "super",
  },
  HRDiagramContainer: {},
  followuphrDiagramContainer: {},
  followupContainer: {
    display: "flex",
    overflow: "hidden",
    flexDirection: "column",
    minWidth: 0,
  },
  sendAlert: {
    margin: "auto",
  },
  position: {
    fontWeight: "bold",
    fontSize: "110%",
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
    padding: "0.25rem 0",
  },
  redshiftInfo: {
    padding: "0.25rem 0.5rem 0.25rem 0",
  },
  dmdlInfo: {
    alignSelf: "center",
    "&>div": {
      display: "inline",
      padding: "0.25rem 0.5rem 0.25rem 0",
    },
  },
  infoButton: {
    paddingRight: "0.5rem",
  },
  findingChart: {
    alignItems: "center",
  },
  tooltipContent: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    width: "100%",
  },
  legend: {
    width: "100%",
    display: "flex",
    flexDirection: "row",
    justifyContent: "left",
    alignItems: "center",
    gap: "10px",
  },
  circle: {
    borderRadius: "50%",
    width: "25px",
    height: "25px",
    display: "inline-block",
  },
  downTriangle: {
    width: 0,
    height: 0,
    backgroundColor: "transparent",
    borderStyle: "solid",
    borderTopWidth: "15px",
    borderRightWidth: "15px",
    borderBottomWidth: "0px",
    borderLeftWidth: "15px",
    borderTopColor: "#359d73",
    borderRightColor: "transparent",
    borderBottomColor: "transparent",
    borderLeftColor: "transparent",
  },
}));

const SourceMobile = WidthProvider(
  withOrientationChange(({ source, isLandscape }) => {
    const matches = useMediaQuery("(min-width: 475px)");
    const centroidPlotSize = matches ? "21.875rem" : "17rem";
    const hrDiagramSize = matches ? 300 : 200;
    const plotWidth = matches ? 800 : 300;

    const classes = useSourceStyles();
    const dispatch = useDispatch();

    const [showStarList, setShowStarList] = useState(false);
    const [showPhotometry, setShowPhotometry] = useState(false);
    const [anchorEl, setAnchorEl] = useState(null);
    const handleClick = (event) => {
      setAnchorEl(event.currentTarget);
    };
    const handleClose = () => {
      setAnchorEl(null);
    };
    const open = Boolean(anchorEl);
    const id = open ? "simple-popover" : undefined;

    const { instrumentList, instrumentFormParams } = useSelector(
      (state) => state.instruments
    );
    const [dialogOpen, setDialogOpen] = useState(false);
    const openDialog = () => {
      setDialogOpen(true);
    };
    const closeDialog = () => {
      setDialogOpen(false);
    };

    const setHost = (galaxyName) => {
      dispatch(sourceActions.addHost(source.id, { galaxyName }));
    };

    const removeHost = () => {
      dispatch(sourceActions.removeHost(source.id));
    };

    const { observingRunList } = useSelector((state) => state.observingRuns);
    const { taxonomyList } = useSelector((state) => state.taxonomies);
    const groups = (useSelector((state) => state.groups.all) || []).filter(
      (g) => !g.single_user_group
    );

    const spectra = useSelector((state) => state.spectra)[source.id];
    const spectrumAnnotations = [];
    if (spectra) {
      spectra.forEach((spec) => {
        spec.annotations.forEach((annotation) => {
          annotation.spectrum_observed_at = spec.observed_at;
          spectrumAnnotations.push(annotation);
        });
      });
    }

    useEffect(() => {
      dispatch(spectraActions.fetchSourceSpectra(source.id));
    }, [source.id, dispatch]);
    const z_round = source.redshift_error
      ? ceil(abs(log10(source.redshift_error)))
      : 4;

    let device = "browser";
    if (isMobileOnly) {
      device = isLandscape ? "mobile_landscape" : "mobile_portrait";
    } else if (isTablet) {
      device = isLandscape ? "tablet_landscape" : "tablet_portrait";
    }

    return (
      <div className={classes.source}>
        <div className={classes.mainColumn}>
          <div className={classes.topRow}>
            <div className={classes.column}>
              <div>
                <div className={classes.alignRight}>
                  <SharePage />
                </div>
                <div className={classes.name}>{source.id}</div>
                <div className={classes.alignRight}>
                  <FavoritesButton sourceID={source.id} />
                </div>
                <div className={classes.alignRight}>
                  {source.alias ? (
                    <div key="aliases"> ({source.alias.join(", ")}) </div>
                  ) : null}
                </div>
              </div>
              <div>
                <div className={classes.sourceInfo}>
                  <div className={classes.redshiftInfo}>
                    <ShowSummaries summaries={source.summary_history} />
                    {source.summary_history?.length < 1 ||
                    !source.summary_history ||
                    source.summary_history[0].summary === null ? ( // eslint-disable-line
                      <div>
                        <b>Summarize: &nbsp;</b>
                      </div>
                    ) : null}
                    <UpdateSourceSummary source={source} />
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
                  <div className={classes.infoLine}>
                    <ShowClassification
                      classifications={source.classifications}
                      taxonomyList={taxonomyList}
                    />
                  </div>
                  <div className={classes.infoLine}>
                    <div className={classes.sourceInfo}>
                      <div>
                        <b>Position (J2000):&nbsp; &nbsp;</b>
                      </div>
                      <div>
                        <span className={classes.position}>
                          {ra_to_hours(source.ra, ":")} &nbsp;
                          {dec_to_dms(source.dec, ":")} &nbsp;
                        </span>
                      </div>
                      <div className={classes.sourceInfo}>
                        <UpdateSourceCoordinates source={source} />
                      </div>
                    </div>
                    <div className={classes.sourceInfo}>
                      <div>
                        (&alpha;,&delta;= {source.ra}, &nbsp;
                        {source.dec}; &nbsp;
                      </div>
                      <div>
                        <i>l</i>,<i>b</i>={source.gal_lon.toFixed(6)}, &nbsp;
                        {source.gal_lat.toFixed(6)})
                      </div>
                      {source.ebv ? (
                        <div>
                          <i> E(B-V)</i>={source.ebv.toFixed(2)}
                        </div>
                      ) : null}
                    </div>
                  </div>
                  <div>
                    <SourcePlugins source={source} />
                  </div>
                  {source.host && (
                    <div className={classes.infoLine}>
                      <div className={classes.sourceInfo}>
                        <b>
                          Host galaxy: {source.host.name} Offset:{" "}
                          {source.host_offset.toFixed(3)} [arcsec]
                        </b>
                        &nbsp;
                        <Button
                          size="small"
                          type="button"
                          name="removeHostGalaxyButton"
                          onClick={() => removeHost()}
                          className={classes.sourceGalaxy}
                        >
                          <RemoveIcon />
                        </Button>
                      </div>
                    </div>
                  )}
                  {source.galaxies && (
                    <div className={classes.infoLine}>
                      <div className={classes.sourceInfo}>
                        <b>
                          <font color="#457b9d">Possible host galaxies:</font>
                        </b>
                        &nbsp;
                        {source.galaxies.map((galaxyName) => (
                          <div key={galaxyName}>
                            <Button
                              size="small"
                              onClick={() => setHost(galaxyName)}
                            >
                              {galaxyName}
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className={classes.infoLine}>
                    <div className={classes.redshiftInfo}>
                      <b>Redshift: &nbsp;</b>
                      {source.redshift && source.redshift.toFixed(z_round)}
                      {source.redshift_error && <b>&nbsp; &plusmn; &nbsp;</b>}
                      {source.redshift_error &&
                        source.redshift_error.toFixed(z_round)}
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
                  {source.duplicates && (
                    <div className={classes.infoLine}>
                      <div className={classes.sourceInfo}>
                        <b>
                          <font color="#457b9d">Possible duplicate of:</font>
                        </b>
                        &nbsp;
                        {source.duplicates.map((dupID) => (
                          <div key={dupID}>
                            <Link
                              to={`/source/${dupID}`}
                              role="link"
                              key={dupID}
                            >
                              <Button size="small">{dupID}</Button>
                            </Link>
                            <Button
                              size="small"
                              type="button"
                              name={`copySourceButton${dupID}`}
                              onClick={() => openDialog(dupID)}
                              className={classes.sourceCopy}
                            >
                              <AddIcon />
                            </Button>
                            <CopyPhotometryDialog
                              source={source}
                              duplicate={dupID}
                              dialogOpen={dialogOpen}
                              closeDialog={closeDialog}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className={classes.alignRight}>
                    <>
                      <div className={classes.infoLine}>
                        <b>MPC Name: &nbsp;</b>
                        <div key="mpc_name"> {source.mpc_name} </div>
                      </div>
                      <div>
                        <UpdateSourceMPC source={source} />
                      </div>
                    </>
                  </div>
                  <div className={classes.alignRight}>
                    <b>GCN Crossmatches: &nbsp;</b>
                    <UpdateSourceGCNCrossmatch source={source} />
                    {source.gcn_crossmatch && (
                      <div>
                        {source.gcn_crossmatch.map((dateobs) => (
                          <div key={dateobs}>
                            <Link
                              to={`/gcn_events/${dateobs.replace(" ", "T")}`}
                              role="link"
                              key={dateobs}
                            >
                              <Button size="small">{dateobs}</Button>
                            </Link>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className={classes.infoLine}>
                    <DisplayPhotStats photstats={source.photstats[0]} />
                  </div>
                  <div
                    className={`${classes.infoLine} ${classes.findingChart}`}
                  >
                    <b>Finding Chart:&nbsp;</b>
                    <Button
                      href={`/api/sources/${source.id}/finder`}
                      download="finder-chart-pdf"
                      size="small"
                    >
                      PDF
                    </Button>
                    &nbsp;|&nbsp;
                    <Link to={`/source/${source.id}/finder`} role="link">
                      <Button size="small">Interactive</Button>
                    </Link>
                  </div>
                  <div className={classes.infoLine}>
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
                      <Link to={`/observability/${source.id}`} role="link">
                        <Button secondary size="small">
                          Observability
                        </Button>
                      </Link>
                    </div>
                    <div className={classes.infoButton}>
                      <Button
                        secondary
                        href={`/api/sources/${source.id}/observability`}
                        download={`observabilityChartRequest-${source.id}`}
                        size="small"
                        type="submit"
                        data-testid={`observabilityChartRequest_${source.id}`}
                      >
                        Observability Chart
                      </Button>
                    </div>
                  </div>
                </div>
                <br />
                {showStarList && <StarList sourceId={source.id} />}
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
                      className={classes.chip}
                    />
                  </Tooltip>
                ))}
                <EditSourceGroups
                  source={{
                    id: source.id,
                    currentGroupIds: source.groups?.map((g) => g.id),
                  }}
                  groups={groups}
                  icon
                />
                <SourceSaveHistory groups={source.groups} />
              </div>
              <div className={classes.thumbnails}>
                <ThumbnailList
                  ra={source.ra}
                  dec={source.dec}
                  thumbnails={source.thumbnails}
                  size="10rem"
                />
              </div>
            </div>
            <Paper className={classes.comments} variant="outlined">
              <Typography className={classes.accordionHeading}>
                Recent Comments
              </Typography>
              <CommentListMobile />
            </Paper>
          </div>
          <div>
            <Accordion defaultExpanded>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="surveys-content"
                id="surveys-header"
              >
                <Typography className={classes.accordionHeading}>
                  Surveys
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <SurveyLinkList
                  id={source.id}
                  ra={source.ra}
                  dec={source.dec}
                />
              </AccordionDetails>
            </Accordion>
          </div>
          <div>
            <Accordion defaultExpanded>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="annotations-content"
                id="annotations-header"
              >
                <Typography className={classes.accordionHeading}>
                  Auto-annotations
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <AnnotationsTable
                  annotations={source.annotations}
                  spectrumAnnotations={spectrumAnnotations}
                />
              </AccordionDetails>
              <AccordionDetails>
                <SourceAnnotationButtons source={source} />
              </AccordionDetails>
            </Accordion>
          </div>
          <div>
            <Accordion defaultExpanded>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="photometry-content"
                id="photometry-header"
              >
                <Typography className={classes.accordionHeading}>
                  Photometry
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container>
                  <div className={classes.photometryContainer}>
                    {!source.photometry_exists ? (
                      <div> No photometry exists </div>
                    ) : (
                      <Suspense
                        fallback={
                          <div>
                            <CircularProgress color="secondary" />
                          </div>
                        }
                      >
                        <Plot
                          url={`/api/internal/plot/photometry/${source.id}?width=${plotWidth}&device=${device}`}
                        />
                      </Suspense>
                    )}
                  </div>
                  <div className={classes.plotButtons}>
                    {isBrowser && (
                      <Link to={`/upload_photometry/${source.id}`} role="link">
                        <Button secondary>Upload additional photometry</Button>
                      </Link>
                    )}
                    <Link to={`/share_data/${source.id}`} role="link">
                      <Button secondary>Share data</Button>
                    </Link>
                    <Button
                      secondary
                      onClick={() => {
                        setShowPhotometry(true);
                      }}
                    >
                      Show Photometry Table
                    </Button>
                    <IconButton
                      aria-label="help"
                      size="small"
                      onClick={handleClick}
                    >
                      <HelpOutlineIcon />
                    </IconButton>
                    <Popover
                      id={id}
                      open={open}
                      anchorEl={anchorEl}
                      onClose={handleClose}
                      anchorOrigin={{
                        vertical: "top",
                        horizontal: "right",
                      }}
                      transformOrigin={{
                        vertical: "top",
                        horizontal: "left",
                      }}
                    >
                      <div className={classes.tooltipContent}>
                        <div className={classes.legend}>
                          <div className={classes.downTriangle} />
                          <p>Stands for Non Detections</p>
                        </div>
                        <div className={classes.legend}>
                          <div
                            style={{
                              background: `${green}`,
                            }}
                            className={classes.circle}
                          />
                          <p> Stands for Detections</p>
                        </div>
                      </div>
                    </Popover>
                  </div>
                </Grid>
              </AccordionDetails>
            </Accordion>
          </div>
          <div>
            <Accordion defaultExpanded>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="spectroscopy-content"
                id="spectroscopy-header"
              >
                <Typography className={classes.accordionHeading}>
                  Spectroscopy
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container>
                  <div className={classes.photometryContainer}>
                    {!source.spectrum_exists ? (
                      <div> No spectra exist </div>
                    ) : (
                      <Suspense
                        fallback={
                          <div>
                            <CircularProgress color="secondary" />
                          </div>
                        }
                      >
                        <Plot
                          url={`/api/internal/plot/spectroscopy/${source.id}?width=${plotWidth}&device=${device}`}
                        />
                      </Suspense>
                    )}
                  </div>
                  <div className={classes.plotButtons}>
                    {isBrowser && (
                      <Link to={`/upload_spectrum/${source.id}`} role="link">
                        <Button secondary>
                          Upload additional spectroscopy
                        </Button>
                      </Link>
                    )}
                    <Link to={`/share_data/${source.id}`} role="link">
                      <Button secondary>Share data</Button>
                    </Link>
                  </div>
                </Grid>
              </AccordionDetails>
            </Accordion>
          </div>
          {/* TODO 1) check for dead links; 2) simplify link formatting if possible */}
          <div>
            {source.color_magnitude.length ? (
              <Accordion defaultExpanded>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  aria-controls="hr_diagram_content"
                  id="hr-diagram-header"
                >
                  <Typography className={classes.accordionHeading}>
                    HR Diagram
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <div className={classes.HRDiagramContainer}>
                    <Suspense
                      fallback={
                        <div>
                          <CircularProgress color="secondary" />
                        </div>
                      }
                    >
                      <VegaHR
                        data={source.color_magnitude}
                        width={hrDiagramSize}
                        height={hrDiagramSize}
                        data-testid={`hr_diagram_${source.id}`}
                      />
                    </Suspense>
                  </div>
                </AccordionDetails>
              </Accordion>
            ) : null}
            <PhotometryTable
              obj_id={source.id}
              open={showPhotometry}
              onClose={() => {
                setShowPhotometry(false);
              }}
              data-testid="show-photometry-table-button"
            />
          </div>
          <div>
            <Accordion defaultExpanded>
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
                <div className={classes.followupContainer}>
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
                  <AssignmentForm
                    obj_id={source.id}
                    observingRunList={observingRunList}
                  />
                  <AssignmentList assignments={source.assignments} />
                </div>
              </AccordionDetails>
            </Accordion>
            <PhotometryTable
              obj_id={source.id}
              open={showPhotometry}
              onClose={() => {
                setShowPhotometry(false);
              }}
              data-testid="show-photometry-table-button"
            />
          </div>
          <Accordion defaultExpanded>
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
          <Accordion
            defaultExpanded
            className={classes.tns}
            data-testid="tns-accordion"
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls="tns-content"
              id="tns-header"
            >
              <Typography className={classes.accordionHeading}>
                TNS Form
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <TNSATForm obj_id={source.id} />
            </AccordionDetails>
          </Accordion>
          <Accordion defaultExpanded>
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
              <div className={classes.centroidPlot}>
                <Suspense
                  fallback={
                    <div>
                      <CircularProgress color="secondary" />
                    </div>
                  }
                >
                  <CentroidPlot
                    className={classes.smallPlot}
                    sourceId={source.id}
                    size={centroidPlotSize}
                  />
                </Suspense>
              </div>
            </AccordionDetails>
          </Accordion>
          <Accordion defaultExpanded>
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
              <div className={classes.sendAlert}>
                <SourceNotification sourceId={source.id} />
              </div>
            </AccordionDetails>
          </Accordion>
        </div>
      </div>
    );
  })
);

SourceMobile.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string.isRequired,
    ra: PropTypes.number,
    dec: PropTypes.number,
    loadError: PropTypes.oneOfType([PropTypes.string, PropTypes.bool]),
    thumbnails: PropTypes.arrayOf(PropTypes.shape({})),
    redshift: PropTypes.number,
    redshift_error: PropTypes.number,
    groups: PropTypes.arrayOf(PropTypes.shape({})),
    gal_lon: PropTypes.number,
    gal_lat: PropTypes.number,
    dm: PropTypes.number,
    luminosity_distance: PropTypes.number,
    annotations: PropTypes.arrayOf(
      PropTypes.shape({
        origin: PropTypes.string.isRequired,
        data: PropTypes.object.isRequired, // eslint-disable-line react/forbid-prop-types
      })
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
      })
    ),
    followup_requests: PropTypes.arrayOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    assignments: PropTypes.arrayOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    redshift_history: PropTypes.arrayOf(PropTypes.any), // eslint-disable-line react/forbid-prop-types
    duplicates: PropTypes.arrayOf(PropTypes.string),
    color_magnitude: PropTypes.arrayOf(
      PropTypes.shape({
        abs_mag: PropTypes.number,
        color: PropTypes.number,
        origin: PropTypes.string,
      })
    ),
    alias: PropTypes.arrayOf(PropTypes.string),
    gcn_crossmatch: PropTypes.arrayOf(PropTypes.string),
    photometry_exists: PropTypes.bool,
    spectrum_exists: PropTypes.bool,
    photstats: PropTypes.arrayOf(PropTypes.shape(Object)),
  }).isRequired,
};

export default SourceMobile;
