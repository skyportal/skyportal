import React from "react";
import PropTypes from "prop-types";
import { useSelector } from "react-redux";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
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

const EarthquakePredictionLists = ({ earthquake }) => {
  const classes = useStyles();
  const theme = useTheme();

  const { mmadetectorList } = useSelector((state) => state.mmadetectors);

  if (!mmadetectorList || mmadetectorList.length === 0) {
    return <p>Need mmadetectors to make predictions...</p>;
  }

  if (!earthquake.predictions || earthquake.predictions.length === 0) {
    return <p>No predictions for this event...</p>;
  }

  const mmadetectorLookUp = mmadetectorList.reduce((r, a) => {
    r[a.id] = a;
    return r;
  }, {});

  const analysesGroupedByMMADetectorId = earthquake.predictions.reduce(
    (r, a) => {
      r[a.detector_id] = [...(r[a.detector_id] || []), a];
      return r;
    },
    {},
  );

  Object.values(analysesGroupedByMMADetectorId).forEach((value) => {
    value.sort();
  });

  const columns = [
    { name: "d", label: "Distance [km]" },
    { name: "p", label: "P-wave time" },
    { name: "s", label: "S-wave time" },
    { name: "r2p0", label: "R-2.0 km/s-wave time" },
    { name: "r3p5", label: "R-3.5 km/s-wave time" },
    { name: "r5p0", label: "R-5.0 km/s-wave time" },
    { name: "rfamp", label: "Amplitude prediction [m/s]" },
    { name: "lockloss", label: "Lockloss Prediction" },
  ];

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
      {Object.keys(analysesGroupedByMMADetectorId).map((mmadetector_id) => (
        <Accordion
          className={classes.accordion}
          key={`mmadetector_${mmadetector_id}_table_div`}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls={`${mmadetectorLookUp[mmadetector_id].name}-requests`}
            data-testid={`${mmadetectorLookUp[mmadetector_id].name}-requests-header`}
          >
            <Typography variant="subtitle1">
              {mmadetectorLookUp[mmadetector_id].name} Requests
            </Typography>
          </AccordionSummary>
          <AccordionDetails
            data-testid={`${mmadetectorLookUp[mmadetector_id].name}_predictionsTable`}
          >
            <StyledEngineProvider injectFirst>
              <ThemeProvider theme={getMuiTheme(theme)}>
                <MUIDataTable
                  data={analysesGroupedByMMADetectorId[mmadetector_id]}
                  options={options}
                  columns={columns}
                />
              </ThemeProvider>
            </StyledEngineProvider>
          </AccordionDetails>
        </Accordion>
      ))}
    </div>
  );
};

EarthquakePredictionLists.propTypes = {
  earthquake: PropTypes.shape({
    predictions: PropTypes.arrayOf(
      PropTypes.shape({
        mmadetector_id: PropTypes.number,
        id: PropTypes.number,
        payload: PropTypes.objectOf(PropTypes.any).isRequired, // eslint-disable-line react/forbid-prop-types,
        status: PropTypes.string,
      }),
    ),
  }).isRequired,
};

export default EarthquakePredictionLists;
