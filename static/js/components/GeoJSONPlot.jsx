import React, { useEffect, useState, useRef } from "react";
import { useDispatch } from "react-redux";
import * as d3 from "d3";

import { GET } from "../API";

const useD3 = (renderChartFn) => {
  const ref = useRef();

  useEffect(() => {
    renderChartFn(d3.select(ref.current));
    return () => {};
  }, [renderChartFn, ref]);
  return ref;
};

const GeoJSONPlot = () => {
  const dispatch = useDispatch();
  const [geoJSON, setGeoJSON] = useState(null);

  useEffect(() => {
    const fetchGeoJSON = async () => {
      const response = await dispatch(
        GET(
          "/api/galaxy_catalog?includeGeojson=true",
          "skyportal/FETCH_GEOJSON"
        )
      );
      setGeoJSON(response.data.geojson);
    };

    fetchGeoJSON();
  }, [dispatch]);

  const render = (svg) => {
    if (geoJSON) {
      svg
        .attr("width", 300)
        .attr("height", 200)
        .append("line")
        .attr("x1", 100)
        .attr("y1", 100)
        .attr("x2", 200)
        .attr("y2", 200)
        .style("stroke", "rgb(255,0,0)")
        .style("stroke-width", 2);
    }
  };
  const svgRef = useD3(render);

  if (geoJSON) {
    return <svg ref={svgRef} />;
  }

  return <div>Fetching GeoJSON...</div>;
};

export default GeoJSONPlot;
