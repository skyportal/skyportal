import React, { useEffect, useState, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import { makeStyles } from "@material-ui/core/styles";
import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";

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
import FoldBox from "./FoldBox";
import FollowupRequestForm from "./FollowupRequestForm";

import FollowupRequestLists from "./FollowupRequestLists";
import SharePage from "./SharePage";

import AssignmentForm from "./AssignmentForm";
import AssignmentList from "./AssignmentList";

const CentroidPlot = React.lazy(() =>
  import(/* webpackChunkName: "CentroidPlot" */ "./CentroidPlot")
);

// Export to allow Candidate.jsx to import and re-use these styles
export const useSourceStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
  source: {
    padding: "1rem",
  },
  leftColumn: {
    display: "inline-block",
    width: "900px",
    verticalAlign: "top",
    paddingRight: "1em",
    // Example if you wanted to reference this class for other CSS tags:
    "&:hover": {
      // Some styling for when .leftColumn is hovered
    },
    "& > div": {
      // Some styling for divs that are direct children of .leftColumn
    },
  },
  rightColumn: {
    display: "inline-block",
    minWidth: "20em",
    verticalAlign: "top",
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
    <div className={classes.source}>
      <div className={classes.leftColumn}>
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
        {source.gal_lon.toFixed(6)}, &nbsp;
        {source.gal_lat.toFixed(6)}
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
        <br />
        <ThumbnailList
          ra={source.ra}
          dec={source.dec}
          thumbnails={source.thumbnails}
        />
        <br />
        <br />
        <Responsive
          element={FoldBox}
          title="Photometry"
          mobileProps={{ folded: true }}
        >
          <Plot
            className={classes.plot}
            url={`/api/internal/plot/photometry/${source.id}`}
          />
          <Link to={`/upload_photometry/${source.id}`} role="link">
            <Button variant="contained">Upload additional photometry</Button>
          </Link>
          <Link to={`/share_data/${source.id}`} role="link">
            <Button variant="contained">Share data</Button>
          </Link>
        </Responsive>
        <Responsive
          element={FoldBox}
          title="Spectroscopy"
          mobileProps={{ folded: true }}
        >
          <Plot
            className={classes.plot}
            url={`/api/internal/plot/spectroscopy/${source.id}`}
          />
          <Link to={`/share_data/${source.id}`} role="link">
            <Button variant="contained">Share data</Button>
          </Link>
        </Responsive>
        {/* TODO 1) check for dead links; 2) simplify link formatting if possible */}
        <Responsive
          element={FoldBox}
          title="Surveys"
          mobileProps={{ folded: true }}
        >
          <SurveyLinkList id={source.id} ra={source.ra} dec={source.dec} />
        </Responsive>
        <Responsive
          element={FoldBox}
          title="Follow-up"
          mobileProps={{ folded: true }}
        >
          <FollowupRequestForm
            obj_id={source.id}
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
        </Responsive>
      </div>

      <div className={classes.rightColumn}>
        <Responsive
          element={FoldBox}
          title="Comments"
          mobileProps={{ folded: true }}
          className={classes.comments}
        >
          <CommentList />
        </Responsive>

        <Responsive
          element={FoldBox}
          title="Classifications"
          mobileProps={{ folded: true }}
          className={classes.classifications}
        >
          <ClassificationList />
          <ClassificationForm
            obj_id={source.id}
            action="createNew"
            taxonomyList={taxonomyList}
          />
        </Responsive>
        <Responsive
          element={FoldBox}
          title="Centroid Plot"
          mobileProps={{ folded: true }}
        >
          <Suspense fallback={<div>Loading centroid plot...</div>}>
            <CentroidPlot className={classes.smallPlot} sourceId={source.id} />
          </Suspense>
        </Responsive>
      </div>
    </div>
  );
};

Source.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default Source;
