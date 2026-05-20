import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import Card from "@mui/material/Card";
import makeStyles from "@mui/styles/makeStyles";
import Skeleton from "@mui/material/Skeleton";
import CardHeader from "@mui/material/CardHeader";
import CardMedia from "@mui/material/CardMedia";
import CardActionArea from "@mui/material/CardActionArea";
import Box from "@mui/material/Box";

const useStyles = makeStyles(() => ({
  root: ({ size, minSize, maxSize, noMargin }) => ({
    width: size,
    minWidth: minSize,
    maxWidth: maxSize,
    margin: noMargin ? 0 : "0.5rem auto",
    height: "100%",
    maxHeight: "31rem",
  }),
  media: ({ size }) => ({
    height: size,
    width: size,
  }),
  inverted: ({ invertThumbnails }) => ({
    filter: invertThumbnails ? "invert(1)" : "unset",
    WebkitFilter: invertThumbnails ? "invert(1)" : "unset",
  }),
  overlay: {
    position: "absolute",
    top: 0,
    left: 0,
  },
}));

const MAXIMUM_NB_OF_RETRIES = 3;

export const getThumbnailAltAndLink = (name, ra, dec) => {
  let alt = "";
  let link = "";
  let thumbnailName = name.toUpperCase();
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
      thumbnailName = "LEGACY SURVEY DR10";
      break;
    case "ps1":
      alt = "Link to PanSTARRS-1 Image Access";
      link = `https://ps1images.stsci.edu/cgi-bin/ps1cutouts?pos=${ra}+${dec}&filter=color&filter=g&filter=r&filter=i&filter=z&filter=y&filetypes=stack&auxiliary=data&size=240&output_size=0&verbose=0&autoscale=99.500000&catlist=`;
      thumbnailName = "PANSTARRS DR2";
      break;
    default:
      break;
  }
  return { alt, link, thumbnailName };
};

// This function is used when the "outside_survey.png" is store in the DB.
const defaultState = (src) =>
  src?.includes("outside_survey") ? "Outside Survey Area" : "loading";

const Thumbnail = ({
  ra,
  dec,
  name,
  src,
  size,
  minSize,
  maxSize,
  titleSize,
  grayscale,
  noMargin = false,
}) => {
  const isFetched = name === "ls" || name === "sdss";
  const [status, setStatus] = useState(defaultState(src));
  const [retry, setRetry] = useState(0);
  const [imgSrc, setImgSrc] = useState(isFetched ? null : src);
  const invertThumbnails = useSelector(
    (state) => state.profile.preferences.invertThumbnails,
  );
  const classes = useStyles({
    size,
    minSize,
    maxSize,
    invertThumbnails,
    noMargin,
  });

  useEffect(() => {
    setStatus(defaultState(src));
    setRetry(0);
    setImgSrc(isFetched ? null : src);
  }, [src, isFetched]);

  useEffect(() => {
    if (!isFetched || src === "#") return undefined;

    let cancelled = false;
    let objectUrl = null;
    fetch(src)
      .then((r) => {
        if (r.status === 429) {
          if (retry < MAXIMUM_NB_OF_RETRIES) {
            // If the request fail due to too many requests, retry after 2 seconds.
            setTimeout(() => {
              if (!cancelled) setRetry((prev) => prev + 1);
            }, 2000);
            return null;
          }
          setStatus("Too Many Requests");
          return null;
        }
        if (r.status === 404 && r.statusText.includes("(ra, dec) is outside")) {
          setStatus("Outside Survey Area");
          return null;
        }
        if (!r.ok) {
          setStatus("Currently Unavailable");
          return null;
        }
        return r.blob();
      })
      .then((blob) => {
        if (cancelled || !blob) return;
        // If the request succeed but the image is too small for Legacy Survey,
        // It means the image is a grey placeholder for "outside survey area".
        if (name === "ls" && blob.size < 1500) {
          setStatus("Outside Survey Area");
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        setImgSrc(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setStatus("Currently Unavailable");
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [src, name, isFetched, retry]);

  const { alt, link, thumbnailName } = getThumbnailAltAndLink(name, ra, dec);
  const imgClasses = grayscale
    ? `${classes.media} ${classes.inverted}`
    : `${classes.media}`;

  const getThumbnailCard = (
    <>
      <CardHeader
        titleTypographyProps={{
          sx: {
            fontSize: titleSize,
            textWrap: "nowrap",
            color: "gray",
            fontWeight: "bold",
          },
        }}
        sx={{ padding: "0.4rem 0.6rem" }}
        title={thumbnailName}
      />
      <Box sx={{ position: "relative", aspectRatio: "1 / 1" }}>
        {status === "loading" || status === "loaded" ? (
          <>
            {imgSrc && (
              <CardMedia
                component="img"
                src={imgSrc}
                alt={alt}
                className={imgClasses}
                title={alt}
                loading="lazy"
                style={{ opacity: status === "loaded" ? 1 : 0 }}
                onLoad={() => setStatus("loaded")}
                onError={(e) => {
                  e.target.onerror = null;
                  if (src === "#" || isFetched) return;
                  setStatus("Currently Unavailable");
                }}
              />
            )}
            {status === "loading" ? (
              <Skeleton
                className={`${classes.media} ${classes.overlay}`}
                variant="rectangular"
              />
            ) : (
              name !== "sdss" && (
                <img
                  className={`${classes.media} ${classes.overlay}`}
                  src="/static/images/crosshairs.png"
                  alt="crosshairs"
                />
              )
            )}
          </>
        ) : (
          <Box
            className={`${classes.media}`}
            sx={{ background: "#eee", containerType: "inline-size" }}
          >
            <Box
              sx={{
                width: "100%",
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                fontSize: "12cqi",
                fontWeight: "bold",
                color: "rgba(0,0,0,0.75)",
              }}
            >
              {status}
            </Box>
          </Box>
        )}
      </Box>
    </>
  );

  return (
    <Card className={classes.root} variant="outlined">
      {link ? (
        <CardActionArea href={link} target="_blank" rel="noreferrer">
          {getThumbnailCard}
        </CardActionArea>
      ) : (
        getThumbnailCard
      )}
    </Card>
  );
};

Thumbnail.propTypes = {
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  name: PropTypes.string.isRequired,
  src: PropTypes.string.isRequired,
  size: PropTypes.string.isRequired,
  minSize: PropTypes.string.isRequired,
  maxSize: PropTypes.string.isRequired,
  titleSize: PropTypes.string.isRequired,
  grayscale: PropTypes.bool.isRequired,
  noMargin: PropTypes.bool,
};

export default Thumbnail;
