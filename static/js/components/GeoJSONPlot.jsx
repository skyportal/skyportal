import React, { useEffect, useState, useRef } from "react";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";

import * as d3 from "d3";
import d3GeoZoom from "d3-geo-zoom";

import { GET } from "../API";

const useD3 = (renderer, height, width, geoJSON) => {
  const svgRef = useRef();

  useEffect(() => {
    if (geoJSON) {
      renderer(d3.select(svgRef.current), height, width, geoJSON);
    }
  }, [renderer, svgRef, geoJSON]);

  return svgRef;
};

const pointLabelPlot = (svg, height, width, geoJSON) => {
  const center = [width / 2, height / 2];
  const projection = d3.geoOrthographic().translate(center).scale(180);
  const geoGenerator = d3.geoPath().projection(projection);
  const graticule = d3.geoGraticule();

  const { features } = geoJSON;

  const render = () => {
    // Draw sphere background
    svg.selectAll("*").remove();

    svg
      .datum({ type: "Sphere" })
      .append("path")
      .style("fill", "aliceblue")
      .style("stroke", "none")
      .style("opacity", 1)
      .attr("d", geoGenerator);

    // Draw grid
    svg
      .data([graticule()])
      .append("path")
      .style("fill", "none")
      .style("stroke", "darkgray")
      .style("stroke-width", "0.5px")
      .attr("d", geoGenerator);

    // Draw text labels
    const translate = (d) => {
      const coord = projection(d.geometry.coordinates);
      return `translate(${coord[0]}, ${coord[1] - 10})`;
    };

    const visibleOnSphere = (d) => {
      if (!d.properties?.name) return false;
      if (!d.geometry?.coordinates) return false;

      const gdistance = d3.geoDistance(
        d.geometry.coordinates,
        projection.invert(center)
      );

      // In front of globe?
      return gdistance < 1.57;
    };

    svg
      .selectAll(".label")
      .data(features)
      .enter()
      .append("a")
      .attr("xlink:href", (d) => d.properties.url)
      .append("text")
      .attr("transform", translate)
      .style("visibility", (d) => (visibleOnSphere(d) ? "visible" : "hidden"))
      .style("text-anchor", "middle")
      .style("font-size", "0.75rem")
      .style("font-weight", "normal")
      .text((d) => d.properties.name);

    const x = (d) => projection(d.geometry.coordinates)[0];
    const y = (d) => projection(d.geometry.coordinates)[1];

    svg
      .selectAll("circle")
      .data(features)
      .enter()
      .append("circle")
      .attr("fill", (d) => (visibleOnSphere(d) ? "red" : "none"))
      .attr("cx", x)
      .attr("cy", y)
      .attr("r", 3);
  };

  render();

  d3GeoZoom().projection(projection).onMove(render)(svg.node());
};

const GeoJSONPlot = ({ dataUrl, renderer, height, width }) => {
  const dispatch = useDispatch();
  const [geoJSON, setGeoJSON] = useState(null);

  useEffect(() => {
    const fetchGeoJSON = async () => {
      const response = await dispatch(GET(dataUrl, "skyportal/FETCH_GEOJSON"));
      setGeoJSON(response.data.geojson);
    };

    fetchGeoJSON();
  }, [dispatch]);

  const svgRef = useD3(renderer, height, width, geoJSON);

  if (geoJSON) {
    return <svg ref={svgRef} height={height} width={width} />;
  }

  return <div>Fetching GeoJSON...</div>;
};
GeoJSONPlot.propTypes = {
  dataUrl: PropTypes.string.isRequired,
  renderer: PropTypes.func.isRequired,
  height: PropTypes.number.isRequired,
  width: PropTypes.number.isRequired,
};

const GeoJSONExamplePlot = () => (
  <div>
    <GeoJSONPlot
      dataUrl="/api/galaxy_catalog?includeGeoJSON=true"
      renderer={pointLabelPlot}
      height={400}
      width={400}
    />
    <GeoJSONPlot
      dataUrl="/api/sources/?includeGeoJSON=true"
      renderer={pointLabelPlot}
      height={400}
      width={400}
    />
  </div>
);

export default GeoJSONExamplePlot;
