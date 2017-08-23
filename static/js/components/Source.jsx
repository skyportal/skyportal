import React from 'react';
import PropTypes from 'prop-types';
import PlotContainer from '../containers/PlotContainer';
import CommentListContainer from '../containers/CommentListContainer';
import SurveyLinkList from './SurveyLinkList';

import styles from "./Source.css";


const Source = ({ ra, dec, red_shift, id }) => {
  if (id === undefined) {
    return <div>Source not found</div>;
  } else {
    return (
      <div className={styles.source}>
        <div className={styles.name}>{id}</div>

        <div className={styles.leftColumn}>

          <b>Location:</b> {ra}, {dec}<br />
          <b>Red Shift: </b>{red_shift}

          <br />
          <b>Photometry:</b>

          <PlotContainer className={styles.plot} url={`/api/plot/photometry/${id}`} />

          <br />
          <b>Spectroscopy:</b><br />
          <PlotContainer className={styles.plot} url={`/api/plot/spectroscopy/${id}`} />
          <br />

          { /* TODO 1) check for dead links; 2) simplify link formatting if possible */ }
          <b>Additional info:</b><br />
          <SurveyLinkList id={id} ra={ra} dec={dec} />
        </div>

        <div className={styles.rightColumn}>

          <div className={styles.comments}>
            <CommentListContainer source={id} />
          </div>

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
