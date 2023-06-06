import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import CircularProgress from "@mui/material/CircularProgress";

import * as Bokeh from "@bokeh/bokehjs";

import { makeStyles } from "@mui/styles";
import * as Actions from "../ducks/plots";

const useStyles = makeStyles(() => ({
  error: {
    color: "red",
  },
}));

const Plot = (props) => {
  const classes = useStyles();
  const { url, className } = props;
  const dispatch = useDispatch();

  const plotData = useSelector((state) => state.plots.plotData[encodeURI(url)]);
  const [error, setError] = useState(false);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    const fetchPlotData = async () => {
      if (plotData === undefined && !fetching) {
        setFetching(true);
        const res = await dispatch(Actions.fetchPlotData(url));
        if (res.status === "error") {
          setError(true);
        }
        setFetching(false);
      } else {
        const { bokehJSON } = plotData;
        window.Bokeh = Bokeh;
        // eslint-disable-next-line no-new-func
        Bokeh.embed.embed_item(bokehJSON, `bokeh-${bokehJSON.root_id}`);
      }
    };
    fetchPlotData();
  }, [plotData, dispatch, url]);

  if (error) {
    return <p className={classes.error}>Error fetching plot data...</p>;
  }
  if (!plotData) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const { bokehJSON } = plotData;

  return (
    <div key={url}>
      <div
        className={`${className} bk-root`}
        id={`bokeh-${bokehJSON.root_id}`}
      />
    </div>
  );
};

Plot.propTypes = {
  url: PropTypes.string.isRequired,
  className: PropTypes.string,
};

Plot.defaultProps = {
  className: "",
};

export default React.memo(Plot);
