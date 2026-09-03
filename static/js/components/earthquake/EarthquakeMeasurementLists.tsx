import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Typography from "@mui/material/Typography";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { makeStyles } from "tss-react/mui";

import { useGetMMADetectorsQuery } from "../../ducks/mmadetector";
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
  {
    field: "rfamp",
    headerName: "Amplitude measurement [m/s]",
    flex: 1,
    minWidth: 200,
    sortable: false,
  },
  {
    field: "lockloss",
    headerName: "Lockloss Measurement",
    flex: 1,
    minWidth: 160,
    sortable: false,
  },
];

interface EarthquakeMeasurementListsProps {
  earthquake: any;
}

const EarthquakeMeasurementLists = ({
  earthquake,
}: EarthquakeMeasurementListsProps) => {
  const { classes } = useStyles();

  const { data: mmadetectorList } = useGetMMADetectorsQuery();

  if (!mmadetectorList || mmadetectorList.length === 0) {
    return <p>Need mmadetectors to make measurements...</p>;
  }

  if (!earthquake.measurements || earthquake.measurements.length === 0) {
    return <p>No measurements for this event...</p>;
  }

  const mmadetectorLookUp = mmadetectorList.reduce((r: any, a: any) => {
    r[a.id] = a;
    return r;
  }, {});

  const analysesGroupedByMMADetectorId = earthquake.measurements.reduce(
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
            data-testid={`${mmadetectorLookUp[mmadetector_id].name}_measurementsTable`}
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

export default EarthquakeMeasurementLists;
