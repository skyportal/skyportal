import React from 'react';
import { useSelector } from 'react-redux';
import styles from './Logo.css';

const Logo = () => {
  const rotateLogo = useSelector((state) => state.logo.rotateLogo);
  return (
    <img
      alt="SkyPortal logo"
      className={rotateLogo ? styles.rotateLogo : styles.noRotateLogo}
      src="/static/images/skyportal_logo_dark.png"
    />
  );
};

export default Logo;
