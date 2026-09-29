import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { useGetMMADetectorsQuery } from "../../ducks/mmadetector";
import StyledDataGrid, { DataGridToolbar } from "../StyledDataGrid";

const columns = {
  predictions: [
    {
      field: "d",
      headerName: "Distance [km]",
      minWidth: 110,
      valueFormatter: (value: number) => value?.toFixed(1),
    },
    ...[
      ["p", "P-wave"],
      ["s", "S-wave"],
      ["r2p0", "R-2.0 km/s"],
      ["r3p5", "R-3.5 km/s"],
      ["r5p0", "R-5.0 km/s"],
    ].map(([field, headerName]) => ({
      field,
      headerName: `${headerName} (UTC)`,
      minWidth: 140,
      valueFormatter: (value: string) => value?.slice(11, 19),
    })),
    { field: "rfamp", headerName: "Amplitude prediction [m/s]", minWidth: 200 },
    { field: "lockloss", headerName: "Lockloss Prediction", minWidth: 160 },
  ],
  measurements: [
    {
      field: "rfamp",
      headerName: "Amplitude measurement [m/s]",
      minWidth: 200,
    },
    { field: "lockloss", headerName: "Lockloss Measurement", minWidth: 160 },
  ],
};

interface EarthquakeDetectorTablesProps {
  earthquake: any;
  kind: keyof typeof columns;
}

const EarthquakeDetectorTables = ({
  earthquake,
  kind,
}: EarthquakeDetectorTablesProps) => {
  const { data: detectors = [] } = useGetMMADetectorsQuery();
  const rows: any[] = earthquake[kind] ?? [];
  if (!rows.length) {
    return (
      <Typography sx={{ color: "text.secondary" }}>
        No {kind} for this event.
      </Typography>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      {[...new Set(rows.map((row) => row.detector_id))].map((detectorId) => (
        <StyledDataGrid
          key={detectorId}
          autoHeight
          rows={rows.filter((row) => row.detector_id === detectorId)}
          columns={columns[kind].map((col) => ({
            ...col,
            flex: 1,
            sortable: false,
          }))}
          slots={{ toolbar: DataGridToolbar }}
          slotProps={{
            toolbar: {
              title: detectors.find((d: any) => d.id === detectorId)?.name,
              showQuickFilter: false,
            },
          }}
          showToolbar
        />
      ))}
    </Box>
  );
};

export default EarthquakeDetectorTables;
