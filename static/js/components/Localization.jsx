import React, { useEffect } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import {
  ComposableMap,
  Geographies,
  Geography,
  Graticule,
} from "react-simple-maps";

import * as localizationActions from "../ducks/localization";

const Localization = ({ route }) => {
  const { localization } = useSelector((state) => state.localization);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(
      localizationActions.fetchLocalization(
        route.dateobs,
        route.localization_name
      )
    );
  }, [dispatch]);

  return (
    <div>
      <ComposableMap projectionConfig={{ scale: 147, rotate: [0.0, 0.0, 0.0] }}>
        <Graticule stroke="#F53" />
        <Geographies geography={localization.contour}>
          {({ geographies }) =>
            geographies.map((geo) => (
              <Geography key={geo.rsmKey} geography={geo} />
            ))
          }
        </Geographies>
      </ComposableMap>
    </div>
  );
};

Localization.propTypes = {
  route: PropTypes.shape({
    dateobs: PropTypes.string,
    localization_name: PropTypes.string,
  }).isRequired,
};

export default Localization;
