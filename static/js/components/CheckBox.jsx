import React from "react";
import PropTypes from "prop-types";

import styles from "./CheckBox.css";

const CheckBox = ({ label, name, checked, onChange, size }) => (
  <div className={styles.checkBoxWrapper}>
    <label htmlFor={name} className={styles.label}>
      {label}
    </label>
    <input
      type="checkbox"
      name={name}
      className={styles.CheckBox}
      checked={checked}
      onChange={onChange}
      size={size}
    />
  </div>
);

CheckBox.propTypes = {
  label: PropTypes.string,
  checked: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
  name: PropTypes.string.isRequired,
  size: PropTypes.string
};

CheckBox.defaultProps = {
  label: null,
  size: "6"
};

export default CheckBox;
