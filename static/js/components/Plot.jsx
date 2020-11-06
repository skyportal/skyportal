import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import * as Bokeh from "@bokeh/bokehjs";

import * as Models from "./BokehModels";
import * as Actions from "../ducks/plots";

Bokeh.Models.register_models(Models);

const Plot = (props) => {
  const { url, className } = props;
  const dispatch = useDispatch();

  const plotData = useSelector((state) => state.plots.plotData[url]);

  useEffect(() => {
    if (plotData === undefined) {
      dispatch(Actions.fetchPlotData(url, Actions.FETCH_SOURCE_PLOT));
    } else {
      const { bokehJSON } = plotData;
      window.Bokeh = Bokeh;
      // eslint-disable-next-line no-new-func
      Bokeh.embed.embed_item(bokehJSON, `bokeh-${bokehJSON.root_id}`);
    }
  }, [plotData, dispatch, url]);

  if (!plotData) {
    return <b>Loading plotting data...</b>;
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
