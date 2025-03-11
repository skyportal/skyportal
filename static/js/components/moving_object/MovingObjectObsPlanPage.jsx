import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import { makeStyles } from "@mui/styles";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import { showNotification } from "baselayer/components/Notifications";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import TextLoop from "react-text-loop";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import CircularProgress from "@mui/material/CircularProgress";
import { MyObjectFieldTemplate } from "../gcn/GcnSelectionForm";

import * as movingObjectActions from "../../ducks/moving_object";

const useStyles = makeStyles((theme) => ({
  root: {
    width: "100%",
    backgroundColor: theme.palette.background.paper,
    whiteSpace: "pre-line",
  },
  paperContent: {
    padding: "1rem",
    marginBottom: "1rem",
  },
  spinner: {
    margin: "auto",
    fontWeight: "bold",
    fontSize: "1.25rem",
    textAlign: "center",
  },
}));

const PlaceHolder = () => {
  const classes = useStyles();
  return (
    <div className={classes.spinner}>
      <TextLoop interval={1500}>
        <span>Retrieving data from JPL Horizons</span>
        <span>Calculating airmass</span>
        <span>Checking moon distance</span>
        <span>Checking sun altitude</span>
        <span>Finding observable fields</span>
        <span>Generating observation plan</span>
      </TextLoop>{" "}
      <br /> <br />
      <CircularProgress color="primary" />
    </div>
  );
};

const MovingObjectObsPlanPage = () => {
  const classes = useStyles();
  const instruments = useSelector((state) => state.instruments.instrumentList);
  const dispatch = useDispatch();

  const [instrumentOptions, setInstrumentOptions] = useState([]);
  const [formData, setFormData] = useState({});

  const [planData, setPlanData] = useState([]);
  const [loading, setLoading] = useState(false);

  const defaultStartTime = new Date();
  const defaultEndTime = new Date();
  defaultEndTime.setHours(defaultEndTime.getHours() + 24);

  useEffect(() => {
    let valid_instruments = (instruments || [])
      .filter(
        (instrument) =>
          instrument.filters.length > 0 && instrument.has_fields === true,
      )
      .map((instrument) => ({
        type: "integer",
        title: instrument.name,
        enum: [instrument.id],
      }));

    setInstrumentOptions(valid_instruments);
  }, [instruments]);

  function onFormSubmit(params) {
    setLoading(true);
    let name = params.formData.name.replace(/\s/g, "");
    let data = Object.fromEntries(
      Object.entries(params.formData).filter(([_, v]) => v != null),
    );
    dispatch(movingObjectActions.postMovingObjectObsPlan(name, data)).then(
      (result) => {
        if (result.status === "success") {
          if (result.data.length === 0) {
            dispatch(
              showNotification(
                "No fields found for the given criteria",
                "warning",
              ),
            );
          } else {
            dispatch(
              showNotification(
                "Observation plan generated successfully",
                "info",
              ),
            );
            setPlanData(result.data);
          }
        }
        setLoading(false);
      },
    );
  }

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
        anyOf: instrumentOptions,
      },
      start_time: {
        type: "string",
        format: "date-time",
        title: "Start Time (UTC)",
        default: defaultStartTime.toISOString().split(".")[0],
      },
      end_time: {
        type: "string",
        format: "date-time",
        title: "End Time (UTC)",
        default: defaultEndTime.toISOString().split(".")[0],
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
          (instruments || []).filter((i) => i.id === formData.instrument_id)[0]
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

  // we want to have a form with a nice layout, with 2 columns
  const uiSchema = {
    "ui:grid": [
      {
        name: 12,
      },
      {
        instrument_id: 6,
        filter: 6,
      },
      {
        start_time: 6,
        end_time: 6,
      },
      {
        exposure_count: 6,
        exposure_time: 6,
      },
      {
        primary_only: 12,
      },
      {
        airmass_limit: 4,
        moon_distance_limit: 4,
        sun_altitude_limit: 4,
      },
    ],
  };

  if (!instruments) {
    return "Loading...";
  }

  return (
    <Grid container spacing={2}>
      <Grid item lg={5} md={12}>
        <Paper elevation={1}>
          <div className={classes.paperContent}>
            <Form
              schema={formSchema}
              formData={formData}
              onChange={(e) => setFormData(e.formData)}
              onSubmit={onFormSubmit}
              validator={validator}
              uiSchema={uiSchema}
              templates={{ ObjectFieldTemplate: MyObjectFieldTemplate }}
            />
          </div>
        </Paper>
      </Grid>
      <Grid item lg={7} md={12}>
        <Paper elevation={1}>
          <TableContainer>
            <Table sx={{ minWidth: 650 }} aria-label="simple table">
              <TableHead>
                <TableRow>
                  <TableCell>Start Time</TableCell>
                  <TableCell>Field ID</TableCell>
                  <TableCell>Band</TableCell>
                  <TableCell>Airmass</TableCell>
                  <TableCell>Moon Distance</TableCell>
                  <TableCell>Sun Altitude</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {planData.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{row.start_time}</TableCell>
                    <TableCell>{row.field_id}</TableCell>
                    <TableCell>{row.band}</TableCell>
                    <TableCell>{row.airmass.toFixed(2)}</TableCell>
                    <TableCell>{row.moon_distance.toFixed(2)}</TableCell>
                    <TableCell>{row.sun_altitude.toFixed(2)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      </Grid>
      <Dialog open={loading} maxWidth="sm" fullWidth>
        <DialogContent>
          <PlaceHolder />
        </DialogContent>
      </Dialog>
    </Grid>
  );
};

export default MovingObjectObsPlanPage;
