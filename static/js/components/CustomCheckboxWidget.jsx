import Checkbox from "@mui/material/Checkbox";
import Tooltip from "@mui/material/Tooltip";
import InfoIcon from "@mui/icons-material/Info";
import PropTypes from "prop-types";
import { Theme as MuiTheme } from "@rjsf/mui";
import React from "react";

const CustomCheckboxWidget = ({ id, name, value, onChange, label, schema }) => {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <Checkbox
        type="checkbox"
        id={id}
        name={name}
        checked={value}
        onChange={(event) => onChange(event.target.checked)}
      />
      <label htmlFor={id}>{label}</label>
      {schema?.description && (
        <Tooltip
          title={<h3>{schema.description}</h3>}
          size="medium"
          style={{ fontSize: "3rem" }}
        >
          <InfoIcon size="small" style={{ color: "grey", fontSize: "1rem" }} />
        </Tooltip>
      )}
    </div>
  );
};

CustomCheckboxWidget.propTypes = {
  id: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
  value: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
  label: PropTypes.string.isRequired,
  schema: PropTypes.shape({
    description: PropTypes.string,
  }),
};

export const CustomCheckboxWidgetMuiTheme = {
  ...MuiTheme,
  widgets: {
    ...MuiTheme.widgets,
    CheckboxWidget: CustomCheckboxWidget,
  },
};
