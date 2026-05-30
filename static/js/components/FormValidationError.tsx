import React from "react";

interface FormValidationErrorProps {
  message: string;
}

const FormValidationError = ({ message }: FormValidationErrorProps) => (
  <div>
    <strong>
      <span style={{ color: "red" }}>{message}</span>
    </strong>
  </div>
);

export default FormValidationError;
