import React from "react";
import PropTypes from "prop-types";
import Paper from "@mui/material/Paper";
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
  adaptV4Theme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";

import MUIDataTable from "mui-datatables";

import Button from "./Button";

const useStyles = makeStyles((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  eventTags: {
    marginLeft: "0.5rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme(
    adaptV4Theme({
      palette: theme.palette,
      overrides: {
        MUIDataTablePagination: {
          toolbar: {
            flexFlow: "row wrap",
            justifyContent: "flex-end",
            padding: "0.5rem 1rem 0",
            [theme.breakpoints.up("sm")]: {
              // Cancel out small screen styling and replace
              padding: "0px",
              paddingRight: "2px",
              flexFlow: "row nowrap",
            },
          },
          tableCellContainer: {
            padding: "1rem",
          },
          selectRoot: {
            marginRight: "0.5rem",
            [theme.breakpoints.up("sm")]: {
              marginLeft: "0",
              marginRight: "2rem",
            },
          },
        },
      },
    })
  );

const SpatialCatalogTable = ({
  catalog,
  totalMatches,
  setSelectedSpatialCatalogEntryId,
  pageNumber = 1,
  numPerPage = 10,
  serverSide = false,
  hideTitle = false,
}) => {
  const classes = useStyles();
  const theme = useTheme();

  if (!catalog || catalog.entries.length === 0) {
    return <p>No entries available...</p>;
  }

  const renderData = (dataIndex) => {
    const entry = catalog.entries[dataIndex];
    return <div>{JSON.stringify(entry.data)}</div>;
  };

  const renderRetrieveSources = (dataIndex) => {
    const entry = catalog.entries[dataIndex];
    if (!entry.entry_name) {
      return <div />;
    }
    return (
      <div>
        <Button
          primary
          onClick={() => {
            setSelectedSpatialCatalogEntryId(entry.id);
          }}
          size="small"
          type="submit"
          data-testid={`retrieveSources_${entry.id}`}
        >
          Retrieve Sources
        </Button>
      </div>
    );
  };

  const columns = [
    {
      name: "entry_name",
      label: "Entry Name",
    },
    {
      name: "data",
      label: "Entry data",
      options: {
        customBodyRenderLite: renderData,
      },
    },
    {
      name: "retrieve_sources",
      label: "Retrieve Sources",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderRetrieveSources,
      },
    },
  ];

  const options = {
    search: true,
    selectableRows: "none",
    elevation: 0,
    page: pageNumber - 1,
    rowsPerPage: numPerPage,
    rowsPerPageOptions: [2, 10, 25, 50, 100],
    jumpToPage: true,
    serverSide,
    pagination: true,
    count: totalMatches,
  };

  return (
    <div>
      {catalog.entries ? (
        <Paper className={classes.container}>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                title={!hideTitle ? "Catalog Entries" : ""}
                data={catalog.entries}
                options={options}
                columns={columns}
              />
            </ThemeProvider>
          </StyledEngineProvider>
        </Paper>
      ) : (
        <CircularProgress />
      )}
    </div>
  );
};

SpatialCatalogTable.propTypes = {
  catalog: PropTypes.shape({
    entries: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        entry_name: PropTypes.string,
        data: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
      })
    ),
  }),
  setSelectedSpatialCatalogEntryId: PropTypes.func.isRequired,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  hideTitle: PropTypes.bool,
  serverSide: PropTypes.bool,
};

SpatialCatalogTable.defaultProps = {
  catalog: null,
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
  hideTitle: false,
  serverSide: false,
};

export default SpatialCatalogTable;
