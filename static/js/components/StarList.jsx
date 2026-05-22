import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";

import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import InputLabel from "@mui/material/InputLabel";
import IconButton from "@mui/material/IconButton";
import DownloadOutlined from "@mui/icons-material/DownloadOutlined";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import Tooltip from "@mui/material/Tooltip";
import FormControl from "@mui/material/FormControl";
import CircularProgress from "@mui/material/CircularProgress";

import { GET } from "../API";

const StarListBody = ({ starList, facility, setFacility, setStarList }) => {
  const handleChange = (event) => {
    setFacility(event.target.value);
    setStarList(null);
  };

  return (
    <div style={{ marginTop: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <FormControl size="small">
          <InputLabel id="StarListSelect">Facility</InputLabel>
          <Select
            label="Facility"
            labelId="StarListSelect"
            value={facility}
            onChange={handleChange}
            name="StarListSelectElement"
          >
            <MenuItem value="Keck">Keck</MenuItem>
            <MenuItem value="P200">P200</MenuItem>
            <MenuItem value="P200-NGPS">P200 (NGPS)</MenuItem>
            <MenuItem value="Shane">Shane</MenuItem>
          </Select>
        </FormControl>
        <div>
          <Tooltip title="Copy to clipboard">
            <span>
              <IconButton
                disabled={!starList?.length}
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
          <Tooltip title="Download">
            <span>
              <IconButton
                disabled={!starList?.length}
                onClick={() => {
                  const element = document.createElement("a");
                  const file = new Blob(
                    [starList.map((item) => item.str).join("\n")],
                    { type: "text/plain" },
                  );
                  element.href = URL.createObjectURL(file);
                  element.download = `starlist_${facility.toLowerCase()}${
                    facility === "P200-NGPS" ? ".csv" : ".txt"
                  }`;
                  document.body.appendChild(element);
                  element.click();
                }}
              >
                <DownloadOutlined />
              </IconButton>
            </span>
          </Tooltip>
        </div>
      </div>
      {starList === null ? (
        <CircularProgress sx={{ mt: 1 }} size={32} />
      ) : (
        <pre
          style={{
            fontSize: "0.75rem",
            border: "solid lightgray 1px",
            background: "#eee",
            padding: "1em",
            borderRadius: "0.5em",
            overflowX: "scroll",
          }}
        >
          {starList.map((item) => item.str).join("\n")}
        </pre>
      )}
    </div>
  );
};

const StarList = ({ sourceId }) => {
  const [starList, setStarList] = useState(null);
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

      let data = response.data.starlist_info || [];
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
  const [starList, setStarList] = useState(null);
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
  ),
  setStarList: PropTypes.func.isRequired,
  setFacility: PropTypes.func.isRequired,
  facility: PropTypes.string.isRequired,
};

export default StarList;
