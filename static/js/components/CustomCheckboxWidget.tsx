import Checkbox from "@mui/material/Checkbox";
import Tooltip from "@mui/material/Tooltip";
import InfoIcon from "@mui/icons-material/Info";
import { Theme as MuiTheme } from "@rjsf/mui";

interface CustomCheckboxWidgetProps {
  id: string;
  name: string;
  value: boolean;
  onChange: (value: boolean) => void;
  label: string;
  schema?: {
    description?: string;
    [key: string]: any;
  };
}

const CustomCheckboxWidget = ({
  id,
  name,
  value,
  onChange,
  label,
  schema,
}: CustomCheckboxWidgetProps) => {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <Checkbox
        {...({ type: "checkbox" } as any)}
        id={id}
        name={name}
        checked={value}
        onChange={(event) => onChange(event.target.checked)}
      />
      <label htmlFor={id}>{label}</label>
      {schema?.description && (
        <Tooltip
          title={<h3>{schema.description}</h3>}
          style={{ fontSize: "3rem" }}
        >
          <InfoIcon style={{ color: "grey", fontSize: "1rem" }} />
        </Tooltip>
      )}
    </div>
  );
};

export const CustomCheckboxWidgetMuiTheme = {
  ...MuiTheme,
  widgets: {
    ...MuiTheme.widgets,
    CheckboxWidget: CustomCheckboxWidget,
  },
};
