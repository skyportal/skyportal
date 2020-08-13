import React, { useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";

import { GET } from "../API";

import styles from "./StarList.css";

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

  return (
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
};

StarList.propTypes = {
  sourceId: PropTypes.string.isRequired,
};

export default StarList;
