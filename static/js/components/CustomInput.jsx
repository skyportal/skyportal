import React from 'react';
import styles from './CustomInput.css';
import NumberFormat from 'react-number-format';

const CustomInput = (props) => {

    // formatting time:
    // %Y-%m-%dT%H:%M:%S in UTC time, e.g. 2012-08-30T00:00:00
    // <NumberFormat format="####-##-##T##:##:##" mask="_"/>

  const customInput =  
    <NumberFormat 
    format="####-##-##T##:##:##" mask="_" 
    className={styles.input}
    type={props.type}
    name={props.name}
    value={props.value}
    onChange={props.onChange}
    size={props.size}
    placeholder={props.placeholder}
    disabled={props.disabled}/>

  const normalInput = <input
    className={styles.input}
    type={props.type}
    name={props.name}
    value={props.value}
    onChange={props.onChange}
    size={props.size}
    placeholder={props.placeholder}
    disabled={props.disabled}/>

  let input = normalInput

  if (props.format == "time") {
    input = customInput
  }

  return (
    <div className={styles.inputWrapper}> 
    <div className={styles.labelWrapper}>
      <label className={styles.label}> {props.label} </label>
    </div>
      {input}
    </div>
  )
};

export default CustomInput;
