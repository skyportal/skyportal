import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";

import dayjs from "dayjs";
import calendar from "dayjs/plugin/calendar";

import makeStyles from "@mui/styles/makeStyles";
import Grid from "@mui/material/Grid";

import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";

dayjs.extend(calendar);

const useStyles = makeStyles((theme) => ({
  root: ({ size }) => ({
    width: size,
    margin: "0.5rem auto",
    maxHeight: "31rem",
    flexGrow: 1,
  }),
  cardTitle: {
    padding: `${theme.spacing(0.75)} ${theme.spacing(1)} ${theme.spacing(
      0.75,
    )} ${theme.spacing(1)}`,
  },
  title: {
    fontSize: "0.875rem",
  },
  pos: {
    marginBottom: 0,
  },
  mediaDiv: {
    position: "relative",
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

const Thumbnail = ({ ra, dec, name, url, size, grayscale, header }) => {
  // convert mjd to unix timestamp *in ms*. 40587 is the mjd of the
  // unix timestamp epoch (1970-01-01).

  const invertThumbnails = useSelector(
    (state) => state.profile.preferences.invertThumbnails,
  );

  const classes = useStyles({ size, invertThumbnails });

  let alt = null;
  let link = null;
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
      link = `https://skyserver.sdss.org/dr16/en/tools/chart/navi.aspx?opt=G&ra=${ra}&dec=${dec}&scale=0.25`;
      break;
    case "ls":
      alt = "Link to Legacy Survey DR9 Image Access";
      link = `https://www.legacysurvey.org/viewer?ra=${ra}&dec=${dec}&layer=ls-dr9&photoz-dr9&zoom=16&mark=${ra},${dec}`;
      break;
    case "ps1":
      alt = "Link to PanSTARRS-1 Image Access";
      link = `https://ps1images.stsci.edu/cgi-bin/ps1cutouts?pos=${ra}+${dec}&filter=color&filter=g&filter=r&filter=i&filter=z&filter=y&filetypes=stack&auxiliary=data&size=240&output_size=0&verbose=0&autoscale=99.500000&catlist=`;
      break;
    default:
      alt = "";
      link = "";
  }

  const imgClasses = grayscale
    ? `${classes.media} ${classes.inverted}`
    : `${classes.media}`;

  return (
    <Card className={classes.root} variant="outlined">
      <CardContent className={classes.cardTitle}>
        <Typography className={classes.title} color="textSecondary">
          <a href={link} target="_blank" rel="noreferrer">
            {header.toUpperCase()}
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
            onError={(e) => {
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
        </a>
        {name !== "sdss" && (
          <img
            className={classes.crosshair}
            src="/static/images/crosshairs.png"
            alt=""
          />
        )}
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
  grayscale: PropTypes.bool.isRequired,
  header: PropTypes.string.isRequired,
};

const sortThumbnailsByDate = (a, b) => {
  const aDate = dayjs(a.created_at);
  const bDate = dayjs(b.created_at);
  if (aDate.isAfter(bDate)) {
    return -1;
  }
  if (aDate.isBefore(bDate)) {
    return 1;
  }
  return 0;
};

const ThumbnailList = ({
  ra,
  dec,
  thumbnails,
  useGrid = true,
  size = "13rem",
  displayTypes = ["new", "ref", "sub", "sdss", "ls", "ps1"],
}) => {
  thumbnails
    ?.filter((thumbnail) => displayTypes.includes(thumbnail.type))
    ?.sort(sortThumbnailsByDate);

  const latestThumbnails = displayTypes
    ?.map((type) => thumbnails.find((thumbnail) => thumbnail.type === type))
    ?.filter((thumbnail) => thumbnail !== undefined);

  const thumbnail_order = ["new", "ref", "sub", "sdss", "ls", "ps1"];
  // Sort thumbnails by order of appearance in `thumbnail_order`
  latestThumbnails?.sort((a, b) =>
    thumbnail_order.indexOf(a.type) < thumbnail_order.indexOf(b.type) ? -1 : 1,
  );

  const thumbnail_display = Object.fromEntries(
    thumbnail_order.map((x) => [x, x]),
  );
  thumbnail_display.ls = "Legacy Survey DR9";
  thumbnail_display.ps1 = "PanSTARRS DR2";

  if (useGrid) {
    return (
      <Grid container direction="row" spacing={1}>
        {latestThumbnails?.map((t) => (
          <Grid item key={t.id}>
            <Thumbnail
              key={`thumb_${t.type}`}
              ra={ra}
              dec={dec}
              name={t.type}
              url={t.public_url}
              size={size}
              grayscale={t.is_grayscale}
              header={thumbnail_display[t.type]}
            />
          </Grid>
        ))}
        {displayTypes?.includes("ps1") &&
          !latestThumbnails?.map((t) => t.type)?.includes("ps1") && (
            <Grid item key="placeholder">
              <Thumbnail
                key="thumbPlaceHolder"
                ra={ra}
                dec={dec}
                name="PanSTARRS DR2: Loading..."
                url="#"
                size={size}
                grayscale={false}
                header="PanSTARRS DR2"
              />
            </Grid>
          )}
      </Grid>
    );
  }
  return latestThumbnails?.map((t) => (
    <Grid item key={t.id}>
      <Thumbnail
        key={`thumb_${t.type}`}
        ra={ra}
        dec={dec}
        name={t.type}
        url={t.public_url}
        size={size}
        grayscale={t.is_grayscale}
        header={thumbnail_display[t.type]}
      />
    </Grid>
  ));
};

ThumbnailList.propTypes = {
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  thumbnails: PropTypes.arrayOf(PropTypes.object).isRequired, // eslint-disable-line react/forbid-prop-types
  size: PropTypes.string,
  displayTypes: PropTypes.arrayOf(PropTypes.string),
  useGrid: PropTypes.bool,
};

ThumbnailList.defaultProps = {
  size: "13rem",
  displayTypes: ["new", "ref", "sub", "sdss", "ls", "ps1"],
  useGrid: true,
};

export default ThumbnailList;
