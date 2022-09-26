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
  accordion: {
    width: "100%",
  },
  container: {
    margin: "0rem 0",
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

const GcnProperties = ({ properties }) => {
  const classes = useStyles();
  const theme = useTheme();

  if (!properties || properties.length === 0) {
    return <p>No properties for this event...</p>;
  }

  const getDataTableColumns = () => {
    const columns = [{ name: "created_at", label: "Created at" }];

    const renderProperties = (dataIndex) => {
      const data = properties[dataIndex];
      return <div>{JSON.stringify(data.data)}</div>;
    };
    columns.push({
      name: "Properties",
      label: "Properties",
      options: {
        customBodyRenderLite: renderProperties,
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
      <Accordion className={classes.accordion} key="properties_table_div">
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="gcn-properties"
          data-testid="gcn-properties-header"
        >
          <Typography variant="subtitle1">Property Lists</Typography>
        </AccordionSummary>
        <AccordionDetails data-testid="gcn-properties-Table">
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                data={properties}
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

GcnProperties.propTypes = {
  properties: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      data: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
    })
  ).isRequired,
};

export default GcnProperties;
