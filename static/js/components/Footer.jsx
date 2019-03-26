import React from 'react';
import PropTypes from 'prop-types';

import styles from './Footer.css';


const Footer = ({ version }) => (
  <div className={styles.footer}>
    <div className={styles.footerContent}>
      SkyPortal v{version}. Please file issues at&nbsp;
      <a href="https://github.com/skyportal/skyportal">
        https://github.com/skyportal/skyportal
      </a>
      .
    </div>
  </div>
);
Footer.propTypes = {
  version: PropTypes.string
};
Footer.defaultProps = {
  version: '0.0.0'
};

export default Footer;
