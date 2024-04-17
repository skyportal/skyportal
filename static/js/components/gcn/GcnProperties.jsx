import React from "react";
import PropTypes from "prop-types";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
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

const GcnProperties = ({ properties }) => {
  const classes = useStyles();
  const theme = useTheme();

  if (!properties || properties.length === 0) {
    return <p>No properties for this event...</p>;
  }

  // properties list of dicts each with a "created_at" key and a "data" key
  // we want to refactor that to a list of dicts with a "created_at" key and
  // a key for each property name

  // that means that first we need the list of all property names of all elements in the list
  const propertyNames = properties
    .map((property) => Object.keys(property.data))
    .flat();
  // then we need to remove duplicates
  const uniquePropertyNames = [...new Set(propertyNames)];

  // now we can create a list of dicts with a "created_at" key and a key for each property name
  const propertiesWithUniqueKeys = properties.map((property) => {
    const newProperty = { created_at: property.created_at };
    uniquePropertyNames.forEach((name) => {
      if (Object.keys(property.data).includes(name)) {
        if (typeof property.data[name] === "number") {
          if (property.data[name] > 10000 || property.data[name] < -10000) {
            newProperty[name] = property.data[name].toExponential(4);
          } else if (
            property.data[name] > 0.0001 ||
            property.data[name] < -0.0001
          ) {
            newProperty[name] = property.data[name].toFixed(4);
          } else if (property.data[name] === 0) {
            newProperty[name] = 0;
          } else {
            newProperty[name] = property.data[name].toExponential(4);
          }
        } else {
          newProperty[name] = property.data[name];
        }
      } else {
        newProperty[name] = null;
      }
    });
    return newProperty;
  });

  const getDataTableColumns = () => {
    const columns = [{ name: "created_at", label: "Created at" }];
    uniquePropertyNames.forEach((name) => {
      columns.push({
        name,
        label: name,
      });
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
            data={propertiesWithUniqueKeys}
            options={options}
            columns={getDataTableColumns()}
          />
        </ThemeProvider>
      </StyledEngineProvider>
    </div>
  );
};

GcnProperties.propTypes = {
  properties: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.number,
      data: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
    }),
  ).isRequired,
};

export default GcnProperties;
