import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';
import { Link } from "react-router-dom";
import Button from "@material-ui/core/Button";

import * as Action from '../ducks/observingRun';
import Plot from './Plot';
import CommentList from './CommentList';
import ThumbnailList from './ThumbnailList';
import SurveyLinkList from './SurveyLinkList';
import { ObservingRunStarList } from './StarList';
import { observingRunTitle } from './AssignmentForm';
import styles from './Source.css';


const RunSummary = ({ route }) => {

  const dispatch = useDispatch();
  const observingRun = useSelector((state) => state.observingRun);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups);

  // Load the observing run and its assignments if needed
  useEffect(() => {
    dispatch(Action.fetchObservingRun(route.id));
  }, [route.id, dispatch]);

  if (observingRun === {}){
    // Don't need to do this for assignments -- we can just let the page be blank for a short time
    return (
      <b>
        Loading run...
      </b>
    )
  }

  return (
    <div className={styles.source}>
      <div className={styles.leftColumn}>
        <div className={styles.name}>
          {observingRunTitle(observingRun, instrumentList, telescopeList, groups)}
        </div>
        <br />
        <b>
          Observers:
        </b>
        &nbsp;
        {observingRun.observers}
        <br />
        <ObservingRunStarList observingRunId={observingRun.id}/>
      </div>
    </div>
  );
};

export default RunSummary;
