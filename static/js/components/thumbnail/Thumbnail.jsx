import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import makeStyles from "@mui/styles/makeStyles";
import Skeleton from "@mui/material/Skeleton";

const useStyles = makeStyles((theme) => ({
  root: ({ size, minSize, maxSize, noMargin }) => ({
    width: size,
    minWidth: minSize,
    maxWidth: maxSize,
    margin: noMargin ? 0 : "0.5rem auto",
    height: "100%",
    maxHeight: "31rem",
    flexGrow: 1,
  }),
  cardTitle: {
    padding: `${theme.spacing(0.75)} ${theme.spacing(1)} ${theme.spacing(
      0.75,
    )} ${theme.spacing(1)}`,
  },
  title: ({ titleSize }) => ({
    fontSize: titleSize,
    textWrap: "nowrap",
  }),
  pos: {
    marginBottom: 0,
  },
  mediaDiv: {
    position: "relative",
    aspectRatio: "1 / 1",
  },
  media: ({ size }) => ({
    height: size,
    width: size,
  }),
  inverted: ({ invertThumbnails }) => ({
    filter: invertThumbnails ? "invert(1)" : "unset",
    WebkitFilter: invertThumbnails ? "invert(1)" : "unset",
  }),
  crosshair: ({ size }) => ({
    position: "absolute",
    top: 0,
    left: 0,
    width: size,
    height: size,
    paddingBottom: "0.2em",
  }),
}));

export const getThumbnailAltAndLink = (name, ra, dec) => {
  let alt = "";
  let link = "";
  switch (name) {
    case "new":
      alt = `discovery image`;
      break;
    case "ref":
      alt = `pre-discovery (reference) image`;
      break;
    case "sub":
      alt = `subtracted image`;
      break;
    case "sdss":
      alt = "Link to SDSS Navigate tool";
      link = `https://skyserver.sdss.org/dr18/VisualTools/navi?opt=G&ra=${ra}&dec=${dec}&scale=0.1`;
      break;
    case "ls":
      alt = "Link to Legacy Survey DR10 Image Access";
      link = `https://www.legacysurvey.org/viewer?ra=${ra}&dec=${dec}&layer=ls-dr10&photoz-dr9&zoom=16&mark=${ra},${dec}`;
      break;
    case "ps1":
      alt = "Link to PanSTARRS-1 Image Access";
      link = `https://ps1images.stsci.edu/cgi-bin/ps1cutouts?pos=${ra}+${dec}&filter=color&filter=g&filter=r&filter=i&filter=z&filter=y&filetypes=stack&auxiliary=data&size=240&output_size=0&verbose=0&autoscale=99.500000&catlist=`;
      break;
    default:
      break;
  }
  return { alt, link };
};

export const getThumbnailHeader = (type) => {
  switch (type) {
    case "ls":
      return "LEGACY SURVEY DR10";
    case "ps1":
      return "PANSTARRS DR2";
    default:
      return type.toUpperCase();
  }
};

const Thumbnail = ({
  ra,
  dec,
  name,
  url,
  size,
  minSize,
  maxSize,
  titleSize,
  grayscale,
  noMargin = false,
}) => {
  const [status, setStatus] = useState("loading");
  const invertThumbnails = useSelector(
    (state) => state.profile.preferences.invertThumbnails,
  );
  const classes = useStyles({
    size,
    minSize,
    maxSize,
    titleSize,
    invertThumbnails,
    noMargin,
  });

  useEffect(() => {
    setStatus("loading");
  }, [url]);

  const { alt, link } = getThumbnailAltAndLink(name, ra, dec);
  const imgClasses = grayscale
    ? `${classes.media} ${classes.inverted}`
    : `${classes.media}`;

  return (
    <Card className={classes.root} variant="outlined">
      <CardContent className={classes.cardTitle}>
        <Typography className={classes.title} color="textSecondary">
          <a href={link} target="_blank" rel="noreferrer">
            {getThumbnailHeader(name)}
          </a>
        </Typography>
      </CardContent>
      <div className={classes.mediaDiv}>
        <a href={link} target="_blank" rel="noreferrer">
          <img
            src={url}
            alt={alt}
            className={imgClasses}
            title={alt}
            loading="lazy"
            style={{ opacity: status === "loading" ? 0 : 1 }}
            onLoad={() => setStatus("loaded")}
            onError={(e) => {
              setStatus("error");
              if (url !== "#") {
                e.target.onerror = null;
                if (name === "ls") {
                  e.target.src = "/static/images/outside_survey.png";
                } else {
                  e.target.src = "/static/images/currently_unavailable.png";
                }
              }
            }}
          />
          {status === "loading" ? (
            <Skeleton
              className={classes.media}
              variant="rectangular"
              animation="wave"
              style={{
                position: "absolute",
                top: 0,
                left: 0,
              }}
            />
          ) : (
            status !== "error" &&
            name !== "sdss" && (
              <img
                className={classes.crosshair}
                src="/static/images/crosshairs.png"
                alt=""
              />
            )
          )}
        </a>
      </div>
    </Card>
  );
};

Thumbnail.propTypes = {
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  name: PropTypes.string.isRequired,
  url: PropTypes.string.isRequired,
  size: PropTypes.string.isRequired,
  minSize: PropTypes.string.isRequired,
  maxSize: PropTypes.string.isRequired,
  titleSize: PropTypes.string.isRequired,
  grayscale: PropTypes.bool.isRequired,
  noMargin: PropTypes.bool,
};

export default Thumbnail;
