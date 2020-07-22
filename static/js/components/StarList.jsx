import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import PropTypes from 'prop-types';

import { GET } from '../API';

import styles from './StarList.css';

function _starListElem(starList){
  return (
    <div className={styles.starListDiv}>
      <code className={styles.starList}>
        {
          starList && starList.map((item, idx) => (
            // eslint-disable-next-line react/no-array-index-key
            <React.Fragment key={idx}>
              { item.str }
              <br />
            </React.Fragment>
          ))
        }
      </code>
    </div>
  );
}

const StarList = ({ sourceId }) => {
  const [starList, setStarList] = useState([{ str: 'Loading starlist...' }]);
  const dispatch = useDispatch();

  useEffect(() => {
    const fetchStarList = async () => {
      const response = await dispatch(
        GET(`/api/sources/${sourceId}/offsets?facility=Keck`, 'skyportal/FETCH_STARLIST')
      );
      setStarList(response.data.starlist_info);
    };

    fetchStarList();
  }, [sourceId, dispatch]);

  return _starListElem(starList);
};

export const ObservingRunStarList = ({ observingRunId }) => {
  const [starList, setStarList] = useState([{ str: 'Loading starlist...' }]);
  const observingRun = useSelector((state) => state.observingRun);
  const dispatch = useDispatch();

  useEffect(() => {
    const fetchStarList = async () => {
      const promises = observingRun.assignments.map(
        (assignment) => (
          dispatch(
            GET(
              `/api/sources/${assignment.obj_id}/offsets?facility=Keck`, 'skyportal/FETCH_STARLIST'
            )
          )
        )
      );

      const starlist_info = [];
      await Promise.allSettled(promises).then(
        (values) => {
          values.forEach(
            (response) => starlist_info.push(...response.value.data.starlist_info)
          )
        }
      );
      setStarList(starlist_info);
    };
    fetchStarList();
  }, [observingRunId, dispatch, observingRun]);

  return _starListElem(starList);

};

StarList.propTypes = {
  sourceId: PropTypes.string.isRequired
};

ObservingRunStarList.propTypes = {
  observingRunId: PropTypes.number.isRequired
};

export default StarList;
