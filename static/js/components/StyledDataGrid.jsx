import React from "react";
import PropTypes from "prop-types";
import { DataGrid } from "@mui/x-data-grid";

// Shared, theme-aware wrapper around MUI X DataGrid.
//
// Unlike the old mui-datatables setup, DataGrid inherits the app's MUI theme
// directly, so no getMuiTheme()/ThemeProvider hack is needed. DataGrid also
// virtualizes rows (and columns) by default: only the cells inside the
// scroll viewport are mounted, so a table backed by a very large `rows` array
// renders a bounded number of DOM nodes regardless of total row count. That is
// what keeps source lists and photometry tables responsive at Argus rates.
//
// Defaults here are the conventions we want everywhere; any of them can be
// overridden by passing the same prop at the call site.
const baseSx = {
  border: "none",
  "& .MuiDataGrid-cell": {
    padding: "0.25rem 0.5rem",
  },
  "& .MuiDataGrid-columnHeader": {
    padding: "0.25rem 0.5rem",
  },
  // Let cell content wrap instead of being clipped, matching the old table.
  "& .MuiDataGrid-cell:focus, & .MuiDataGrid-cell:focus-within": {
    outline: "none",
  },
};

const StyledDataGrid = ({ sx, ...props }) => (
  <DataGrid
    density="compact"
    disableRowSelectionOnClick
    sx={[baseSx, ...(Array.isArray(sx) ? sx : [sx])]}
    {...props}
  />
);

StyledDataGrid.propTypes = {
  // MUI's sx prop accepts an object or an array of objects/functions.
  sx: PropTypes.oneOfType([PropTypes.object, PropTypes.array]),
};

StyledDataGrid.defaultProps = {
  sx: undefined,
};

export default StyledDataGrid;
