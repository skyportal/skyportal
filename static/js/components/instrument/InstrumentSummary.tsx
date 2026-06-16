import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import RefreshIcon from "@mui/icons-material/Refresh";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";
import { useEffect, useState } from "react";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import { showNotification } from "baselayer/components/Notifications";

import Paper from "@mui/material/Paper";
import IconButton from "@mui/material/IconButton";
import JsonDashboard from "react-json-dashboard";
import withRouter from "../withRouter";
import { useAppDispatch } from "../../types/hooks";
import {
  useGetInstrumentQuery,
  useLazyGetInstrumentLogsQuery,
  useUpdateInstrumentStatusMutation,
} from "../../ducks/instrument";
import InstrumentLogForm from "./InstrumentLogForm";
import InstrumentLogsPlot from "./InstrumentLogsPlot";

dayjs.extend(utc);

const useStyles = makeStyles()((theme) => ({
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

interface InstrumentSummaryProps {
  route: {
    id: number;
  };
}

const InstrumentSummary = ({ route }: InstrumentSummaryProps) => {
  const dispatch = useAppDispatch();
  const { classes: styles } = useStyles() as any;
  const { data: instrument } = useGetInstrumentQuery(route.id);
  const [fetchInstrumentLogs] = useLazyGetInstrumentLogsQuery();
  const [updateInstrumentStatus] = useUpdateInstrumentStatusMutation();

  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<any[] | undefined>(undefined);

  const defaultStartDate = dayjs
    .utc()
    .subtract(2, "day")
    .format("YYYY-MM-DD HH:mm:ss");
  const defaultEndDate = dayjs.utc().format("YYYY-MM-DD HH:mm:ss");

  // Load the instrument logs on mount.
  useEffect(() => {
    setLoading(true);
    fetchInstrumentLogs({
      id: route.id,
      params: {
        startDate: defaultStartDate,
        endDate: defaultEndDate,
      },
    })
      .unwrap()
      .then((response: any) => {
        setLogs(response);
      })
      .catch(() => {
        dispatch(showNotification("Error fetching instrument logs", "error"));
      })
      .finally(() => {
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route.id, dispatch]);

  if (
    !(
      instrument != null &&
      "id" in instrument &&
      instrument["id"] === parseInt(route.id as any, 10)
    )
  ) {
    // Don't need to do this for instruments -- we can just let the page be blank for a short time
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const handleSubmit = async ({ formData }: { formData: any }) => {
    setLoading(true);
    fetchInstrumentLogs({ id: route.id, params: formData })
      .unwrap()
      .then((response: any) => {
        setLogs(response);
      })
      .catch(() => {
        dispatch(showNotification("Error fetching instrument logs", "error"));
      })
      .finally(() => {
        setLoading(false);
      });
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
      onClick={async () => {
        try {
          await updateInstrumentStatus(route.id).unwrap();
          dispatch(showNotification("Instrument status updated"));
        } catch {
          dispatch(
            showNotification("Error updating instrument status", "error"),
          );
        }
      }}
    >
      <RefreshIcon />
    </IconButton>
  );

  return (
    <div>
      <Grid container spacing={2} className={styles.source}>
        <Grid size={12}>
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
                  {!loading && !(instrument as any)["log_exists"] && (
                    <div> No logs exist </div>
                  )}
                  {!loading &&
                    (instrument as any)["log_exists"] &&
                    logs?.length === 0 && (
                      <div> No logs exist in the specified time range </div>
                    )}
                  {!loading &&
                    (instrument as any)["log_exists"] &&
                    (logs?.length ?? 0) > 0 && (
                      <InstrumentLogsPlot instrument_logs={logs || []} />
                    )}
                </div>
                <div>
                  <Form
                    schema={InstrumentSummaryFormSchema as any}
                    validator={validator}
                    onSubmit={handleSubmit as any}
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
                <InstrumentLogForm
                  instrument={instrument as { id: number; [key: string]: any }}
                />
              </AccordionDetails>
            </Accordion>
          </div>
          <Paper elevation={3} style={{ marginTop: "1rem", padding: "1rem" }}>
            <JsonDashboard
              title={`${instrument?.["name"] || "Instrument"} Status`}
              data={instrument?.["status"] || {}}
              lastUpdated={instrument?.["last_status_update"]}
              refreshButton={refreshButton}
            />
          </Paper>
        </Grid>
      </Grid>
    </div>
  );
};

export default withRouter(InstrumentSummary);
