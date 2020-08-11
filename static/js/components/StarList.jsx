import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import { GET } from "../API";

import styles from "./StarList.css";

const StarListBody = ({ starList }) => (
  <div className={styles.starListDiv}>
    <code className={styles.starList}>
      {starList &&
        starList.map((item, idx) => (
          // eslint-disable-next-line react/no-array-index-key
          <React.Fragment key={idx}>
            {item.str}
            <br />
          </React.Fragment>
        ))}
    </code>
  </div>
);

const StarList = ({ sourceId }) => {
  const [starList, setStarList] = useState([{ str: "Loading starlist..." }]);
  const dispatch = useDispatch();

  useEffect(() => {
    const fetchStarList = async () => {
      const response = await dispatch(
        GET(
          `/api/sources/${sourceId}/offsets?facility=Keck`,
          "skyportal/FETCH_STARLIST"
        )
      );
      setStarList(response.data.starlist_info);
    };

    fetchStarList();
  }, [sourceId, dispatch]);

  return <StarListBody starList={starList} />;
};

export const ObservingRunStarList = () => {
  const [starList, setStarList] = useState([{ str: "Loading starlist..." }]);
  const { assignments } = useSelector((state) => state.observingRun);
  const dispatch = useDispatch();

  useEffect(() => {
    const fetchStarList = async () => {
      const promises = assignments.map(
        (assignment) => (
          dispatch(
            GET(
              `/api/sources/${assignment.obj_id}/offsets?facility=Keck`, 'skyportal/FETCH_STARLIST'
            )
          )
        )
      );

      const starlistInfo = [];
      const values = await Promise.allSettled(promises);

      values.forEach(
        (response) => starlistInfo.push(...response.value.data.starlist_info)
      );

      setStarList(starlistInfo);
    };
    fetchStarList();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch]);
  return <StarListBody starList={starList} />;
};

StarList.propTypes = {
  sourceId: PropTypes.string.isRequired,
};

StarListBody.propTypes = {
  starList: PropTypes.arrayOf(
    PropTypes.shape({
      str: PropTypes.string,
    })
  ).isRequired,
};

export default StarList;
