import React from 'react';
import { useSelector } from 'react-redux';

import styles from './Footer.css';


const Footer = () => {
  const version = useSelector((state) => state.sysInfo.version);
  return (
    <div className={styles.footer}>
      <div className={styles.footerContent}>
        SkyPortal v
        {version}
        . Please file issues at&nbsp;
        <a href="https://github.com/skyportal/skyportal">
          https://github.com/skyportal/skyportal
        </a>
        .
      </div>
    </div>
  );
};

export default Footer;
