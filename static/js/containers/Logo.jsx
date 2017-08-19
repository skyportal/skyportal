import React from 'react';
import PropTypes from 'prop-types';
import { connect } from 'react-redux';
import styles from './Logo.css';

const Logo = ({ rotateLogo }) => (
  <img
    alt="SkyPortal logo"
    className={rotateLogo ? styles.rotateLogo : styles.noRotateLogo}
    src="/static/images/skyportal_logo_dark.png"
  />
);

Logo.defaultProps = {
  rotateLogo: false
};

Logo.propTypes = {
  rotateLogo: PropTypes.bool
};

const mapStateToProps = (state, ownProps) => {
  const { rotateLogo } = state.misc;
  return {
    rotateLogo
  };
};

export default connect(mapStateToProps)(Logo);
