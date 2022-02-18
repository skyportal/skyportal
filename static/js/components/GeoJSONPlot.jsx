import React, { useEffect, useState, useRef } from "react";
import { useDispatch } from "react-redux";

import * as d3 from "d3";
import d3GeoZoom from "d3-geo-zoom";

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
          "/api/galaxy_catalog?includeGeoJSON=true",
          "skyportal/FETCH_GEOJSON"
        )
      );
      setGeoJSON(response.data.geojson);
    };

    fetchGeoJSON();
  }, [dispatch]);

  const render = (svg) => {
    if (geoJSON) {
      const projection = d3.geoOrthographic().translate([200, 200]).scale(190);
      const geoGenerator = d3.geoPath().projection(projection);
      const graticule = d3.geoGraticule();

      const renderSVG = () => {
        svg.selectAll("*").remove();

        svg
          .selectAll(".label")
          .data(geoJSON.features)
          .enter()
          .append("text")
          .attr("transform", (d) => `translate(${geoGenerator.centroid(d)})`)
          .style("stroke", "blue")
          .style("text-anchor", "middle")
          .text((d) => d.properties.name);

        svg
          .selectAll("path")
          .data([graticule()])
          .enter()
          .append("path")
          .attr("d", geoGenerator)
          .style("fill", "none")
          .style("stroke", "darkgray")
          .style("stroke-width", "0.5px");

        svg
          .selectAll("path")
          .data(geoJSON.features)
          .enter()
          .append("path")
          .attr("d", geoGenerator)
          .style("fill", "red");
      };

      renderSVG();

      d3GeoZoom().projection(projection).onMove(renderSVG)(svg.node());
    }
  };
  const svgRef = useD3(render);

  if (geoJSON) {
    return <svg ref={svgRef} height="400" width="400" />;
  }

  return <div>Fetching GeoJSON...</div>;
};

export default GeoJSONPlot;
