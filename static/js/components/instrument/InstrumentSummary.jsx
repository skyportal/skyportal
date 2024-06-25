import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import RefreshIcon from "@mui/icons-material/Refresh";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import makeStyles from "@mui/styles/makeStyles";
import PropTypes from "prop-types";
import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";

import Paper from "@mui/material/Paper";
import IconButton from "@mui/material/IconButton";
import JsonDashboard from "react-json-dashboard";
import withRouter from "../withRouter";
import * as Action from "../../ducks/instrument";
import InstrumentLogForm from "./InstrumentLogForm";
import InstrumentLogsPlot from "./InstrumentLogsPlot";

dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
  displayInlineBlock: {
    display: "inline-block",
  },
  center: {
    margin: "auto",
    padding: "0.625rem",
  },
  columnItem: {
    marginBottom: theme.spacing(1),
  },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
}));

const InstrumentSummary = ({ route }) => {
  const dispatch = useDispatch();
  const styles = useStyles();
  const instrument = useSelector((state) => state.instrument);

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
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
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
    <div>
      <Grid container spacing={2} className={styles.source}>
        <Grid item xs={12}>
          <div>
            <Accordion defaultExpanded>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="instrument-log-content"
                id="instrument-log-header"
              >
                <Typography className={styles.accordionHeading}>
                  Instrument Log Display
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <div className={styles.columnItem}>
                  {loading && <CircularProgress color="secondary" />}
                  {!loading && !instrument.log_exists && (
                    <div> No logs exist </div>
                  )}
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
          </div>
          <div>
            <Accordion defaultExpanded>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="instrument-log-query"
                id="instrument-log-query"
              >
                <Typography className={styles.accordionHeading}>
                  Instrument Log Query
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <InstrumentLogForm instrument={instrument} />
              </AccordionDetails>
            </Accordion>
          </div>
          <Paper elevation={3} style={{ marginTop: "1rem", padding: "1rem" }}>
            <JsonDashboard
              title={`${instrument?.name || "Instrument"} Status`}
              data={instrument?.status || {}}
              lastUpdated={instrument?.last_status_update}
              refreshButton={refreshButton}
              showTitle
            />
          </Paper>
        </Grid>
      </Grid>
    </div>
  );
};

InstrumentSummary.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.number,
  }).isRequired,
};

export default withRouter(InstrumentSummary);
