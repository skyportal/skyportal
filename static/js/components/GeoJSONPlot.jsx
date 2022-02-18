import React, { useEffect, useState, useRef } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";

import * as d3 from "d3";
import d3GeoZoom from "d3-geo-zoom";

import { GET } from "../API";

const useD3 = (renderer, features) => {
  const svgRef = useRef();

  useEffect(() => {
    if (features) {
      renderer(d3.select(svgRef.current), features);
    }
  }, [renderer, svgRef, features]);

  return svgRef;
};

const pointLabelPlot = (svg, features) => {
  const projection = d3.geoOrthographic().translate([200, 200]).scale(190);
  const geoGenerator = d3.geoPath().projection(projection);
  const graticule = d3.geoGraticule();

  const render = () => {
    svg.selectAll("*").remove();

    svg
      .selectAll(".label")
      .data(features)
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
      .data(features)
      .enter()
      .append("path")
      .attr("d", geoGenerator)
      .style("fill", "red");
  };

  render();

  d3GeoZoom().projection(projection).onMove(render)(svg.node());
};

const GeoJSONPlot = ({ dataUrl, renderer }) => {
  const dispatch = useDispatch();
  const [geoJSON, setGeoJSON] = useState(null);

  useEffect(() => {
    const fetchGeoJSON = async () => {
      const response = await dispatch(GET(dataUrl, "skyportal/FETCH_GEOJSON"));
      setGeoJSON(response.data.geojson);
    };

    fetchGeoJSON();
  }, [dispatch]);

  const svgRef = useD3(renderer, geoJSON?.features);

  if (geoJSON) {
    return <svg ref={svgRef} height="400" width="400" />;
  }

  return <div>Fetching GeoJSON...</div>;
};
GeoJSONPlot.propTypes = {
  dataUrl: PropTypes.string.isRequired,
  renderer: PropTypes.func.isRequired,
};

const GeoJSONExamplePlot = () => (
  <GeoJSONPlot
    dataUrl="/api/galaxy_catalog?includeGeoJSON=true"
    renderer={pointLabelPlot}
  />
);

export default GeoJSONExamplePlot;
