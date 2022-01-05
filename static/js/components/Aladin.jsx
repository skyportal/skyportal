import React from "react";
import PropTypes from "prop-types";

// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";

// Aladin is a component used to display the skymap, see https://aladin.cds.unistra.fr/ for more examples

const Aladin = ({ height, width, ra, dec, fov, feature_data }) => {
  // ManageData is used to display the data given in param
  console.log("feature_data", feature_data);
  const ManageData = (aladin, data) => {
    // check if the data structure is fine else return nothing
    const { geometry } = data;
    if (!data || !geometry || !geometry.type) {
      return null;
    }
    // If the type is Point add Point
    if (geometry?.type === "Point") {
      if (!geometry.coordinates || geometry.coordinates.length !== 2)
        return null;
      const cat = window.A.catalog({ name: "Points", sourceSize: 15 });
      aladin.addCatalog(cat); // eslint-disable-line
      cat.addSources([
        window.A.marker(geometry.coordinates[0], geometry.coordinates[1]),
      ]);
    }
    if (geometry?.type === "MultiLineString") {
      const overlay = window.A.graphicOverlay({
        color: "#ee2345",
        lineWidth: 2,
      });
      aladin.addOverlay(overlay); // eslint-disable-line
      // If the data is of type 'MultiLineString', cross the data and display polyline for each tab
      for (let i = 0; i < geometry.coordinates.length; i += 1) {
        overlay.add(window.A.polyline(geometry.coordinates[i]));
      }
    }
    return null;
  };

  React.useEffect(() => {
    // Set the default parameters of the Aladin skymap
    const aladin = window.A.aladin("#aladin-lite-div", {
      survey: "P/DSS2/color",
      fov: 60,
    });
    aladin.setFov(fov);
    aladin.gotoRaDec(ra, dec);

    // check if data exists then go through it and use the ManageData function
    if (feature_data && feature_data.features && feature_data.features.length) {
      feature_data.features.map((value) => ManageData(aladin, value));
    }
  }, [fov, ra, dec, feature_data]);

  // Return the default skymap
  return (
    <div
      style={{ width: "100%", alignItems: "center", justifyContent: "center" }}
    >
      <div id="aladin-lite-div" className="aladin" style={{ height, width }} />
    </div>
  );
};

Aladin.propTypes = {
  height: PropTypes.number,
  width: PropTypes.number,
  ra: PropTypes.number,
  dec: PropTypes.number,
  fov: PropTypes.number,
  feature_data: PropTypes.shape({
    length: PropTypes.number,
    features: GeoPropTypes.FeatureCollection,
  }).isRequired,
};

Aladin.defaultProps = {
  ra: 13.623,
  dec: -23.8063,
  fov: 180.0,
  height: 400,
  width: 700,
};

export default Aladin;
