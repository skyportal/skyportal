import React from "react";
import PropTypes from "prop-types";

import Button from "../Button";

const PhotometryDownload = ({ obj_id, photometry }) => {
  const download = () => {
    const photometryData = photometry.map((point) => {
      const newPoint = {
        mjd: point.mjd,
        filter: point.filter,
        zp: 23.9,
        magsys: point.magsys,
        lim_mag: point.limiting_mag,
        stacked: 0, // false
      };
      if (point.mag !== null) {
        newPoint.flux = 10 ** (-0.4 * (point.mag - 25));
        newPoint.fluxerr = (point.magerr / (2.5 / Math.log(10))) * point.flux;
      } else {
        newPoint.flux = 10 ** (-0.4 * (point.limiting_mag - 25));
        newPoint.fluxerr = 0;
      }
      return newPoint;
    });
    let csvText = `#source: "${obj_id}" downloaded at ${new Date().toISOString()} UTC\nmjd,filter,flux,fluxerr,zp,magsys,lim_mag,stacked\n`;
    photometryData.forEach((point) => {
      csvText += `${point.mjd},${point.filter},${point.flux},${point.fluxerr},${point.zp},${point.magsys},${point.lim_mag},${point.stacked}\n`;
    });
    const blob = new Blob([csvText], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `${obj_id}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Button
      onClick={() => download()}
      variant="contained"
      secondary
      id="download-lightcurve-button"
    >
      Download Lightcurve
    </Button>
  );
};

PhotometryDownload.propTypes = {
  obj_id: PropTypes.string.isRequired,
  photometry: PropTypes.arrayOf(
    PropTypes.shape({
      mjd: PropTypes.number.isRequired,
      mag: PropTypes.number,
      magerr: PropTypes.number,
      limiting_mag: PropTypes.number,
      filter: PropTypes.string.isRequired,
      instrument_name: PropTypes.string.isRequired,
      origin: PropTypes.string,
    }),
  ).isRequired,
};

export default PhotometryDownload;
