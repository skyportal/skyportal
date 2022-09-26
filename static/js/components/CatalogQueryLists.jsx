import React from "react";
import PropTypes from "prop-types";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  createTheme,
  ThemeProvider,
  StyledEngineProvider,
  useTheme,
  adaptV4Theme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import MUIDataTable from "mui-datatables";

const useStyles = makeStyles(() => ({
  observationplanRequestTable: {
    borderSpacing: "0.7em",
  },
  actionButtons: {
    display: "flex",
    flexFlow: "row wrap",
    gap: "0.2rem",
  },
  accordion: {
    width: "99%",
  },
  container: {
    margin: "1rem 0",
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme(
    adaptV4Theme({
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
    })
  );

const CatalogQueryLists = ({ catalog_queries }) => {
  const classes = useStyles();
  const theme = useTheme();

  if (!catalog_queries || catalog_queries.length === 0) {
    return <p>No survey efficiency analyses for this event...</p>;
  }

  const getDataTableColumns = () => {
    const columns = [{ name: "status", label: "Status" }];

    const renderPayload = (dataIndex) => {
      const analysis = catalog_queries[dataIndex];
      return <div>{JSON.stringify(analysis.payload)}</div>;
    };
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
      <Accordion className={classes.accordion} key="catalog_query_table_div">
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="catalog-query-requests"
          data-testid="catalog-query-header"
        >
          <Typography variant="subtitle1">Catalog Query Requests</Typography>
        </AccordionSummary>
        <AccordionDetails data-testid="catalogQueryRequestsTable">
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                data={catalog_queries}
                options={options}
                columns={getDataTableColumns()}
              />
            </ThemeProvider>
          </StyledEngineProvider>
        </AccordionDetails>
      </Accordion>
    </div>
  );
};

CatalogQueryLists.propTypes = {
  catalog_queries: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      payload: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
      status: PropTypes.string,
    })
  ).isRequired,
};

export default CatalogQueryLists;
