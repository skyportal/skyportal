import React from 'react';
import PropTypes from 'prop-types';
import moment from 'moment';
import classnames from 'classnames';

import styles from "./ThumbnailList.css";


const Thumbnail = ({ ra, dec, telescope, observed_at, name, url }) => {
  const observed_at_str = moment(observed_at).calendar();

  let alt = null;
  let link = null;
  switch (name) {
    case "new":
      alt = `${telescope} discovery image (${observed_at_str})`;
      break;
    case "ref":
      alt = `${telescope} pre-discovery (reference) image (${observed_at_str})`;
      break;
    case "sub":
      alt = `${telescope} subtracted image (${observed_at_str})`;
      break;
    case "sdss":
      alt = "Link to SDSS Navigate tool";
      link = `http://skyserver.sdss3.org/public/en/tools/chart/navi.aspx?opt=G&ra=${ra}&dec=${dec}&scale=0.1981`;
      break;
    case "dr8":
      alt = "Link to DESI DR8 Image Access";
      link = `http://legacysurvey.org/viewer/jpeg-cutout?ra=${ra}&dec=${dec}&size=512&layer=dr8&pixscale=0.262&bands=grz`;
      break;
  }

  const thumbnailDivClassNames = classnames(styles.Thumbnail, { [styles.dr8]: name === "dr8" });

  return (
    <a href={link}>
      {name === "dr8" && <br />}
      <div className={thumbnailDivClassNames}>
        <b>
          {name.toUpperCase()}
        </b>
        <br />
        <div className={styles.thumbnailimgdiv}>
          <img className={name === "dr8" && styles.dr8crosshairs} src={url} alt={alt} title={alt} />
          {
            (name === "dr8") &&
            <img className={styles.dr8crosshairs} src="/static/images/crosshairs.png" alt="" />
          }
        </div>
      </div>
    </a>
  );
};

Thumbnail.propTypes = {
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  telescope: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
  url: PropTypes.string.isRequired,
  observed_at: PropTypes.string.isRequired
};


const ThumbnailList = ({ ra, dec, thumbnails }) => {
  const thumbnail_order = ['new', 'ref', 'sub', 'sdss', 'dr8'];
  // Sort thumbnails by order of appearance in `thumbnail_order`
  thumbnails.sort((a, b) => (thumbnail_order.indexOf(a.type) <
                             thumbnail_order.indexOf(b.type) ? -1 : 1));

  return (
    <div className={styles.ThumbnailList}>
      {thumbnails.map((t) => (
        <Thumbnail
          key={`thumb_${t.type}`}
          ra={ra}
          dec={dec}
          name={t.type}
          url={t.public_url}
          telescope={t.photometry.instrument.telescope.nickname}
          observed_at={t.photometry.observed_at}
        />
      ))}
    </div>
  );
};

ThumbnailList.propTypes = {
  ra: PropTypes.number.isRequired,
  dec: PropTypes.number.isRequired,
  thumbnails: PropTypes.arrayOf(PropTypes.object).isRequired
};


export default ThumbnailList;
