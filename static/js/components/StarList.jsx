import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import makeStyles from "@mui/styles/makeStyles";

import { GET } from "../API";

const useStyles = makeStyles(() => ({
  starListDiv: {
    padding: "1rem",
    margin: "1rem",
    lineHeight: "0.8rem",
    position: "relative",
    minHeight: "7rem",
    minWidth: "15rem",
    maxWidth: "100%",
  },
  starList: {
    fontSize: "0.75rem",
  },
  codeText: {
    overflow: "scroll",
  },
  dropDown: {
    margin: "1.5rem",
  },
}));

const StarListBody = ({ starList, facility, setFacility, setStarList }) => {
  const classes = useStyles();
  const handleChange = (event) => {
    setFacility(event.target.value);
    setStarList([{ str: "Loading starlist..." }]);
  };

  return (
    <div className={classes.starListDiv}>
      <div className={classes.dropDown}>
        <InputLabel id="StarListSelect">Facility</InputLabel>
        <Select
          labelId="StarListSelect"
          value={facility}
          onChange={handleChange}
          name="StarListSelectElement"
        >
          <MenuItem value="Keck">Keck</MenuItem>
          <MenuItem value="P200">P200</MenuItem>
          <MenuItem value="Shane">Shane</MenuItem>
        </Select>
      </div>
      <code className={classes.starList}>
        <div className={classes.codeText}>
          <pre>
            {starList &&
              starList.map((item, idx) => (
                // eslint-disable-next-line react/no-array-index-key
                <React.Fragment key={idx}>
                  {item.str}
                  <br />
                </React.Fragment>
              ))}
          </pre>
        </div>
      </code>
    </div>
  );
};

const StarList = ({ sourceId }) => {
  const [starList, setStarList] = useState([{ str: "Loading starlist..." }]);
  const dispatch = useDispatch();
  const [facility, setFacility] = useState("Keck");

  useEffect(() => {
    const fetchStarList = async () => {
      const response = await dispatch(
        GET(
          `/api/sources/${sourceId}/offsets?facility=${facility}`,
          "skyportal/FETCH_STARLIST",
        ),
      );
      setStarList(response.data.starlist_info);
    };

    fetchStarList();
  }, [sourceId, dispatch, facility]);

  return (
    <StarListBody
      starList={starList}
      facility={facility}
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
            "skyportal/FETCH_STARLIST",
          ),
        ),
      );
      const standard_promise = [
        dispatch(
          GET(
            `/api/internal/standards?facility=${facility}`,
            "skyportal/FETCH_STANDARDS",
          ),
        ),
      ];
      const starlistInfo = [];
      const values = await Promise.allSettled(promises);
      const standard_value = await Promise.allSettled(standard_promise);
      values.push(standard_value[0]);

      values.forEach((response) =>
        starlistInfo.push(...response.value.data.starlist_info),
      );

      setStarList(starlistInfo);
    };
    fetchStarList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, facility]);
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
    }),
  ).isRequired,
  setStarList: PropTypes.func.isRequired,
  setFacility: PropTypes.func.isRequired,
  facility: PropTypes.string.isRequired,
};

export default StarList;
