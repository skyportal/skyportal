import React from 'react';
import PropTypes from 'prop-types';

import dayjs from 'dayjs';
import calendar from 'dayjs/plugin/calendar';

import { makeStyles } from '@material-ui/core/styles';
import Grid from '@material-ui/core/Grid';

import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import Typography from '@material-ui/core/Typography';

dayjs.extend(calendar);


/* const useStyles = makeStyles((theme) => ({
})); */

const useStyles = makeStyles((theme) =>
  ({
    root: {
      width: 200,
      margin: 'auto',
      maxHeight: 500,
      flexGrow: 1
    },
    title: {
      fontSize: 14,
    },
    pos: {
      marginBottom: 0,
    },
    mediaDiv: {
      position: "relative"
    },
    media: {
      height: 200,
      width: 200,
    },
    crosshair: {
      position: "absolute",
      top: 0,
      left: 0,
      width: 200,
      height: 200,
      paddingBottom: "0.2em"
    }
  })
);



const Thumbnail = ({ ra, dec, mjd, name, url }) => {
  // convert mjd to unix timestamp *in ms*. 40587 is the mjd of the
  // unix timestamp epoch (1970-01-01).

  const unixt = (mjd - 40587.0) * 86400000;
  const observed_at = new Date(unixt); // a new date
  const observed_at_str = dayjs(observed_at).toString();
  const classes = useStyles();

  let alt = null;
  let link = null;
  switch (name) {
    case "new":
      alt = `discovery image (${observed_at_str})`;
      break;
    case "ref":
      alt = `pre-discovery (reference) image (${observed_at_str})`;
      break;
    case "sub":
      alt = `$subtracted image (${observed_at_str})`;
      break;
    case "sdss":
      alt = "Link to SDSS Navigate tool";
      link = `http://skyserver.sdss3.org/public/en/tools/chart/navi.aspx?opt=G&ra=${ra}&dec=${dec}&scale=0.1981`;
      break;
    case "dr8":
      alt = "Link to DESI DR8 Image Access";
      link = `http://legacysurvey.org/viewer/jpeg-cutout?ra=${ra}&dec=${dec}&size=512&layer=dr8&pixscale=0.262&bands=grz`;
      break;
    default:
      alt = "";
      link = "";
  }


  return (
    <Card className={classes.root} variant="outlined">
      <CardContent>
        <Typography className={classes.title} color="textSecondary">
          {name.toUpperCase()}
        </Typography>
      </CardContent>
      <div className={classes.mediaDiv}>
        <a href={link}>
          <img src={url} alt={alt} className={classes.media} title={alt}/>
        </a>
        {
          (name === "dr8") && <img className={classes.crosshair} src="/static/images/crosshairs.png" alt="" />
        }
      </div>
    </Card>
  );
};

Thumbnail.propTypes = {
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  name: PropTypes.string.isRequired,
  url: PropTypes.string.isRequired,
  mjd: PropTypes.number.isRequired
};

const ThumbnailList = ({ ra, dec, thumbnails, gridKwargs={} }) => {

  const thumbnail_order = ['new', 'ref', 'sub', 'sdss', 'dr8'];
  // Sort thumbnails by order of appearance in `thumbnail_order`
  thumbnails.sort((a, b) => (thumbnail_order.indexOf(a.type) <
  thumbnail_order.indexOf(b.type) ? -1 : 1));

  return (
    <Grid
      container
      direction="row"
      spacing={3}
      {...gridKwargs}
    >
      {
        thumbnails.map((t) => (
          <Grid item key={t.id}>
            <Thumbnail
              key={`thumb_${t.type}`}
              ra={ra}
              dec={dec}
              name={t.type}
              url={t.public_url}
              mjd={t.photometry.mjd}
            />
          </Grid>
          )
        )
      }
    </Grid>
  );
};

ThumbnailList.propTypes = {
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  thumbnails: PropTypes.arrayOf(PropTypes.object).isRequired
};

export default ThumbnailList;


