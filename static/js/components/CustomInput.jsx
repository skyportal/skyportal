import React from 'react';
import NumberFormat from 'react-number-format';
import PropTypes from 'prop-types';
import styles from './CustomInput.css';


const CustomInput = ({ type, name, value, onChange, placeholder, size, disabled, format, label }) => {
  // formatting time:
  // %Y-%m-%dT%H:%M:%S in UTC time, e.g. 2012-08-30T00:00:00
  // <NumberFormat format="####-##-##T##:##:##" mask="_"/
  const customInput =
    (
      <NumberFormat
        format="####-##-##T##:##:##"
        mask="_"
        className={styles.input}
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        size={size}
        placeholder={placeholder}
        disabled={disabled}
      />
    );

  const normalInput = (
    <input
      className={styles.input}
      type={type}
      name={name}
      value={value}
      onChange={onChange}
      size={size}
      placeholder={placeholder}
      disabled={disabled}
    />
  );

  let input = normalInput;

  if (format === "UTC") {
    input = customInput;
  }

  return (
    <div className={styles.inputWrapper}>
      <div className={styles.labelWrapper}>
        <label htmlFor={name} className={styles.label}>
          {label}
        </label>
      </div>
      {input}
    </div>
  );
};

CustomInput.propTypes = {
  type: PropTypes.oneOf(['number', 'text']).isRequired,
  name: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([
    PropTypes.number,
    PropTypes.string
  ]).isRequired,
  onChange: PropTypes.func.isRequired,
  size: PropTypes.string,
  placeholder: PropTypes.string,
  disabled: PropTypes.bool,
  label: PropTypes.string,
  format: PropTypes.oneOf([null, "UTC"])
};

CustomInput.defaultProps = {
  size: "6",
  placeholder: null,
  disabled: false,
  label: null,
  format: null
};


export default CustomInput;
