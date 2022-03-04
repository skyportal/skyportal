import React, { useEffect, useRef } from "react";
import PropTypes from "prop-types";

import * as d3 from "d3";
import d3GeoZoom from "d3-geo-zoom";
// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";

const useD3 = (
  renderer,
  height,
  width,
  skymap,
  sources,
  galaxies,
  instrument
) => {
  const svgRef = useRef();

  useEffect(() => {
    if (skymap || sources || galaxies || instrument) {
      renderer(
        d3.select(svgRef.current),
        height,
        width,
        skymap,
        sources,
        galaxies,
        instrument
      );
    }
  }, [renderer, svgRef, skymap, sources, galaxies, instrument, height, width]);

  return svgRef;
};

const GeoJSONGlobePlot = ({ skymap, sources, galaxies, instrument }) => {
  function renderMap(
    svg,
    height,
    width,
    // eslint-disable-next-line
    skymap,
    // eslint-disable-next-line
    sources,
    // eslint-disable-next-line
    galaxies,
    // eslint-disable-next-line
    instrument
  ) {
    const center = [width / 2, height / 2];
    const projection = d3.geoOrthographic().translate(center).scale(100);
    const geoGenerator = d3.geoPath().projection(projection);
    const graticule = d3.geoGraticule();

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

    function refresh() {
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

      if (skymap?.features) {
        svg
          .selectAll("path")
          .data(skymap.features)
          .enter()
          .append("path")
          .attr("class", (d) => d.properties.name)
          .attr("d", geoGenerator)
          .style("fill", "none")
          .style("stroke", "black")
          .style("stroke-width", "0.5px");
      }

      if (sources?.features) {
        svg
          .selectAll(".label")
          .data(sources.features)
          .enter()
          .append("a")
          .attr("xlink:href", (d) => d.properties.url)
          .append("text")
          .attr("transform", translate)
          .style("visibility", (d) =>
            visibleOnSphere(d) ? "visible" : "hidden"
          )
          .style("text-anchor", "middle")
          .style("font-size", "0.75rem")
          .style("font-weight", "normal")
          .text((d) => d.properties.name);

        const x = (d) => projection(d.geometry.coordinates)[0];
        const y = (d) => projection(d.geometry.coordinates)[1];

        svg
          .selectAll("circle")
          .data(sources.features)
          .enter()
          .append("circle")
          .attr("fill", (d) => (visibleOnSphere(d) ? "red" : "none"))
          .attr("cx", x)
          .attr("cy", y)
          .attr("r", 3);
      }

      if (galaxies?.features) {
        svg
          .selectAll(".label")
          .data(galaxies.features)
          .enter()
          .append("a")
          .attr("xlink:href", (d) => d.properties.url)
          .append("text")
          .attr("transform", translate)
          .style("visibility", (d) =>
            visibleOnSphere(d) ? "visible" : "hidden"
          )
          .style("text-anchor", "middle")
          .style("font-size", "0.75rem")
          .style("font-weight", "normal")
          .text((d) => d.properties.name);

        const x = (d) => projection(d.geometry.coordinates)[0];
        const y = (d) => projection(d.geometry.coordinates)[1];

        svg
          .selectAll("circle")
          .data(galaxies.features)
          .enter()
          .append("circle")
          .attr("fill", (d) => (visibleOnSphere(d) ? "red" : "none"))
          .attr("cx", x)
          .attr("cy", y)
          .attr("r", 3);
      }

      if (instrument?.fields) {
        for (let z = 0; z < instrument.fields.length; z += 1) {
          svg
            .selectAll("path")
            .data(instrument.fields[z].contour_summary.features)
            .enter()
            .append("path")
            .attr("class", (d) => d.properties.field_id)
            .attr("fake", (d) => console.log(d))
            .attr("d", geoGenerator)
            .style("fill", "none")
            .style("stroke", "black")
            .style("stroke-width", "0.5px");
        }
      }
    }

    refresh();
    d3GeoZoom().projection(projection).onMove(refresh)(svg.node());
  }
  const svgRef = useD3(
    renderMap,
    300,
    300,
    skymap,
    sources,
    galaxies,
    instrument
  );

  return <svg height={300} width={300} ref={svgRef} />;
};
GeoJSONGlobePlot.propTypes = {
  skymap: GeoPropTypes.FeatureCollection.isRequired,
  sources: GeoPropTypes.FeatureCollection.isRequired,
  galaxies: GeoPropTypes.FeatureCollection.isRequired,
  instrument: PropTypes.shape({
    name: PropTypes.string,
    type: PropTypes.string,
    band: PropTypes.string,
    fields: PropTypes.arrayOf(
      PropTypes.shape({
        ra: PropTypes.number,
        dec: PropTypes.number,
        id: PropTypes.number,
        contour: GeoPropTypes.FeatureCollection,
        contour_summary: GeoPropTypes.FeatureCollection,
      })
    ),
  }).isRequired,
};

export { useD3 };
export default GeoJSONGlobePlot;
