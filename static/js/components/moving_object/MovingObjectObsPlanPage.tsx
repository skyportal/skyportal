import { useState } from "react";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import dayjs from "dayjs";
import { showNotification } from "baselayer/components/Notifications";
import TextLoop from "react-text-loop";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import CircularProgress from "@mui/material/CircularProgress";
import { MyObjectFieldTemplate } from "../gcn/GcnSelectionForm";
import StyledDataGrid from "../StyledDataGrid";

import { useAppDispatch } from "../../types/hooks";
import { usePostMovingObjectObsPlanMutation } from "../../ducks/moving_object";
import { useGetInstrumentsQuery } from "../../ducks/instruments";

const COLUMNS = [
  {
    field: "start_time",
    headerName: "Start Time (UTC)",
    width: 180,
    valueFormatter: (value: string) =>
      dayjs(value).format("YYYY-MM-DD HH:mm:ss"),
  },
  {
    field: "field_id",
    headerName: "Field ID",
    flex: 1,
    minWidth: 90,
  },
  { field: "band", headerName: "Band", flex: 1, minWidth: 80 },
  {
    field: "airmass",
    headerName: "Airmass",
    flex: 1,
    minWidth: 110,
    valueFormatter: (value: number) => value.toFixed(2),
  },
  {
    field: "moon_distance",
    headerName: "Moon Distance",
    flex: 1,
    minWidth: 110,
    valueFormatter: (value: number) => value.toFixed(2),
  },
  {
    field: "sun_altitude",
    headerName: "Sun Altitude",
    flex: 1,
    minWidth: 110,
    valueFormatter: (value: number) => value.toFixed(2),
  },
];

const MovingObjectObsPlanPage = () => {
  const { data: instruments = [] } = useGetInstrumentsQuery();
  const dispatch = useAppDispatch();
  const [postMovingObjectObsPlan, { isLoading }] =
    usePostMovingObjectObsPlanMutation();

  const [formData, setFormData] = useState<any>({});
  const [planData, setPlanData] = useState<any[]>([]);

  const validInstruments = instruments.filter(
    (instrument: any) =>
      (instrument.filters?.length ?? 0) > 0 && instrument.has_fields === true,
  );

  const onFormSubmit = async ({ formData: submitted }: any) => {
    const { data: result } = await postMovingObjectObsPlan({
      name: submitted.name.replace(/\s/g, ""),
      // name is a path param and the API rejects unknown body keys
      data: Object.fromEntries(
        Object.entries(submitted).filter(([k, v]) => k !== "name" && v != null),
      ),
    });
    if (!result) return;
    if (result.length === 0) {
      dispatch(
        showNotification("No fields found for the given criteria", "warning"),
      );
    } else {
      dispatch(
        showNotification("Observation plan generated successfully", "info"),
      );
      setPlanData(result.map((row: any, id: number) => ({ ...row, id })));
    }
  };

  const formSchema = {
    type: "object",
    properties: {
      name: {
        type: "string",
        title: "Moving Object Name",
        default: "2025 BS6",
      },
      instrument_id: {
        type: "integer",
        title: "Instrument",
        enum: validInstruments.map((instrument: any) => instrument.id),
      },
      start_time: {
        type: "string",
        format: "date-time",
        title: "Start Time (UTC)",
        default: new Date().toISOString().split(".")[0],
      },
      end_time: {
        type: "string",
        format: "date-time",
        title: "End Time (UTC)",
        default: dayjs().add(1, "day").toISOString().split(".")[0],
      },
      exposure_count: {
        type: "number",
        title: "Exposure Count",
        default: 1,
      },
      exposure_time: {
        type: "number",
        title: "Exposure Time (seconds)",
        default: 30,
      },
      filter: {
        type: "string",
        title: "Filter",
        enum:
          instruments.find((i: any) => i.id === formData.instrument_id)
            ?.filters || [],
      },
      primary_only: {
        type: "boolean",
        title: "Primary Grid Only",
        default: false,
        description:
          "If checked, only fields from the primary grid will be used (where applicable).",
      },
      airmass_limit: {
        type: "number",
        title: "Airmass Limit",
        default: 2.5,
        minimum: 1,
        maximum: 8,
      },
      moon_distance_limit: {
        type: "number",
        title: "Moon Distance Limit",
        default: 30,
      },
      sun_altitude_limit: {
        type: "number",
        title: "Sun Altitude Limit",
        default: -18,
      },
    },
    required: [
      "name",
      "instrument_id",
      "start_time",
      "end_time",
      "exposure_count",
      "exposure_time",
      "filter",
    ],
  };

  const uiSchema = {
    instrument_id: {
      "ui:enumNames": validInstruments.map(
        (instrument: any) => instrument.name,
      ),
    },
    "ui:grid": [
      { name: 12 },
      { instrument_id: 6, filter: 6 },
      { start_time: 6, end_time: 6 },
      { exposure_count: 6, exposure_time: 6 },
      { primary_only: 12 },
      { airmass_limit: 4, moon_distance_limit: 4, sun_altitude_limit: 4 },
    ],
  };

  return (
    <Grid container spacing={2}>
      <Grid size={{ lg: 5, md: 12 }}>
        <Paper sx={{ p: "1rem", mb: "1rem" }}>
          <Form
            schema={formSchema as any}
            formData={formData}
            onChange={(e) => setFormData(e.formData)}
            onSubmit={onFormSubmit}
            validator={validator}
            uiSchema={uiSchema as any}
            templates={{ ObjectFieldTemplate: MyObjectFieldTemplate }}
          />
        </Paper>
      </Grid>
      <Grid size={{ lg: 7, md: 12 }}>
        <Paper sx={{ height: "calc(100vh - 5.25rem)" }}>
          <StyledDataGrid rows={planData} columns={COLUMNS} />
        </Paper>
      </Grid>
      <Dialog open={isLoading} maxWidth="sm" fullWidth>
        <DialogContent
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "2rem",
            fontWeight: "bold",
            fontSize: "1.25rem",
          }}
        >
          <TextLoop interval={1500}>
            <span>Retrieving data from JPL Horizons</span>
            <span>Calculating airmass</span>
            <span>Checking moon distance</span>
            <span>Checking sun altitude</span>
            <span>Finding observable fields</span>
            <span>Generating observation plan</span>
          </TextLoop>
          <CircularProgress color="primary" />
        </DialogContent>
      </Dialog>
    </Grid>
  );
};

export default MovingObjectObsPlanPage;
