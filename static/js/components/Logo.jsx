import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";
import styles from "./Logo.css";

const Logo = ({ src, altText }) => {
  const rotateLogo = useSelector((state) => state.logo.rotateLogo);
  return (
    <div className={styles.logoContainer}>
      <img
        alt={altText}
        className={rotateLogo ? styles.rotateLogo : styles.noRotateLogo}
        src={src}
      />
    </div>
  );
};

Logo.propTypes = {
  src: PropTypes.string,
  altText: PropTypes.string,
};

Logo.defaultProps = {
  src: "/static/images/skyportal_logo_dark.png",
  altText: "SkyPortal logo",
};

export default Logo;
