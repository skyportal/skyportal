import { Link } from "react-router-dom";

import dayjs from "dayjs";
import calendar from "dayjs/plugin/calendar";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { makeStyles } from "tss-react/mui";
import DownloadIcon from "@mui/icons-material/Download";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Button from "../Button";
import withRouter from "../withRouter";
import AnalysisCornerPlot from "../analysis/AnalysisCornerPlot";

import {
  useGetAnalysisQuery,
  useGetAnalysisResultsQuery,
} from "../../ducks/source";

dayjs.extend(calendar);

const useStyles = makeStyles()((theme) => ({
  root: {
    margin: "0.5rem auto",
    flexGrow: 1,
  },
  div: {
    padding: "0.25rem 0.5rem 0.25rem 0",
    fontSize: "0.875rem",
  },
  cardTitle: {
    padding: `${theme.spacing(0.75)} ${theme.spacing(1)} ${theme.spacing(
      0.75,
    )} ${theme.spacing(1)}`,
  },
  title: {
    fontSize: "0.875rem",
  },
  chip: {
    margin: "0.1em",
  },
  pos: {
    marginBottom: 0,
  },
  mediaDiv: {
    position: "relative",
    height: "95%",
    width: "95%",
  },
  corner: {
    maxHeight: "70vh",
    maxWidth: "100%",
  },
  media: {
    maxHeight: "70vh",
    maxWidth: "100%",
  },
  downTriangle: {
    width: 0,
    height: 0,
    backgroundColor: "transparent",
    borderStyle: "solid",
    borderTopWidth: "15px",
    borderRightWidth: "15px",
    borderBottomWidth: "0px",
    borderLeftWidth: "15px",
    borderTopColor: "#359d73",
    borderRightColor: "transparent",
    borderBottomColor: "transparent",
    borderLeftColor: "transparent",
  },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
}));

interface SourceAnalysisPageProps {
  route: {
    obj_id: string;
    analysis_id: number;
  };
}

const SourceAnalysisPage = ({ route }: SourceAnalysisPageProps) => {
  const { classes } = useStyles();

  const { data: analysisData } = useGetAnalysisQuery({
    analysis_id: route.analysis_id,
    analysis_resource_type: "obj",
    params: { objID: route.obj_id },
  });
  const { data: analysisResults } = useGetAnalysisResultsQuery({
    analysis_id: route.analysis_id,
    analysis_resource_type: "obj",
  });
  const analysis = analysisData as any;

  let chip_color: any = "warning";
  if (analysis?.status === "completed") {
    chip_color = "success";
  }
  if (analysis?.status === "failure") {
    chip_color = "error";
  }
  const last_active_str = `${dayjs().to(
    dayjs.utc(`${analysis?.["last_activity"]}Z`),
  )}`;
  const duration_str = `${analysis?.["duration"]?.toFixed(2)} sec`;
  const info_str = `Last activity ${last_active_str} (duration ${duration_str})`;
  return (
    <>
      <Typography variant="h5" gutterBottom>
        Analysis Page for{" "}
        <Link to={`/source/${route.obj_id}`} role="link">
          {route.obj_id}
        </Link>{" "}
        (#{route.analysis_id})
      </Typography>
      {analysis && analysis?.["last_activity"] ? (
        <>
          <Chip
            label={analysis?.status}
            key={`chip${analysis?.id}_${analysis?.status}`}
            size="small"
            className={classes.chip}
            color={chip_color}
          />
          <Chip
            label={info_str}
            key={`chip${analysis?.id}_${analysis?.status}_info`}
            size="small"
            className={classes.chip}
          />
          <Tooltip
            title={`${analysis?.analysis_service_id}: ${analysis?.analysis_service_description}`}
          >
            <Chip
              label={`Service: ${analysis.analysis_service_name}`}
              key={`chip${analysis.id}_${analysis.analysis_service_id}`}
              size="small"
              className={classes.chip}
            />
          </Tooltip>
          {analysis?.status_message && (
            <div className={classes.div}>
              <b>Message</b>: {analysis?.status_message}
            </div>
          )}
          {analysis?.analysis_parameters && (
            <div className={classes.div}>
              <b>Analysis Parameters</b>:
              {Object.keys(analysis?.analysis_parameters ?? {}).map((key) => (
                <Chip
                  label={`${key}: ${(analysis?.["analysis_parameters"] ?? {})[key]}`}
                  key={`chip_ap_${key}`}
                  size="small"
                  className={classes.chip}
                />
              ))}
            </div>
          )}
          {analysis?.["input_filters"] &&
            Object.keys(analysis?.["input_filters"] || {}).every(
              (input_type) =>
                Object.keys(analysis?.["input_filters"][input_type]).length > 0,
            ) && (
              <div className={classes.div}>
                <b>Input Data Filters</b>:
                {Object.keys(analysis?.["input_filters"]).map(
                  (input_type: string) =>
                    Object.keys(analysis?.["input_filters"][input_type]).map(
                      (key) => (
                        <Chip
                          label={`${input_type}.${key}: ${JSON.stringify(
                            analysis?.["input_filters"][input_type][key],
                          )}`}
                          key={`chip_if_${key}`}
                          size="small"
                          className={classes.chip}
                        />
                      ),
                    ),
                )}
              </div>
            )}
          {analysis?.["show_parameters"] &&
            analysisResults &&
            analysis?.status === "completed" && (
              <Accordion>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  aria-controls="analysis-content"
                  id="results-header"
                >
                  <Typography className={classes.accordionHeading}>
                    Analysis Results
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Card className={classes.root} variant="outlined">
                    <CardContent>
                      {typeof analysisResults === "object" &&
                      analysisResults !== null &&
                      !Array.isArray(analysisResults) ? (
                        Object.keys(analysisResults).map((k) => (
                          <span
                            className={classes.div}
                            key={`display_results_${k}`}
                          >
                            <b>{k}</b>: {JSON.stringify(analysisResults[k])}
                            <br />
                          </span>
                        ))
                      ) : (
                        // Not a plain object (e.g. an undecodable string) — show
                        // it verbatim rather than spreading it into characters.
                        <span className={classes.div}>
                          {JSON.stringify(analysisResults)}
                        </span>
                      )}
                    </CardContent>
                  </Card>
                  <Button
                    primary
                    href={`/api/obj/analysis/${analysis.id}/results`}
                    size="small"
                    type="submit"
                    target="_blank"
                    data-testid={`analysis_results_${analysis.id}`}
                  >
                    <DownloadIcon />
                  </Button>
                </AccordionDetails>
              </Accordion>
            )}
          {analysis?.["show_corner"] && analysis?.status === "completed" && (
            <Accordion>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="analysis-content"
                id="results-header"
              >
                <Typography className={classes.accordionHeading}>
                  Posterior Corner Plot
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Card className={classes.root} variant="outlined">
                  <CardContent>
                    <div className={classes.mediaDiv}>
                      <AnalysisCornerPlot
                        objId={route.obj_id}
                        analysisId={analysis.id}
                      />
                    </div>
                  </CardContent>
                </Card>
              </AccordionDetails>
            </Accordion>
          )}
          {analysis?.["show_plots"] &&
            analysis?.status === "completed" &&
            (analysis?.["num_plots"] ?? 0) > 0 && (
              <Accordion>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  aria-controls="analysis-content"
                  id="results-header"
                >
                  <Typography className={classes.accordionHeading}>
                    Plots
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Card className={classes.root} variant="outlined">
                    <CardContent>
                      {[...Array(analysis?.num_plots)].map((x, i) => (
                        <div
                          key={`plot_key_${analysis.id}_${x}`}
                          className={classes.mediaDiv}
                        >
                          <img
                            src={`/api/obj/analysis/${analysis.id}/plots/${i}`}
                            alt={`analysis plot ${i}`}
                            className={classes.media}
                            title={`analysis plot ${i}`}
                            loading="lazy"
                          />
                          <Button
                            primary
                            href={`/api/obj/analysis/${analysis.id}/plots/${i}`}
                            size="small"
                            type="submit"
                            target="_blank"
                            data-testid={`plot_${analysis.id}_${i}`}
                          >
                            <DownloadIcon />
                          </Button>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                </AccordionDetails>
              </Accordion>
            )}
        </>
      ) : (
        "Analysis not found"
      )}
    </>
  );
};

export default withRouter(SourceAnalysisPage);
