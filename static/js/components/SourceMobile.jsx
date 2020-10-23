import React, { useState, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
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

import Plot from "./Plot";
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
    color: "darkgray",
    paddingBottom: "0.25em",
    display: "inline-block",
  },
  plot: {
    width: "900px",
    overflow: "auto",
  },
  smallPlot: {
    width: "350px",
    overflow: "auto",
  },
  photometryContainer: {
    display: "flex",
    overflowX: "scroll",
    flexDirection: "column",
    paddingBottom: "0.5rem",
    "& div button": {
      margin: "0.5rem",
    },
    "& .bk-bs-nav": {
      marginTop: "0px",
    },
    "& .bk-plotdiv > .bk-widget": {
      marginTop: "0px",
    },
  },
  comments: {
    marginLeft: "1rem",
    padding: "1rem",
  },
  classifications: {
    display: "flex",
    flexDirection: "column",
    margin: "auto",
    maxWidth: "100%",
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
  followupContainer: {
    display: "flex",
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
}));

const SourceMobile = ({ source }) => {
  const matches = useMediaQuery("(min-width: 475px)");
  const centroidPlotSize = matches ? "21.875rem" : "17rem";

  const classes = useSourceStyles();

  const [showStarList, setShowStarList] = useState(false);

  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
  );
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const userAccessibleGroups = useSelector(
    (state) => state.groups.userAccessible
  );

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
            </div>
            <div>
              <ShowClassification
                classifications={source.classifications}
                taxonomyList={taxonomyList}
              />
              <b>Position (J2000):</b>
              &nbsp; &nbsp;
              <span className={classes.position}>
                {ra_to_hours(source.ra)} &nbsp;
                {dec_to_dms(source.dec)}
              </span>
              &nbsp; (&alpha;,&delta;= {source.ra}, &nbsp;
              {source.dec}; <i>l</i>,<i>b</i>={source.gal_lon.toFixed(6)},
              &nbsp;
              {source.gal_lat.toFixed(6)}
              )
              <br />
              <>
                <b>Redshift: &nbsp;</b>
                {source.redshift && source.redshift.toFixed(4)}
                <UpdateSourceRedshift source={source} />
                <SourceRedshiftHistory
                  redshiftHistory={source.redshift_history}
                />
              </>
              {source.dm && (
                <>
                  &nbsp;|&nbsp;
                  <b>DM: &nbsp;</b>
                  {source.dm.toFixed(3)}
                  &nbsp; mag
                </>
              )}
              {source.luminosity_distance && (
                <>
                  &nbsp;|&nbsp;
                  <b>
                    <i>D</i>
                    <sub>L</sub>: &nbsp;
                  </b>
                  {source.luminosity_distance.toFixed(2)}
                  &nbsp; Mpc
                </>
              )}
              {source.redshift != null && <>&nbsp;|&nbsp;</>}
              <Button href={`/api/sources/${source.id}/finder`}>
                PDF Finding Chart
              </Button>
              &nbsp;|&nbsp;
              <Button onClick={() => setShowStarList(!showStarList)}>
                {showStarList ? "Hide Starlist" : "Show Starlist"}
              </Button>
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
                userGroups={userAccessibleGroups}
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
              <SurveyLinkList id={source.id} ra={source.ra} dec={source.dec} />
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
                <Plot
                  className={classes.plot}
                  url={`/api/internal/plot/photometry/${source.id}`}
                />
                <div>
                  <Link to={`/upload_photometry/${source.id}`} role="link">
                    <Button variant="contained">
                      Upload additional photometry
                    </Button>
                  </Link>
                  <Link to={`/share_data/${source.id}`} role="link">
                    <Button variant="contained">Share data</Button>
                  </Link>
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
                <Plot
                  className={classes.plot}
                  url={`/api/internal/plot/spectroscopy/${source.id}`}
                />
                <Link to={`/share_data/${source.id}`} role="link">
                  <Button variant="contained">Share data</Button>
                </Link>
              </div>
            </AccordionDetails>
          </Accordion>
        </div>
        {/* TODO 1) check for dead links; 2) simplify link formatting if possible */}
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
};

SourceMobile.propTypes = {
  source: PropTypes.shape({
    id: PropTypes.string.isRequired,
    ra: PropTypes.number,
    dec: PropTypes.number,
    loadError: PropTypes.oneOfType([PropTypes.string, PropTypes.bool]),
    thumbnails: PropTypes.arrayOf(PropTypes.shape({})),
    redshift: PropTypes.number,
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
  }).isRequired,
};

export default SourceMobile;
