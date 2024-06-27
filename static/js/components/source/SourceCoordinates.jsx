import React from "react";
import PropTypes from "prop-types";
import Tooltip from "@mui/material/Tooltip";
import UpdateSourceCoordinates from "./UpdateSourceCoordinates";
import { dec_to_dms, ra_to_hours } from "../../units";

const SourceCoordinates = ({ classes, source, downMd = false }) => {
  const ra = source?.adjusted_position?.ra || source.ra;
  const dec = source?.adjusted_position?.dec || source.dec;
  const gal_lon = source?.adjusted_position?.gal_lon || source.gal_lon;
  const gal_lat = source?.adjusted_position?.gal_lat || source.gal_lat;
  const ebv = source?.adjusted_position?.ebv || source.ebv;

  const title =
    source?.adjusted_position?.separation > 0
      ? `The coordinates displayed here have been re-computed using the object's photometry (${source.adjusted_position.separation.toFixed(
          2,
        )}" from the original)`
      : "The coordinates displayed here are the original coordinates of the object";

  return (
    <Tooltip title={title} placement="top">
      <div
        className={classes.infoLine}
        style={{
          gap: 0,
          columnGap: "0.5rem",
        }}
      >
        <div className={classes.sourceInfo}>
          <span
            style={{
              fontWeight: "bold",
              fontSize: downMd ? "1rem" : "110%",
            }}
          >
            {`${ra_to_hours(ra, ":")} ${dec_to_dms(dec, ":")}`}
          </span>
        </div>
        <div className={classes.sourceInfo}>
          (&alpha;,&delta;= {ra.toFixed(6)}, &nbsp;
          {dec.toFixed(6)})
        </div>
        <div className={classes.sourceInfo}>
          (<i>l</i>,<i>b</i>={gal_lon.toFixed(6)}, &nbsp;
          {gal_lat.toFixed(6)})
        </div>
        {ebv && (
          <div className={classes.sourceInfo}>{`E(B-V): ${ebv.toFixed(
            2,
          )}`}</div>
        )}
        <div className={classes.sourceInfo}>
          <UpdateSourceCoordinates source={source} />
        </div>
      </div>
    </Tooltip>
  );
};

SourceCoordinates.propTypes = {
  classes: PropTypes.shape({
    infoLine: PropTypes.string,
    sourceInfo: PropTypes.string,
  }).isRequired,
  source: PropTypes.shape({
    ra: PropTypes.number,
    dec: PropTypes.number,
    gal_lat: PropTypes.number,
    gal_lon: PropTypes.number,
    ebv: PropTypes.number,
    adjusted_position: PropTypes.shape({
      ra: PropTypes.number,
      dec: PropTypes.number,
      gal_lat: PropTypes.number,
      gal_lon: PropTypes.number,
      ebv: PropTypes.number,
      separation: PropTypes.number,
    }),
  }).isRequired,
  downMd: PropTypes.bool,
};

SourceCoordinates.defaultProps = {
  downMd: false,
};

export default SourceCoordinates;
