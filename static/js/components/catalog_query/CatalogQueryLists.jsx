import React, { useState } from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import MUIDataTable from "mui-datatables";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Button from "../Button";

const useStyles = makeStyles(() => ({
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    maxWidth: "100%",
    "& > *": {
      maxWidth: "inherit",
    },
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    overrides: {
      MUIDataTable: {
        paper: {
          width: "100%",
        },
      },
      MUIDataTableBodyCell: {
        stackedCommon: {
          overflow: "hidden",
          "&:last-child": {
            paddingLeft: "0.25rem",
          },
        },
      },
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
  });

const SourcesList = ({ sources }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };

  // reorder the sources list alphabetically descending
  sources.sort((a, b) => (a > b ? 1 : -1));

  return (
    <div>
      <Button
        size="small"
        id="basic-button"
        aria-controls={open ? "basic-menu" : undefined}
        aria-haspopup="true"
        aria-expanded={open ? "true" : undefined}
        onClick={handleClick}
      >
        Added {sources.length} sources
      </Button>
      <Menu
        id="basic-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          "aria-labelledby": "basic-button",
        }}
      >
        {sources.map((source) => (
          <MenuItem key={source}>
            <Link
              to={`/source/${source}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              {source}
            </Link>
          </MenuItem>
        ))}
      </Menu>
    </div>
  );
};

SourcesList.propTypes = {
  sources: PropTypes.arrayOf(PropTypes.string).isRequired,
};

const CatalogQueryLists = ({ catalog_queries }) => {
  const classes = useStyles();
  const theme = useTheme();

  if (!catalog_queries || catalog_queries.length === 0) {
    return <p>No catalog queries for this event.</p>;
  }

  const getDataTableColumns = () => {
    const columns = [];

    const renderStatus = (dataIndex) => {
      let text = <div>{catalog_queries[dataIndex]?.status}</div>;
      if (catalog_queries[dataIndex]?.status?.includes("completed: Added ")) {
        let transients =
          catalog_queries[dataIndex]?.status?.split("completed: Added ")[1];
        // split by commas
        transients = transients.split(",");
        text = <SourcesList sources={transients} />;
      }
      return text;
    };

    const renderPayload = (dataIndex) => {
      const analysis = catalog_queries[dataIndex];
      return <div>{JSON.stringify(analysis.payload)}</div>;
    };

    columns.push({
      name: "status",
      label: "Status",
      options: {
        customBodyRenderLite: renderStatus,
      },
    });

    columns.push({
      name: "ntransients",
      label: "Payload",
      options: {
        customBodyRenderLite: renderPayload,
      },
    });

    return columns;
  };

  const options = {
    filter: false,
    sort: false,
    print: true,
    download: true,
    search: true,
    selectableRows: "none",
    enableNestedDataAccess: ".",
    elevation: 0,
    rowsPerPageOptions: [1, 10, 15],
  };

  return (
    <div className={classes.container}>
      <StyledEngineProvider injectFirst>
        <ThemeProvider theme={getMuiTheme(theme)}>
          <MUIDataTable
            data={catalog_queries}
            options={options}
            columns={getDataTableColumns()}
          />
        </ThemeProvider>
      </StyledEngineProvider>
    </div>
  );
};

CatalogQueryLists.propTypes = {
  catalog_queries: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      payload: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
      status: PropTypes.string,
    }),
  ).isRequired,
};

export default CatalogQueryLists;
