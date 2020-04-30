import React from 'react';
import PropTypes from 'prop-types';


const BoldRedTextDiv = ({ message }) => (
  <div>
    <strong>
      <font color="red">
        {message}
      </font>
    </strong>
  </div>
);
BoldRedTextDiv.propTypes = {
  message: PropTypes.string.isRequired
};

export default BoldRedTextDiv;
