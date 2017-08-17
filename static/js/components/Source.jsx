import React from 'react'
import PlotContainer from '../containers/PlotContainer'
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

        <CommentListContainer className={styles.comments} source={id}/>

        <b>Location:</b> {ra}, {dec}<br/>
        <b>Red Shift: </b>{red_shift}

        <br/>
        <b>Photometry:</b>

        <PlotContainer className={styles.plot} url={`/api/plot/photometry/${id}`}/>

        <br/>
        <b>Spectroscopy:</b><br/>
        <PlotContainer className={styles.plot} url={`/api/plot/spectroscopy/${id}`}/>

        { /* TODO 1) check for dead links; 2) simplify link formatting if possible */ }
        <b>Additional info:</b><br/>
        <SurveyLinkList id={id} ra={ra} dec={dec}/>
      </div>
    );
  }
};


export default Source;
