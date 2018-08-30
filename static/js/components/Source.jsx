import React from 'react';
import PropTypes from 'prop-types';

import PlotContainer from '../containers/PlotContainer';
import CommentListContainer from '../containers/CommentListContainer';
import ThumbnailList from './ThumbnailList';
import SurveyLinkList from './SurveyLinkList';
import { ra_to_hours, dec_to_hours } from '../units';

import styles from "./Source.css";
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";


const Source = ({ ra, dec, redshift, thumbnails, id }) => {
  if (id === undefined) {
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
            {id}
          </div>

          <b>
Position (J2000):
          </b>
          {' '}
          {ra}
,
          {' '}
          {dec}
          {' '}
(&alpha;,&delta;=
          {ra_to_hours(ra)}
,
          {' '}
          {dec_to_hours(dec)}
)
          <br />
          <b>
Redshift:
            {' '}
          </b>
          {redshift}
          <br />
          <ThumbnailList ra={ra} dec={dec} thumbnails={thumbnails} />

          <br /><br />
          <Responsive
            element={FoldBox}
            title="Photometry"
            mobileProps={{ folded: true }}
          >
            <PlotContainer className={styles.plot} url={`/api/plot/photometry/${id}`} />
          </Responsive>

          <Responsive
            element={FoldBox}
            title="Spectroscopy"
            mobileProps={{ folded: true }}
          >

            <PlotContainer className={styles.plot} url={`/api/plot/spectroscopy/${id}`} />
          </Responsive>

          { /* TODO 1) check for dead links; 2) simplify link formatting if possible */ }
          <Responsive
            element={FoldBox}
            title="Surveys"
            mobileProps={{ folded: true }}
          >

            <SurveyLinkList id={id} ra={ra} dec={dec} />

          </Responsive>
        </div>

        <div className={styles.rightColumn}>

          <Responsive
            element={FoldBox}
            title="Comments"
            mobileProps={{ folded: true }}
            className={styles.comments}
          >
            <CommentListContainer source={id} />
          </Responsive>

        </div>

      </div>
    );
  }
};

Source.propTypes = {
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  redshift: PropTypes.number,
  id: PropTypes.string.isRequired,
  thumbnails: PropTypes.arrayOf(PropTypes.object).isRequired
};

Source.defaultProps = {
  redshift: null
};

export default Source;
