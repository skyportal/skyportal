import {
  DataGrid,
  Toolbar,
  ToolbarButton,
  ColumnsPanelTrigger,
  FilterPanelTrigger,
  ExportCsv,
  QuickFilter,
  QuickFilterControl,
} from "@mui/x-data-grid";
import { TextField, Tooltip, InputAdornment } from "@mui/material";
import ViewColumnIcon from "@mui/icons-material/ViewColumn";
import FilterListIcon from "@mui/icons-material/FilterList";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import SearchIcon from "@mui/icons-material/Search";

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

// Shared v8 DataGrid toolbar. Replaces the deprecated GridToolbar* family
// (GridToolbarContainer/GridToolbarColumnsButton/GridToolbarQuickFilter), which
// MUI X v8 deprecates in favor of these composable primitives. Renders the
// columns-panel trigger + a quick-filter search box; `children` are slotted
// between for any table-specific buttons (download/export/etc.).
export const DataGridToolbar = ({
  children,
  showColumns = true,
  showQuickFilter = true,
  showFilter = false,
  showExport = false,
  quickFilterTestId,
}: {
  children?: any;
  showColumns?: boolean;
  showQuickFilter?: boolean;
  showFilter?: boolean;
  showExport?: boolean;
  quickFilterTestId?: string;
}) => (
  <Toolbar>
    {showColumns && (
      <Tooltip title="Columns">
        <ColumnsPanelTrigger
          render={
            <ToolbarButton
              aria-label="Columns"
              data-testid="datagrid-columns-button"
            />
          }
        >
          <ViewColumnIcon fontSize="small" />
        </ColumnsPanelTrigger>
      </Tooltip>
    )}
    {showFilter && (
      <Tooltip title="Filters">
        <FilterPanelTrigger
          render={
            <ToolbarButton
              aria-label="Filters"
              data-testid="datagrid-filter-button"
            />
          }
        >
          <FilterListIcon fontSize="small" />
        </FilterPanelTrigger>
      </Tooltip>
    )}
    {showExport && (
      <Tooltip title="Export CSV">
        <ExportCsv
          render={
            <ToolbarButton
              aria-label="Export CSV"
              data-testid="datagrid-export-button"
            />
          }
        >
          <FileDownloadIcon fontSize="small" />
        </ExportCsv>
      </Tooltip>
    )}
    {children}
    {showQuickFilter && (
      <QuickFilter data-testid={quickFilterTestId}>
        <QuickFilterControl
          render={({ ref, ...controlProps }: any) => (
            <TextField
              {...controlProps}
              inputRef={ref}
              size="small"
              placeholder="Search…"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              }}
            />
          )}
        />
      </QuickFilter>
    )}
  </Toolbar>
);

export default StyledDataGrid;
