import React, { useState, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import { Link } from "react-router-dom";

import { makeStyles } from "@material-ui/core/styles";
import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";
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
import { ra_to_hours, dec_to_hours } from "../units";
import FollowupRequestForm from "./FollowupRequestForm";
import FollowupRequestLists from "./FollowupRequestLists";
import SharePage from "./SharePage";
import AssignmentForm from "./AssignmentForm";
import AssignmentList from "./AssignmentList";

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
  },
}));

const SourceMobile = ({ source }) => {
  const classes = useSourceStyles();

  const [showStarList, setShowStarList] = useState(false);

  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
  );
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const { taxonomyList } = useSelector((state) => state.taxonomies);

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
              &nbsp;
              {source.ra}, &nbsp;
              {source.dec}
              &nbsp; (&alpha;,&delta;=
              {ra_to_hours(source.ra)}, &nbsp;
              {dec_to_hours(source.dec)}) &nbsp; (l,b=
              {source.gal_lon.toFixed(1)}, &nbsp;
              {source.gal_lat.toFixed(1)}
              )
              <br />
              <b>Redshift: &nbsp;</b>
              {source.redshift}
              &nbsp;|&nbsp;
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
                <Chip
                  label={group.name.substring(0, 15)}
                  key={group.id}
                  size="small"
                  className={classes.chip}
                />
              ))}
            </div>
            <ThumbnailList
              ra={source.ra}
              dec={source.dec}
              thumbnails={source.thumbnails}
              size="10rem"
            />
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
                />
              </Suspense>
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
    loadError: PropTypes.bool,
    thumbnails: PropTypes.arrayOf(PropTypes.shape({})),
    redshift: PropTypes.number,
    groups: PropTypes.arrayOf(PropTypes.shape({})),
    gal_lon: PropTypes.number,
    gal_lat: PropTypes.number,
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
  }).isRequired,
};

export default SourceMobile;
