import React from 'react';
import styles from './CheckBox.css';

const CheckBox = (props) => {
  return (
    <div className={styles.checkBoxWrapper}> 
      <label className={styles.label}> {props.label} </label>

      {/* A hack to style checkbox.
          Essentially overwrite the original 
          style completely. */}

      <label 
      className={styles.checkboxLabel}
      style={props.labelStyle}>
        <input
          type="checkbox"
          style={props.checkboxStyle}
          name={props.name}
          className={styles.CheckBox}
          checked={props.checked}
          onChange={props.onChange}
          size={props.size}/>
        <span className={styles.checkboxCustom}/>
      </label>
    </div>
  )
};

export default CheckBox;
