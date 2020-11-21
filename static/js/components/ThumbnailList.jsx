import React from "react";
import PropTypes from "prop-types";

import dayjs from "dayjs";
import calendar from "dayjs/plugin/calendar";

import { makeStyles } from "@material-ui/core/styles";
import Grid from "@material-ui/core/Grid";

import Card from "@material-ui/core/Card";
import CardContent from "@material-ui/core/CardContent";
import Typography from "@material-ui/core/Typography";

dayjs.extend(calendar);

const useStyles = makeStyles((theme) => ({
  root: (props) => ({
    width: props.size,
    margin: "0.5rem auto",
    maxHeight: "31rem",
    flexGrow: 1,
  }),
  cardTitle: {
    padding: `${theme.spacing(0.75)}px ${theme.spacing(1)}px ${theme.spacing(
      0.75
    )}px ${theme.spacing(1)}px`,
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
  media: (props) => ({
    height: props.size,
    width: props.size,
  }),
  crosshair: (props) => ({
    position: "absolute",
    top: 0,
    left: 0,
    width: props.size,
    height: props.size,
    paddingBottom: "0.2em",
  }),
}));

const Thumbnail = ({ ra, dec, name, url, size }) => {
  // convert mjd to unix timestamp *in ms*. 40587 is the mjd of the
  // unix timestamp epoch (1970-01-01).

  const classes = useStyles({ size });

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
      link = `http://skyserver.sdss3.org/public/en/tools/chart/navi.aspx?opt=G&ra=${ra}&dec=${dec}&scale=0.1981`;
      break;
    case "dr8":
      alt = "Link to DESI DR8 Image Access";
      link = `https://www.legacysurvey.org/viewer/jpeg-cutout?ra=${ra}&dec=${dec}&size=512&layer=dr8&pixscale=0.262&bands=grz`;
      break;
    case "ps1":
      alt = "Link to PanSTARRS-1 Image Access";
      link = `http://ps1images.stsci.edu/cgi-bin/ps1cutouts?pos=${ra}+${dec}&filter=color&filter=g&filter=r&filter=i&filter=z&filter=y&filetypes=stack&auxiliary=data&size=240&output_size=0&verbose=0&autoscale=99.500000&catlist=`;
      break;
    default:
      alt = "";
      link = "";
  }

  return (
    <Card className={classes.root} variant="outlined">
      <CardContent className={classes.cardTitle}>
        <Typography className={classes.title} color="textSecondary">
          {name.toUpperCase()}
        </Typography>
      </CardContent>
      <div className={classes.mediaDiv}>
        <a href={link}>
          <img
            src={url}
            alt={alt}
            className={classes.media}
            title={alt}
            loading="lazy"
          />
        </a>
        {(name === "dr8" || name === "ps1") && (
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
  displayTypes = ["new", "ref", "sub", "sdss", "dr8", "ps1"],
}) => {
  thumbnails
    .filter((thumbnail) => displayTypes.includes(thumbnail.type))
    .sort(sortThumbnailsByDate);

  const latestThumbnails = displayTypes
    .map((type) => thumbnails.find((thumbnail) => thumbnail.type === type))
    .filter((thumbnail) => thumbnail !== undefined);

  const thumbnail_order = ["new", "ref", "sub", "sdss", "dr8", "ps1"];
  // Sort thumbnails by order of appearance in `thumbnail_order`
  latestThumbnails.sort((a, b) =>
    thumbnail_order.indexOf(a.type) < thumbnail_order.indexOf(b.type) ? -1 : 1
  );

  if (useGrid) {
    return (
      <Grid container direction="row" spacing={3}>
        {latestThumbnails.map((t) => (
          <Grid item key={t.id}>
            <Thumbnail
              key={`thumb_${t.type}`}
              ra={ra}
              dec={dec}
              name={t.type}
              url={t.public_url}
              size={size}
            />
          </Grid>
        ))}
        {displayTypes.includes("ps1") &&
          !latestThumbnails.map((t) => t.type).includes("ps1") && (
            <Grid item key="placeholder">
              <Thumbnail
                key="thumbPlaceHolder"
                ra={ra}
                dec={dec}
                name="PS1: Loading..."
                url="#"
                size={size}
              />
            </Grid>
          )}
      </Grid>
    );
  }
  return latestThumbnails.map((t) => (
    <Grid item key={t.id}>
      <Thumbnail
        key={`thumb_${t.type}`}
        ra={ra}
        dec={dec}
        name={t.type}
        url={t.public_url}
        size={size}
      />
    </Grid>
  ));
};

ThumbnailList.propTypes = {
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  thumbnails: PropTypes.arrayOf(PropTypes.object).isRequired,
  size: PropTypes.string,
  displayTypes: PropTypes.arrayOf(PropTypes.string),
};

export default ThumbnailList;
