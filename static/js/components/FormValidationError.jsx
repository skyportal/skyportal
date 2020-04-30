import React from 'react';
import PropTypes from 'prop-types';


const FormValidationError = ({ message }) => (
  <div>
    <strong>
      <font color="red">
        {message}
      </font>
    </strong>
  </div>
);
FormValidationError.propTypes = {
  message: PropTypes.string.isRequired
};

export default FormValidationError;
