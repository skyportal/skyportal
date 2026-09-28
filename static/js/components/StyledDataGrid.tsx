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
import {
  TextField,
  Tooltip,
  InputAdornment,
  Typography,
  Box,
} from "@mui/material";
import ViewColumnIcon from "@mui/icons-material/ViewColumn";
import FilterListIcon from "@mui/icons-material/FilterList";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import SearchIcon from "@mui/icons-material/Search";
import UnfoldMoreIcon from "@mui/icons-material/UnfoldMore";
import UnfoldLessIcon from "@mui/icons-material/UnfoldLess";
import { useContext } from "react";

import { ExpandAllContext, ExpandAllProvider } from "./ExpandableCell";

export const FULL_PAGE_HEIGHT = "calc(100vh - 5.25rem)";
export const FULL_PAGE_HEIGHT_WITH_TABS = "calc(100vh - 5.25rem - 49px - 1rem)";

const baseSx = (theme: any) => ({
  border: `1px solid ${theme.palette.divider}`,
  borderRadius: 1,
  overflow: "hidden",
  "& .MuiDataGrid-cell": {
    padding: "0.5rem 0.75rem",
    borderColor: theme.palette.divider,
  },
  "& .MuiDataGrid-columnHeaders": {
    borderBottom: `1px solid ${theme.palette.divider}`,
  },
  "& .MuiDataGrid-columnHeader": {
    padding: "0.5rem 0.75rem",
    backgroundColor:
      theme.palette.mode === "dark"
        ? theme.palette.grey[900]
        : theme.palette.grey[100],
  },
  "& .MuiDataGrid-columnHeaderTitle": {
    fontWeight: 600,
  },
  "& .MuiDataGrid-row:hover": {
    backgroundColor: theme.palette.action.hover,
  },
  // Default <p>/heading margins clip text in compact rows.
  "& .MuiDataGrid-cell p, & .MuiDataGrid-cell h1, & .MuiDataGrid-cell h2, & .MuiDataGrid-cell h3, & .MuiDataGrid-cell h4, & .MuiDataGrid-cell h5, & .MuiDataGrid-cell h6":
    {
      margin: 0,
    },
  "& .MuiDataGrid-cell:focus, & .MuiDataGrid-cell:focus-within": {
    outline: "none",
  },
});

interface StyledDataGridProps {
  sx?: any;
  initialState?: any;
  [key: string]: any;
}

const LooseDataGrid = DataGrid as any;

const StyledDataGrid = ({
  sx,
  initialState,
  ...props
}: StyledDataGridProps) => (
  <ExpandAllProvider>
    <LooseDataGrid
      density="standard"
      disableRowSelectionOnClick
      sx={[baseSx, ...(Array.isArray(sx) ? sx : [sx])]}
      initialState={{
        ...initialState,
        pagination: {
          ...initialState?.pagination,
          paginationModel: {
            pageSize: 25,
            ...initialState?.pagination?.paginationModel,
          },
        },
      }}
      {...props}
    />
  </ExpandAllProvider>
);

const ExpandAllButton = () => {
  const { expandAll, setExpandAll } = useContext(ExpandAllContext);
  const label = expandAll ? "Collapse all" : "Expand all";
  return (
    <Tooltip title={label}>
      <ToolbarButton
        aria-label={label}
        onClick={() => setExpandAll(!expandAll)}
      >
        {expandAll ? (
          <UnfoldLessIcon fontSize="small" />
        ) : (
          <UnfoldMoreIcon fontSize="small" />
        )}
      </ToolbarButton>
    </Tooltip>
  );
};

export const DataGridToolbar = ({
  children,
  title,
  showColumns = true,
  showQuickFilter = true,
  showFilter = false,
  showExport = true,
  showExpandAll = false,
  quickFilterTestId,
}: {
  children?: any;
  title?: string;
  showColumns?: boolean;
  showQuickFilter?: boolean;
  showFilter?: boolean;
  showExport?: boolean;
  showExpandAll?: boolean;
  quickFilterTestId?: string;
}) => (
  <Toolbar>
    {title && (
      <>
        <Typography variant="h6" sx={{ ml: 1, mr: 1 }}>
          {title}
        </Typography>
        <Box sx={{ flexGrow: 1 }} />
      </>
    )}
    {showExpandAll && <ExpandAllButton />}
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
              aria-label="Search"
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" />
                    </InputAdornment>
                  ),
                },
              }}
            />
          )}
        />
      </QuickFilter>
    )}
  </Toolbar>
);

export default StyledDataGrid;
