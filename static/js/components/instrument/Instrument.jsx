import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import RefreshIcon from "@mui/icons-material/Refresh";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import PropTypes from "prop-types";
import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";

import JsonDashboard from "react-json-dashboard";
import { Link } from "react-router-dom";
import withRouter from "../withRouter";
import * as Action from "../../ducks/instrument";
import InstrumentLogForm from "./InstrumentLogForm";
import InstrumentLogsPlot from "./InstrumentLogsPlot";
import Paper from "../Paper";

dayjs.extend(utc);

const Instrument = ({ route }) => {
  const dispatch = useDispatch();
  const instrument = useSelector((state) => state.instrument);
  const { telescopeList } = useSelector((state) => state.telescopes);
  const telescope = telescopeList.find(
    (t) => t.id === instrument?.telescope_id,
  );
  const [loading, setLoading] = useState(false);

  const defaultStartDate = dayjs
    .utc()
    .subtract(2, "day")
    .format("YYYY-MM-DD HH:mm:ss");
  const defaultEndDate = dayjs.utc().format("YYYY-MM-DD HH:mm:ss");

  // Load the instrument if needed
  useEffect(() => {
    dispatch(Action.fetchInstrument(route.id));

    setLoading(true);
    dispatch(
      Action.fetchInstrumentLogs(route.id, {
        startDate: defaultStartDate,
        endDate: defaultEndDate,
      }),
    ).then((response) => {
      if (response.status !== "success") {
        dispatch(showNotification("Error fetching instrument logs", "error"));
      }
      setLoading(false);
    });
  }, [route.id, dispatch]);

  if (!("id" in instrument && instrument.id === parseInt(route.id, 10))) {
    // Don't need to do this for instruments -- we can just let the page be blank for a short time
    return <CircularProgress />;
  }

  const handleSubmit = async ({ formData }) => {
    setLoading(true);
    dispatch(Action.fetchInstrumentLogs(route.id, formData)).then(
      (response) => {
        if (response.status !== "success") {
          dispatch(showNotification("Error fetching instrument logs", "error"));
        }
        setLoading(false);
      },
    );
  };

  const InstrumentSummaryFormSchema = {
    type: "object",
    properties: {
      startDate: {
        type: "string",
        format: "date-time",
        title: "Start Date",
        default: defaultStartDate,
      },
      endDate: {
        type: "string",
        format: "date-time",
        title: "End Date",
        default: defaultEndDate,
      },
    },
    required: ["startDate", "endDate"],
  };

  const refreshButton = (
    <IconButton
      color="primary"
      aria-label="refresh"
      style={{ margin: 0, padding: 0 }}
      onClick={() => {
        dispatch(Action.updateInstrumentStatus(route.id)).then((response) => {
          if (response.status === "success") {
            dispatch(showNotification("Instrument status updated"));
          } else {
            dispatch(
              showNotification("Error updating instrument status", "error"),
            );
          }
        });
      }}
    >
      <RefreshIcon />
    </IconButton>
  );

  return (
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <Typography variant="h5">{instrument.name}</Typography>
        {telescope ? (
          <Link to={`/telescope/${instrument.telescope_id}`}>
            {telescope.name} ({telescope.nickname})
          </Link>
        ) : (
          <CircularProgress size={20} />
        )}
      </Grid>
      <Grid item xs={12}>
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h5">Instrument Log Display</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div>
              {loading && <CircularProgress />}
              {!loading && !instrument.log_exists && <div> No logs exist </div>}
              {!loading &&
                instrument.log_exists &&
                instrument?.logs?.length === 0 && (
                  <div> No logs exist in the specified time range </div>
                )}
              {!loading &&
                instrument.log_exists &&
                instrument?.logs?.length > 0 && (
                  <InstrumentLogsPlot
                    instrument_logs={instrument?.logs || []}
                  />
                )}
            </div>
            <div>
              <Form
                schema={InstrumentSummaryFormSchema}
                validator={validator}
                onSubmit={handleSubmit}
              />
            </div>
          </AccordionDetails>
        </Accordion>
        <Accordion defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h5">Instrument Log Query</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <InstrumentLogForm instrument={instrument} />
          </AccordionDetails>
        </Accordion>
        <Paper>
          <JsonDashboard
            title={`${instrument?.name || "Instrument"} Status`}
            data={instrument?.status || {}}
            lastUpdated={instrument?.last_status_update}
            refreshButton={refreshButton}
          />
        </Paper>
      </Grid>
    </Grid>
  );
};

Instrument.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.number,
  }).isRequired,
};

export default withRouter(Instrument);
