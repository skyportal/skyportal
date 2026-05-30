import React from "react";
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
  // Many cells render text inside a <p> (and sometimes headings). Browser
  // default margins on those block elements are taller than a compact row, so
  // the content gets vertically clipped ("half cut off"). Zero the margins so
  // the cell's own flex-centering positions the text correctly.
  "& .MuiDataGrid-cell p, & .MuiDataGrid-cell h1, & .MuiDataGrid-cell h2, & .MuiDataGrid-cell h3, & .MuiDataGrid-cell h4, & .MuiDataGrid-cell h5, & .MuiDataGrid-cell h6":
    {
      margin: 0,
    },
  "& .MuiDataGrid-cell:focus, & .MuiDataGrid-cell:focus-within": {
    outline: "none",
  },
};

// Loose props: `sx` is optional and everything else is forwarded straight to
// the underlying DataGrid (columns/rows/pagination/etc.). Kept as `any` to
// match the non-strict migration — DataGrid's own prop types are large and
// version-sensitive, and call sites already pass a validated shape.
interface StyledDataGridProps {
  sx?: any;
  [key: string]: any;
}

// DataGrid requires `columns`/`rows`; those are supplied by callers via the
// forwarded `...props`. Cast to a loose component so the spread satisfies the
// required props without re-declaring DataGrid's (large, version-sensitive)
// prop types here.
const LooseDataGrid = DataGrid as any;

const StyledDataGrid = ({ sx, ...props }: StyledDataGridProps) => (
  <LooseDataGrid
    density="compact"
    disableRowSelectionOnClick
    sx={[baseSx, ...(Array.isArray(sx) ? sx : [sx])]}
    {...props}
  />
);

export default StyledDataGrid;
