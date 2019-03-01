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
    case "ps1":
      alt = "Link to PanSTARRS-1 Image Access";
      link = `http://ps1images.stsci.edu/cgi-bin/ps1cutouts?pos=${ra}+${dec}&filter=color&filter=g&filter=r&filter=i&filter=z&filter=y&filetypes=stack&auxiliary=data&size=240&output_size=0&verbose=0&autoscale=99.500000&catlist=`;
      break;
  }

  const thumbnailDivClassNames = classnames(styles.Thumbnail, { [styles.ps1]: name === "ps1" });

  return (
    <a href={link}>
      {name === "ps1" && <br />}
      <div className={thumbnailDivClassNames}>
        <b>
          {name.toUpperCase()}
        </b>
        <br />
        <div className={styles.thumbnailimgdiv}>
          <img className={name === "ps1" && styles.ps1crosshairs} src={url} alt={alt} title={alt} />
          {(name === "ps1") &&
          <img className={styles.ps1crosshairs} src="/static/images/crosshairs.png" alt="" />
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
  const thumbnail_order = ['new', 'ref', 'sub', 'sdss', 'ps1'];
  // Sort thumbnails by order of appearance in `thumbnail_order`
  thumbnails.sort((a, b) => (thumbnail_order.indexOf(a.type) <
                             thumbnail_order.indexOf(b.type) ? -1 : 1));

  return (
    <div className={styles.ThumbnailList}>
      {thumbnails.map(t => (
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
