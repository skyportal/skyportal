import React, { useEffect, useState, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import { makeStyles } from "@material-ui/core/styles";
import useMediaQuery from "@material-ui/core/useMediaQuery";
import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";
import Tooltip from "@material-ui/core/Tooltip";
import Accordion from "@material-ui/core/Accordion";
import AccordionSummary from "@material-ui/core/AccordionSummary";
import AccordionDetails from "@material-ui/core/AccordionDetails";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";
import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";

import {
  isBrowser,
  isMobileOnly,
  isTablet,
  withOrientationChange,
} from "react-device-detect";
import { WidthProvider } from "react-grid-layout";
import { log10, abs, ceil } from "mathjs";

import CommentListMobile from "./CommentListMobile";
import ClassificationList from "./ClassificationList";
import ClassificationForm from "./ClassificationForm";
import ShowClassification from "./ShowClassification";
import ThumbnailList from "./ThumbnailList";
import SurveyLinkList from "./SurveyLinkList";
import StarList from "./StarList";
import { ra_to_hours, dec_to_dms } from "../units";
import FollowupRequestForm from "./FollowupRequestForm";
import FollowupRequestLists from "./FollowupRequestLists";
import SharePage from "./SharePage";
import AssignmentForm from "./AssignmentForm";
import AssignmentList from "./AssignmentList";
import EditSourceGroups from "./EditSourceGroups";
import SourceNotification from "./SourceNotification";
import UpdateSourceRedshift from "./UpdateSourceRedshift";
import SourceRedshiftHistory from "./SourceRedshiftHistory";
import ObjPageAnnotations from "./ObjPageAnnotations";
import SourceSaveHistory from "./SourceSaveHistory";
import PhotometryTable from "./PhotometryTable";
import FavoritesButton from "./FavoritesButton";

import * as spectraActions from "../ducks/spectra";

const VegaHR = React.lazy(() => import("./VegaHR"));

const Plot = React.lazy(() => import(/* webpackChunkName: "Bokeh" */ "./Plot"));

const CentroidPlot = React.lazy(() =>
  import(/* webpackChunkName: "CentroidPlot" */ "./CentroidPlot")
);

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
    color: theme.palette.primary.main,
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
    "& div button": {
      margin: "0.5rem",
    },
  },
  plotButtons: {
    display: "flex",
    flexFlow: "row wrap",
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
}));

const SourceMobile = WidthProvider(
  withOrientationChange(({ source, isLandscape, width }) => {
    const matches = useMediaQuery("(min-width: 475px)");
    const centroidPlotSize = matches ? "21.875rem" : "17rem";

    const classes = useSourceStyles();

    const [showStarList, setShowStarList] = useState(false);
    const [showPhotometry, setShowPhotometry] = useState(false);

    const { instrumentList, instrumentFormParams } = useSelector(
      (state) => state.instruments
    );
    const dispatch = useDispatch();
    const { observingRunList } = useSelector((state) => state.observingRuns);
    const { taxonomyList } = useSelector((state) => state.taxonomies);
    const groups = (useSelector((state) => state.groups.all) || []).filter(
      (g) => !g.single_user_group
    );

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

    const plotWidth = isBrowser ? 800 : width - 100;

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
                    </div>
                  </div>
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
                        Possible duplicate of:&nbsp;
                        {source.duplicates.map((dupID) => (
                          <Link to={`/source/${dupID}`} role="link" key={dupID}>
                            <Button size="small">{dupID}</Button>
                          </Link>
                        ))}
                      </div>
                    </div>
                  )}
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
                        size="small"
                        variant="contained"
                        onClick={() => setShowStarList(!showStarList)}
                      >
                        {showStarList ? "Hide Starlist" : "Show Starlist"}
                      </Button>
                    </div>
                    <div className={classes.infoButton}>
                      <Link to={`/observability/${source.id}`} role="link">
                        <Button size="small" variant="contained">
                          Observability
                        </Button>
                      </Link>
                    </div>
                  </div>
                </div>
                <br />
                {showStarList && <StarList sourceId={source.id} />}
                {source.groups.map((group) => (
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
                    currentGroupIds: source.groups.map((g) => g.id),
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
                <ObjPageAnnotations annotations={source.annotations} />
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
                <div className={classes.photometryContainer}>
                  <Suspense fallback={<div>Loading photometry plot...</div>}>
                    <Plot
                      url={`/api/internal/plot/photometry/${source.id}?width=${plotWidth}&device=${device}`}
                    />
                  </Suspense>
                  <div className={classes.plotButtons}>
                    {isBrowser && (
                      <Link to={`/upload_photometry/${source.id}`} role="link">
                        <Button variant="contained">
                          Upload additional photometry
                        </Button>
                      </Link>
                    )}
                    <Link to={`/manage_data/${source.id}`} role="link">
                      <Button variant="contained">Manage data</Button>
                    </Link>
                    <Button
                      variant="contained"
                      onClick={() => {
                        setShowPhotometry(true);
                      }}
                    >
                      Show Photometry Table
                    </Button>
                  </div>
                </div>
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
                <div className={classes.photometryContainer}>
                  <Suspense fallback={<div>Loading spectroscopy plot...</div>}>
                    <Plot
                      url={`/api/internal/plot/spectroscopy/${source.id}?width=${plotWidth}&device=${device}`}
                    />
                  </Suspense>
                  <div className={classes.plotButtons}>
                    {isBrowser && (
                      <Link to={`/upload_spectrum/${source.id}`} role="link">
                        <Button variant="contained">
                          Upload additional spectroscopy
                        </Button>
                      </Link>
                    )}
                    <Link to={`/manage_data/${source.id}`} role="link">
                      <Button variant="contained">Manage data</Button>
                    </Link>
                  </div>
                </div>
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
                    <Suspense fallback={<div>Loading HR diagram...</div>}>
                      <VegaHR
                        data={source.color_magnitude}
                        width={300}
                        height={300}
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
                <Suspense fallback={<div>Loading centroid plot...</div>}>
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
    followup_requests: PropTypes.arrayOf(PropTypes.any),
    assignments: PropTypes.arrayOf(PropTypes.any),
    redshift_history: PropTypes.arrayOf(PropTypes.any),
    duplicates: PropTypes.arrayOf(PropTypes.string),
    color_magnitude: PropTypes.arrayOf(
      PropTypes.shape({
        abs_mag: PropTypes.number,
        color: PropTypes.number,
        origin: PropTypes.string,
      })
    ),
    alias: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
};

export default SourceMobile;
