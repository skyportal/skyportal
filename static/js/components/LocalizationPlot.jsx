import React, { useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import CircularProgress from "@material-ui/core/CircularProgress";

import * as d3 from "d3";
import d3GeoZoom from "d3-geo-zoom";
// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";

import * as localizationActions from "../ducks/localization";

const LocalizationPlot = ({
  loc,
  sources,
  galaxies,
  instrument,
  observations,
  options,
}) => {
  const cachedLocalization = useSelector((state) => state.localization);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(
      localizationActions.fetchLocalization(loc.dateobs, loc.localization_name)
    );
  }, [loc, dispatch]);

  const localization =
    loc.id === cachedLocalization?.id ? cachedLocalization : null;

  if (!localization || !instrument) {
    return <CircularProgress />;
  }

  return (
    <>
      <GeoJSONGlobePlot
        skymap={localization.contour}
        sources={sources.geojson}
        galaxies={galaxies.geojson}
        instrument={instrument}
        observations={observations.geojson}
        options={options}
      />
    </>
  );
};

LocalizationPlot.propTypes = {
  loc: PropTypes.shape({
    id: PropTypes.number,
    dateobs: PropTypes.string,
    localization_name: PropTypes.string,
  }).isRequired,
  sources: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      ra: PropTypes.number,
      dec: PropTypes.number,
      origin: PropTypes.string,
      alias: PropTypes.arrayOf(PropTypes.string),
      redshift: PropTypes.number,
      classifications: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          classification: PropTypes.string,
          created_at: PropTypes.string,
          groups: PropTypes.arrayOf(
            PropTypes.shape({
              id: PropTypes.number,
              name: PropTypes.string,
            })
          ),
        })
      ),
      recent_comments: PropTypes.arrayOf(PropTypes.shape({})),
      altdata: PropTypes.shape({
        tns: PropTypes.shape({
          name: PropTypes.string,
        }),
      }),
      spectrum_exists: PropTypes.bool,
      last_detected_at: PropTypes.string,
      last_detected_mag: PropTypes.number,
      peak_detected_at: PropTypes.string,
      peak_detected_mag: PropTypes.number,
      groups: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          name: PropTypes.string,
        })
      ),
    })
  ).isRequired,
  galaxies: PropTypes.arrayOf(
    PropTypes.shape({
      catalog_name: PropTypes.string,
      name: PropTypes.string,
      alt_name: PropTypes.string,
      ra: PropTypes.number,
      dec: PropTypes.number,
      distmpc: PropTypes.number,
      distmpc_unc: PropTypes.number,
      redshift: PropTypes.number,
      redshift_error: PropTypes.number,
      sfr_fuv: PropTypes.number,
      mstar: PropTypes.number,
      magb: PropTypes.number,
      magk: PropTypes.number,
      a: PropTypes.number,
      b2a: PropTypes.number,
      pa: PropTypes.number,
      btc: PropTypes.number,
    })
  ).isRequired,
  instrument: PropTypes.shape({
    name: PropTypes.string,
    type: PropTypes.string,
    band: PropTypes.string,
    fields: PropTypes.arrayOf(
      PropTypes.shape({
        ra: PropTypes.number,
        dec: PropTypes.number,
        id: PropTypes.number,
      })
    ),
  }).isRequired,
  observations: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      obstime: PropTypes.instanceOf(Date),
      filt: PropTypes.string,
      exposure_time: PropTypes.number,
      airmass: PropTypes.number,
      limmag: PropTypes.number,
      seeing: PropTypes.number,
      processed_fraction: PropTypes.number,
    })
  ).isRequired,
  options: PropTypes.arrayOf(PropTypes.number).isRequired,
};

const useD3 = (
  renderer,
  height,
  width,
  skymap,
  sources,
  galaxies,
  instrument,
  observations,
  options
) => {
  const svgRef = useRef();

  useEffect(() => {
    if (skymap || sources || galaxies || instrument || observations) {
      renderer(
        d3.select(svgRef.current),
        height,
        width,
        skymap,
        sources,
        galaxies,
        instrument,
        observations,
        options
      );
    }
  }, [
    renderer,
    svgRef,
    skymap,
    sources,
    galaxies,
    instrument,
    observations,
    options,
    height,
    width,
  ]);

  return svgRef;
};

const GeoJSONGlobePlot = ({
  skymap,
  sources,
  galaxies,
  instrument,
  observations,
  options,
}) => {
  function renderMap(
    svg,
    height,
    width,
    skymap_geojson,
    sources_geojson,
    galaxies_geojson,
    instrument_geojson,
    observations_geojson,
    options_bool
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

      if (skymap_geojson?.features && options_bool.localization) {
        svg
          .selectAll("path")
          .data(skymap_geojson.features)
          .enter()
          .append("path")
          .attr("class", (d) => d.properties.name)
          .attr("d", geoGenerator)
          .style("fill", "none")
          .style("stroke", "black")
          .style("stroke-width", "0.5px");
      }

      if (sources_geojson?.features && options_bool.sources) {
        svg
          .selectAll(".label")
          .data(sources_geojson.features)
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

      if (galaxies_geojson?.features && options_bool.galaxies) {
        svg
          .selectAll(".label")
          .data(galaxies_geojson.features)
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

      if (instrument_geojson?.fields && options_bool.instrument) {
        instrument_geojson.fields.forEach((f) => {
          const { field_id } = f.contour_summary.properties;
          const { features } = f.contour_summary;
          svg
            .data(features)
            .append("path")
            .attr("class", field_id)
            .style("fill", "none")
            .style("stroke", "blue")
            .style("stroke-width", "0.5px")
            .attr("d", geoGenerator);
        });
      }

      if (observations_geojson && options_bool.observations) {
        observations_geojson.forEach((f) => {
          const { field_id } = f.properties;
          const { features } = f;
          svg
            .data(features)
            .append("path")
            .attr("class", field_id)
            .style("fill", "none")
            .style("stroke", "blue")
            .style("stroke-width", "0.5px")
            .attr("d", geoGenerator);
        });
      }
    }

    refresh();
    d3GeoZoom().projection(projection).onMove(refresh)(svg.node());
  }
  const svgRef = useD3(
    renderMap,
    600,
    600,
    skymap,
    sources,
    galaxies,
    instrument,
    observations,
    options
  );

  return <svg height={600} width={600} ref={svgRef} />;
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
  observations: PropTypes.arrayOf(GeoPropTypes.FeatureCollection).isRequired,
  options: PropTypes.arrayOf(PropTypes.number).isRequired,
};

export default LocalizationPlot;
