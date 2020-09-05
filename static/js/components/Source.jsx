import React, { useEffect, useState, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import { makeStyles } from "@material-ui/core/styles";
import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";
import Paper from "@material-ui/core/Paper";
import Accordion from "@material-ui/core/Accordion";
import AccordionSummary from "@material-ui/core/AccordionSummary";
import AccordionDetails from "@material-ui/core/AccordionDetails";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";
import Typography from "@material-ui/core/Typography";

import * as Action from "../ducks/source";
import Plot from "./Plot";
import CommentList from "./CommentList";
import ClassificationList from "./ClassificationList";
import ClassificationForm from "./ClassificationForm";
import ShowClassification from "./ShowClassification";

import ThumbnailList from "./ThumbnailList";
import SurveyLinkList from "./SurveyLinkList";
import StarList from "./StarList";

import { ra_to_hours, dec_to_hours } from "../units";

import Responsive from "./Responsive";
import FollowupRequestForm from "./FollowupRequestForm";

import FollowupRequestLists from "./FollowupRequestLists";
import SharePage from "./SharePage";

import AssignmentForm from "./AssignmentForm";
import AssignmentList from "./AssignmentList";

const CentroidPlot = React.lazy(() =>
  import(/* webpackChunkName: "CentroidPlot" */ "./CentroidPlot")
);

// Export to allow Candidate.jsx to use styles
export const useSourceStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
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
  source: {
    padding: "1rem",
  },
  leftColumn: {
    display: "inline-flex",
    flexFlow: "column nowrap",
    justifyContent: "flex-start",
    verticalAlign: "top",
    paddingRight: "1em",
    maxWidth: "900px",
  },
  leftColumnItem: {
    margin: "0.5rem 0",
  },
  rightColumn: {
    display: "inline-flex",
    minWidth: "20em",
    verticalAlign: "top",
    flexFlow: "column nowrap",
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
  comments: {},
  classifications: {},
  alignRight: {
    display: "inline-block",
    verticalAlign: "super",
  },
  followupContainer: {
    display: "flex",
    flexDirection: "column",
  },
}));

const Source = ({ route }) => {
  const classes = useSourceStyles();
  const dispatch = useDispatch();
  const source = useSelector((state) => state.source);
  const cachedSourceId = source ? source.id : null;
  const isCached = route.id === cachedSourceId;
  const [showStarList, setShowStarList] = useState(false);

  useEffect(() => {
    const fetchSource = async () => {
      const data = await dispatch(Action.fetchSource(route.id));
      if (data.status === "success") {
        dispatch(Action.addSourceView(route.id));
      }
    };

    if (!isCached) {
      fetchSource();
    }
  }, [dispatch, isCached, route.id]);
  const { instrumentList, instrumentFormParams } = useSelector(
    (state) => state.instruments
  );
  const { observingRunList } = useSelector((state) => state.observingRuns);
  const { taxonomyList } = useSelector((state) => state.taxonomies);

  if (source.loadError) {
    return <div>{source.loadError}</div>;
  }
  if (!isCached) {
    return (
      <div>
        <span>Loading...</span>
      </div>
    );
  }
  if (source.id === undefined) {
    return <div>Source not found</div>;
  }

  return (
    <Paper elevation={1}>
      <div className={classes.source}>
        <div className={classes.leftColumn}>
          <div className={classes.leftColumnItem}>
            <div className={classes.alignRight}>
              <SharePage />
            </div>
            <div className={classes.name}>{source.id}</div>
            <br />
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
          <div className={classes.leftColumnItem}>
            <ThumbnailList
              ra={source.ra}
              dec={source.dec}
              thumbnails={source.thumbnails}
            />
          </div>
          <div className={classes.leftColumnItem}>
            <Responsive
              element={Accordion}
              desktopProps={{ defaultExpanded: false }}
              elvation={0}
            >
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
            </Responsive>
          </div>
          <div className={classes.leftColumnItem}>
            <Responsive
              element={Accordion}
              title="Spectroscopy"
              desktopProps={{ defaultExpanded: true }}
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
            </Responsive>
          </div>
          {/* TODO 1) check for dead links; 2) simplify link formatting if possible */}
          <div className={classes.leftColumnItem}>
            <Responsive
              element={Accordion}
              desktopProps={{ defaultExpanded: true }}
            >
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
            </Responsive>
          </div>
          <div className={classes.leftColumnItem}>
            <Responsive
              element={Accordion}
              desktopProps={{ defaultExpanded: true }}
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
            </Responsive>
          </div>
        </div>

        <div className={classes.rightColumn}>
          <Responsive
            element={Accordion}
            desktopProps={{ defaultExpanded: true }}
            className={classes.comments}
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
            <AccordionDetails>
              <CommentList />
            </AccordionDetails>
          </Responsive>
          <Responsive
            element={Accordion}
            desktopProps={{ defaultExpanded: true }}
            className={classes.classifications}
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
              <ClassificationList />
              <ClassificationForm
                obj_id={source.id}
                action="createNew"
                taxonomyList={taxonomyList}
              />
            </AccordionDetails>
          </Responsive>
          <Responsive
            element={Accordion}
            desktopProps={{ defaultExpanded: true }}
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
              <Suspense fallback={<div>Loading centroid plot...</div>}>
                <CentroidPlot
                  className={classes.smallPlot}
                  sourceId={source.id}
                />
              </Suspense>
            </AccordionDetails>
          </Responsive>
        </div>
      </div>
    </Paper>
  );
};

Source.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default Source;
