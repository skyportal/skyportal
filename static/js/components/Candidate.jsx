import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import * as Actions from "../ducks/candidate";
import Plot from "./Plot";
import CommentList from "./CommentList";
import ThumbnailList from "./ThumbnailList";
import SurveyLinkList from "./SurveyLinkList";

import { ra_to_hours, dec_to_hours } from "../units";

import styles from "./Source.css";
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";

const Candidate = ({ route }) => {
  const dispatch = useDispatch();
  const candidate = useSelector((state) => state.candidate);
  const cachedCandidateId = candidate ? candidate.id : null;
  const isCached = route.id === cachedCandidateId;

  useEffect(() => {
    const fetchCandidate = () => {
      dispatch(Actions.fetchCandidate(route.id));
    };

    if (!isCached) {
      fetchCandidate();
    }
  }, [dispatch, isCached, route.id]);

  if (candidate.loadError) {
    return <div>{candidate.loadError}</div>;
  }
  if (!isCached) {
    return (
      <div>
        <span>Loading...</span>
      </div>
    );
  }
  if (candidate.id === undefined) {
    return <div>Candidate not found</div>;
  }

  return (
    <div className={styles.source}>
      <div className={styles.leftColumn}>
        <div className={styles.name}>{candidate.id}</div>
        <br />
        <b>Position (J2000):</b>
        &nbsp;
        {candidate.ra}, &nbsp;
        {candidate.dec}
        &nbsp; (&alpha;,&delta;=
        {ra_to_hours(candidate.ra)}, &nbsp;
        {dec_to_hours(candidate.dec)}) &nbsp; (l,b=
        {candidate.gal_lon}, &nbsp;
        {candidate.gal_lat}
        )
        <br />
        <b>Redshift: &nbsp;</b>
        {candidate.redshift}
        <ThumbnailList
          ra={candidate.ra}
          dec={candidate.dec}
          thumbnails={candidate.thumbnails}
        />
        <br />
        <br />
        <Responsive
          element={FoldBox}
          title="Photometry"
          mobileProps={{ folded: true }}
        >
          <Plot
            className={styles.plot}
            url={`/api/internal/plot/photometry/${candidate.id}`}
          />
        </Responsive>
        <Responsive
          element={FoldBox}
          title="Spectroscopy"
          mobileProps={{ folded: true }}
        >
          <Plot
            className={styles.plot}
            url={`/api/internal/plot/spectroscopy/${candidate.id}`}
          />
        </Responsive>
        {/* TODO 1) check for dead links; 2) simplify link formatting if possible */}
        <Responsive
          element={FoldBox}
          title="Surveys"
          mobileProps={{ folded: true }}
        >
          <SurveyLinkList
            id={candidate.id}
            ra={candidate.ra}
            dec={candidate.dec}
          />
        </Responsive>
      </div>

      <div className={styles.rightColumn}>
        <Responsive
          element={FoldBox}
          title="Comments"
          mobileProps={{ folded: true }}
          className={styles.comments}
        >
          <CommentList isCandidate />
        </Responsive>
      </div>
    </div>
  );
};

Candidate.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default Candidate;
