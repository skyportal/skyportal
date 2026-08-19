import { useState } from "react";

import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FilterListIcon from "@mui/icons-material/FilterList";
import Autocomplete from "@mui/material/Autocomplete";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

import { AlertFilter, OPERATORS } from "./alertFields";

interface BrokerAlertFiltersProps {
  fields: string[];
  filters: AlertFilter[];
  onChange: (filters: AlertFilter[]) => void;
  label?: string;
}

const BrokerAlertFilters = ({
  fields,
  filters,
  onChange,
  label = "Filter results",
}: BrokerAlertFiltersProps) => {
  const [open, setOpen] = useState(false);

  const update = (index: number, patch: Partial<AlertFilter>) =>
    onChange(filters.map((f, i) => (i === index ? { ...f, ...patch } : f)));

  return (
    <Box sx={{ mb: 2 }}>
      <Button
        size="small"
        startIcon={<FilterListIcon />}
        endIcon={open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        onClick={() => setOpen(!open)}
      >
        {`${label}${filters.length ? ` (${filters.length})` : ""}`}
      </Button>
      <Collapse in={open} unmountOnExit>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1, mt: 1 }}>
          {filters.map((filter, index) => (
            <Box key={index} sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
              <Autocomplete
                size="small"
                sx={{ minWidth: 260 }}
                options={fields}
                value={filter.field || null}
                onChange={(_event, value) =>
                  update(index, { field: value ?? "" })
                }
                renderInput={(params) => (
                  <TextField {...params} label="Field" />
                )}
              />
              <TextField
                select
                size="small"
                label="Op"
                sx={{ minWidth: 110 }}
                value={filter.op}
                onChange={(e) => update(index, { op: e.target.value })}
              >
                {OPERATORS.map((op) => (
                  <MenuItem key={op} value={op}>
                    {op}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                size="small"
                label="Value"
                value={filter.value}
                onChange={(e) => update(index, { value: e.target.value })}
              />
              <IconButton
                size="small"
                aria-label="remove filter"
                onClick={() => onChange(filters.filter((_f, i) => i !== index))}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Box>
          ))}
          <Box>
            <Button
              size="small"
              startIcon={<AddIcon />}
              onClick={() =>
                onChange([...filters, { field: "", op: "=", value: "" }])
              }
            >
              Add filter
            </Button>
          </Box>
        </Box>
      </Collapse>
    </Box>
  );
};

export default BrokerAlertFilters;
