import React from 'react';
import PropTypes from 'prop-types';

import PlotContainer from '../containers/PlotContainer';
import CommentListContainer from '../containers/CommentListContainer';
import SurveyLinkList from './SurveyLinkList';

import styles from "./Source.css";
import Responsive from "./Responsive";
import FoldBox from "./FoldBox";


const Source = ({ ra, dec, red_shift, id }) => {
  if (id === undefined) {
    return <div>Source not found</div>;
  } else {
    return (
      <div className={styles.source}>

        <div className={styles.leftColumn}>

          <div className={styles.name}>{id}</div>

          <b>Location:</b> {ra}, {dec}<br />
          <b>Red Shift: </b>{red_shift}

          <br />
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
  red_shift: PropTypes.number.isRequired,
  id: PropTypes.string.isRequired
};

export default Source;
