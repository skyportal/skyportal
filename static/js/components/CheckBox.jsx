import React from 'react';
import PropTypes from 'prop-types';

import styles from './CheckBox.css';


function CheckBox({ label, name, checked, onChange, size }) {
  return (
    <div className={styles.checkBoxWrapper}>
      <label htmlFor={name} className={styles.label}>
        {label}
      </label>
      <input htmlFor="dummy" className={styles.dummy} />
      <label
        className={styles.checkboxLabel}
        htmlFor="dummy"
      >
        <input
          type="checkbox"
          name={name}
          className={styles.CheckBox}
          checked={checked}
          onChange={onChange}
          size={size}
        />
        <span className={styles.checkboxCustom} />
      </label>
    </div>
  );
}

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
