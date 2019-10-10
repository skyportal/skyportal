import React, { useEffect } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';

import * as Action from '../ducks/source';
import Plot from './Plot';
import CommentList from './CommentList';
import ThumbnailList from './ThumbnailList';
import SurveyLinkList from './SurveyLinkList';
import { ra_to_hours, dec_to_hours } from '../units';

import styles from "./Source.css";
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";


const Source = ({ route }) => {
  const dispatch = useDispatch();
  const source = useSelector((state) => state.source);
  const isCached = () => {
    const cachedSourceID = source ? source.id : null;
    return route.id === cachedSourceID;
  };
  useEffect(() => {
    if (!isCached()) {
      dispatch(Action.fetchSource(route.id));
    }
  }, []);
  if (source.loadError) {
    return (
      <div>
        Could not retrieve requested source
      </div>
    );
  } else if (!isCached()) {
    return (
      <div>
        <span>
          Loading...
        </span>
      </div>
    );
  } else if (source.id === undefined) {
    return (
      <div>
        Source not found
      </div>
    );
  } else {
    return (
      <div className={styles.source}>

        <div className={styles.leftColumn}>

          <div className={styles.name}>
            {source.id}
          </div>

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
          <br />
          <ThumbnailList ra={source.ra} dec={source.dec} thumbnails={source.thumbnails} />

          <br />
          <br />
          <Responsive
            element={FoldBox}
            title="Photometry"
            mobileProps={{ folded: true }}
          >
            <Plot className={styles.plot} url={`/api/internal/plot/photometry/${source.id}`} />
          </Responsive>

          <Responsive
            element={FoldBox}
            title="Spectroscopy"
            mobileProps={{ folded: true }}
          >

            <Plot className={styles.plot} url={`/api/internal/plot/spectroscopy/${source.id}`} />
          </Responsive>

          { /* TODO 1) check for dead links; 2) simplify link formatting if possible */ }
          <Responsive
            element={FoldBox}
            title="Surveys"
            mobileProps={{ folded: true }}
          >

            <SurveyLinkList id={source.id} ra={source.ra} dec={source.dec} />

          </Responsive>
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

        </div>

      </div>
    );
  }
};

Source.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string
  }).isRequired
};

export default Source;
