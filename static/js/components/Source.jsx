import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';
import { Link } from "react-router-dom";
import Button from "@material-ui/core/Button";

import * as Action from '../ducks/source';
import Plot from './Plot';
import CommentList from './CommentList';
import ClassificationList from './ClassificationList';
import ClassificationForm from './ClassificationForm';
import ShowClassification from './ShowClassification';


import ThumbnailList from './ThumbnailList';
import SurveyLinkList from './SurveyLinkList';
import StarList from './StarList';

import { ra_to_hours, dec_to_hours } from '../units';

import styles from "./Source.css";
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";
import FollowupRequestForm from './FollowupRequestForm';
import FollowupRequestList from './FollowupRequestList';


const Source = ({ route }) => {
  const dispatch = useDispatch();
  const source = useSelector((state) => state.source);
  const cachedSourceId = source ? source.id : null;
  const isCached = (route.id === cachedSourceId);
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
  const { instrumentList, instrumentObsParams } = useSelector((state) => state.instruments);
  const { taxonomyList } = useSelector((state) => state.taxonomies);

  if (source.loadError) {
    return (
      <div>
        { source.loadError }
      </div>
    );
  }
  if (!isCached) {
    return (
      <div>
        <span>
          Loading...
        </span>
      </div>
    );
  }
  if (source.id === undefined) {
    return (
      <div>
        Source not found
      </div>
    );
  }

  return (
    <div className={styles.source}>

      <div className={styles.leftColumn}>

        <div className={styles.name}>
          {source.id}
        </div>

        <br />
        <ShowClassification
          classifications={source.classifications}
          taxonomyList={taxonomyList}
        />
        <b>
          Position (J2000):
        </b>
        &nbsp;
        {source.ra}
        ,
        &nbsp;
        {source.dec}
        &nbsp;
        (&alpha;,&delta;=
        {ra_to_hours(source.ra)}
        ,
        &nbsp;
        {dec_to_hours(source.dec)}
        )
        <br />
        <b>
          Redshift:
          &nbsp;
        </b>
        {source.redshift}
        &nbsp;|&nbsp;
        <Button href={`/api/sources/${source.id}/finder`}>
          PDF Finding Chart
        </Button>
        &nbsp;|&nbsp;
        <Button onClick={() => setShowStarList(!showStarList)}>
          { showStarList ? "Hide Starlist" : "Show Starlist" }
        </Button>
        <br />
        {showStarList && <StarList sourceId={source.id} />}
        <ThumbnailList ra={source.ra} dec={source.dec} thumbnails={source.thumbnails} />

        <br />
        <br />
        <Responsive
          element={FoldBox}
          title="Photometry"
          mobileProps={{ folded: true }}
        >
          <Plot className={styles.plot} url={`/api/internal/plot/photometry/${source.id}`} />
          <Link to={`/upload_photometry/${source.id}`} role="link">
            <Button variant="contained">
              Upload additional photometry
            </Button>
          </Link>
          <Link to={`/share_data/${source.id}`} role="link">
            <Button variant="contained">
              Share data
            </Button>
          </Link>
        </Responsive>

        <Responsive
          element={FoldBox}
          title="Spectroscopy"
          mobileProps={{ folded: true }}
        >

          <Plot className={styles.plot} url={`/api/internal/plot/spectroscopy/${source.id}`} />
          <Link to={`/share_data/${source.id}`} role="link">
            <Button variant="contained">
              Share data
            </Button>
          </Link>
        </Responsive>

        { /* TODO 1) check for dead links; 2) simplify link formatting if possible */ }
        <Responsive
          element={FoldBox}
          title="Surveys"
          mobileProps={{ folded: true }}
        >

          <SurveyLinkList id={source.id} ra={source.ra} dec={source.dec} />

        </Responsive>
        <FollowupRequestForm
          obj_id={source.id}
          action="createNew"
          instrumentList={instrumentList}
          instrumentObsParams={instrumentObsParams}
        />
        <FollowupRequestList
          followupRequests={source.followup_requests}
          instrumentList={instrumentList}
          instrumentObsParams={instrumentObsParams}
        />
      </div>

      <div className={styles.rightColumn}>

        <Responsive
          element={FoldBox}
          title="Comments"
          mobileProps={{ folded: true }}
          className={styles.comments}
        >
          <CommentList />
        </Responsive>

        <Responsive
          element={FoldBox}
          title="Classifications"
          mobileProps={{ folded: true }}
          className={styles.classifications}
        >
          <ClassificationList />
          <ClassificationForm
            obj_id={source.id}
            action="createNew"
            taxonomyList={taxonomyList}
          />
        </Responsive>

      </div>

    </div>
  );
};

Source.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string
  }).isRequired
};

export default Source;
