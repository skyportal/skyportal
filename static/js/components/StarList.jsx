import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import makeStyles from "@mui/styles/makeStyles";
import Paper from "@mui/material/Paper";
import IconButton from "@mui/material/IconButton";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import Tooltip from "@mui/material/Tooltip";

import { GET } from "../API";

const useStyles = makeStyles(() => ({
  starList: {
    fontSize: "0.75rem",
  },
  codeText: {
    overflow: "scroll",
  },
  paper: {
    marginTop: "0.5rem",
    padding: "0 0.5rem 0 0.5rem",
  },
}));

const StarListBody = ({ starList, facility, setFacility, setStarList }) => {
  const classes = useStyles();
  const handleChange = (event) => {
    setFacility(event.target.value);
    setStarList([{ str: "Loading starlist..." }]);
  };

  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column" }}>
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <InputLabel id="StarListSelect">Facility</InputLabel>
          <Select
            labelId="StarListSelect"
            value={facility}
            onChange={handleChange}
            name="StarListSelectElement"
            size="small"
          >
            <MenuItem value="Keck">Keck</MenuItem>
            <MenuItem value="P200">P200</MenuItem>
            <MenuItem value="P200-NGPS">P200 (NGPS)</MenuItem>
            <MenuItem value="Shane">Shane</MenuItem>
          </Select>
        </div>
        {starList &&
          starList?.length > 0 &&
          starList[0].str !== "Loading starlist..." && (
            <Tooltip title="Copy to clipboard">
              <span>
                <IconButton
                  onClick={() => {
                    navigator.clipboard.writeText(
                      starList.map((item) => item.str).join("\n"),
                    );
                  }}
                >
                  <ContentCopyIcon />
                </IconButton>
              </span>
            </Tooltip>
          )}
      </div>
      <Paper variant="outlined" className={classes.paper}>
        <code className={classes.starList}>
          <div className={classes.codeText}>
            <pre>
              {starList &&
                starList.map((item, idx) => (
                  <React.Fragment key={idx}>
                    {item.str}
                    <br />
                  </React.Fragment>
                ))}
            </pre>
          </div>
        </code>
      </Paper>
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

      let data = response.data.starlist_info;
      // if the facility is P200-NGPS, we add the header to the starlist
      if (facility === "P200-NGPS") {
        data = [
          {
            str: "NAME,RA,DECL,OFFSET_RA,OFFSET_DEC,COMMENT,PRIORITY,BINSPAT,BINSPECT,SLITANGLE,SLITWIDTH,AIRMASS_MAX,WRANGE_LOW,WRANGE_HIGH,CHANNEL,MAGNITUDE,MAGFILTER,EXPTIME",
          },
          ...data,
        ];
      }
      setStarList(data);
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
            `/api/sources/${assignment.obj_id}/offsets?facility=${facility}&observing_run_id=${assignment.run_id}`,
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

      // if the facility is P200-NGPS, we add the header to the starlist
      if (facility === "P200-NGPS") {
        starlistInfo.unshift({
          str: "NAME,RA,DECL,OFFSET_RA,OFFSET_DEC,COMMENT,PRIORITY,BINSPAT,BINSPECT,SLITANGLE,SLITWIDTH,AIRMASS_MAX,WRANGE_LOW,WRANGE_HIGH,CHANNEL,MAGNITUDE,MAGFILTER,EXPTIME",
        });
      }

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
