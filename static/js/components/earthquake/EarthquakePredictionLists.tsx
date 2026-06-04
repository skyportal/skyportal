import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { makeStyles } from "tss-react/mui";

import { useAppSelector } from "../../types/hooks";
import StyledDataGrid from "../StyledDataGrid";

const useStyles = makeStyles()(() => ({
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

const columns: any[] = [
  { field: "d", headerName: "Distance [km]", flex: 1, minWidth: 110 },
  { field: "p", headerName: "P-wave time", flex: 1, minWidth: 110 },
  { field: "s", headerName: "S-wave time", flex: 1, minWidth: 110 },
  { field: "r2p0", headerName: "R-2.0 km/s-wave time", flex: 1, minWidth: 150 },
  { field: "r3p5", headerName: "R-3.5 km/s-wave time", flex: 1, minWidth: 150 },
  { field: "r5p0", headerName: "R-5.0 km/s-wave time", flex: 1, minWidth: 150 },
  {
    field: "rfamp",
    headerName: "Amplitude prediction [m/s]",
    flex: 1,
    minWidth: 200,
  },
  {
    field: "lockloss",
    headerName: "Lockloss Prediction",
    flex: 1,
    minWidth: 160,
  },
].map((col) => ({ ...col, sortable: false }));

interface EarthquakePredictionListsProps {
  earthquake: any;
}

const EarthquakePredictionLists = ({
  earthquake,
}: EarthquakePredictionListsProps) => {
  const { classes } = useStyles();

  const { mmadetectorList } = useAppSelector(
    (state) => (state as any).mmadetectors,
  );

  if (!mmadetectorList || mmadetectorList.length === 0) {
    return <p>Need mmadetectors to make predictions...</p>;
  }

  if (!earthquake.predictions || earthquake.predictions.length === 0) {
    return <p>No predictions for this event...</p>;
  }

  const mmadetectorLookUp = mmadetectorList.reduce((r: any, a: any) => {
    r[a.id] = a;
    return r;
  }, {});

  const analysesGroupedByMMADetectorId = earthquake.predictions.reduce(
    (r: any, a: any) => {
      r[a.detector_id] = [...(r[a.detector_id] || []), a];
      return r;
    },
    {},
  );

  Object.values(analysesGroupedByMMADetectorId).forEach((value: any) => {
    value.sort();
  });

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
            <StyledDataGrid
              autoHeight
              rows={analysesGroupedByMMADetectorId[mmadetector_id]}
              columns={columns}
              getRowId={(row: any) => row.id}
              initialState={{
                pagination: { paginationModel: { pageSize: 10 } },
              }}
              pageSizeOptions={[1, 10, 15]}
              showToolbar
            />
          </AccordionDetails>
        </Accordion>
      ))}
    </div>
  );
};

export default EarthquakePredictionLists;
