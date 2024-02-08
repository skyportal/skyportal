import React from "react";
import { useSelector } from "react-redux";
import PropTypes from "prop-types";
import makeStyles from "@mui/styles/makeStyles";

const useStyles = makeStyles(() => ({
  rotateLogo: {
    verticalAlign: "middle",
    height: "100%",
    animationName: "$rotateUp",
    animationDuration: "4s",
  },
  noRotateLogo: {
    verticalAlign: "middle",
    height: "100%",
  },
  "@keyframes rotateUp": {
    "0%": {
      transform: "rotate(60deg)",
    },
    "50%": {
      transform: "rotate(-10deg)",
    },
    "100%": {
      transform: "rotate(0deg)",
    },
  },
}));

const Logo = ({ src, altText }) => {
  const rotateLogo = useSelector((state) => state.logo.rotateLogo);
  const styles = useStyles();
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
