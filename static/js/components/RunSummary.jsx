import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { useSelector, useDispatch } from 'react-redux';

import * as Action from '../ducks/observingRun';
import { ObservingRunStarList } from './StarList';
import { observingRunTitle } from './AssignmentForm';
import styles from './Source.css';


const RunSummary = ({ route }) => {

  const dispatch = useDispatch();
  const observingRun = useSelector((state) => state.observingRun);
  const { instrumentList } = useSelector((state) => state.instruments);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const groups = useSelector((state) => state.groups.all);

  // Load the observing run and its assignments if needed
  useEffect(() => {
    dispatch(Action.fetchObservingRun(route.id));
  }, [route.id, dispatch]);

  if (!(("id" in observingRun) && (observingRun.id === parseInt(route.id)))) {
    // Don't need to do this for assignments -- we can just let the page be blank for a short time
    return (
      <b>
        Loading run...
      </b>
    );
  } else {
    return (
      <div className={styles.source}>
        <div className={styles.leftColumn}>
          <div className={styles.name}>
            {observingRunTitle(observingRun, instrumentList, telescopeList, groups)}
          </div>
          <br/>
          <b>
            Observers:
          </b>
          &nbsp;
          {observingRun.observers}
          <br/>
          <b>
            Starlist and Offsets:
          </b>
          <ObservingRunStarList observingRunId={observingRun.id}/>
        </div>
      </div>
    );
  }
};

export default RunSummary;
