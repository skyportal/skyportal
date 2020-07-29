import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import Select from "@material-ui/core/Select";
import MenuItem from "@material-ui/core/MenuItem";
import InputLabel from "@material-ui/core/InputLabel";

import { GET } from "../API";
import styles from "./StarList.css";

const StarListBody = ({ starList, facility, setFacility, setStarList }) => {
  const handleChange = (event) => {
    setFacility(event.target.value);
    setStarList([{ str: "Loading starlist..." }]);
  };

  return (
    <div className={styles.starListDiv}>
      <code className={styles.starList}>
        <div className={styles.codeText}>
          {starList &&
            starList.map((item, idx) => (
              // eslint-disable-next-line react/no-array-index-key
              <React.Fragment key={idx}>
                {item.str}
                <br />
              </React.Fragment>
            ))}
        </div>
      </code>
      <div className={styles.dropDown}>
        <InputLabel id="StarListSelect">Facility</InputLabel>
        <Select
          labelId="StarListSelect"
          value={facility}
          onChange={handleChange}
        >
          <MenuItem value="Keck">Keck</MenuItem>
          <MenuItem value="P200">P200</MenuItem>
          <MenuItem value="Shane">Shane</MenuItem>
        </Select>
      </div>
    </div>
  );
};

const StarList = ({ sourceId }) => {
  const [starList, setStarList] = useState([{ str: "Loading starlist..." }]);
  const dispatch = useDispatch();
  const [fac, setFacility] = useState("Keck");

  useEffect(() => {
    const fetchStarList = async () => {
      const response = await dispatch(
        GET(
          `/api/sources/${sourceId}/offsets?facility=${fac}`,
          "skyportal/FETCH_STARLIST"
        )
      );
      setStarList(response.data.starlist_info);
    };

    fetchStarList();
  }, [sourceId, dispatch, fac]);

  return (
    <StarListBody
      starList={starList}
      fac={fac}
      setFacility={setFacility}
      setStarList={setStarList}
    />
  );
};

export const ObservingRunStarList = () => {
  const dispatch = useDispatch();
  const [starList, setStarList] = useState([{ str: "Loading starlist..." }]);
  const { assignments } = useSelector((state) => state.observingRun);
  const [facility, setFacility] = useState("Keck");

  useEffect(() => {
    const fetchStarList = async () => {
      const promises = assignments.map((assignment) =>
        dispatch(
          GET(
            `/api/sources/${assignment.obj_id}/offsets?facility=${facility}`,
            "skyportal/FETCH_STARLIST"
          )
        )
      );

      const starlistInfo = [];
      const values = await Promise.allSettled(promises);

      values.forEach((response) =>
        starlistInfo.push(...response.value.data.starlist_info)
      );

      setStarList(starlistInfo);
    };
    fetchStarList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assignments, dispatch, facility]);
  return (
    <StarListBody
      starList={starList}
      facility={facility}
      setStarList={setStarList}
      setFacility={setFacility}
    />
  );
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
  setStarList: PropTypes.func.isRequired,
  setFacility: PropTypes.func.isRequired,
  facility: PropTypes.string.isRequired,
};

export default StarList;
