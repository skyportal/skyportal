import React, { useState } from "react";

import { useDispatch, useSelector } from "react-redux";
import Chip from "@mui/material/Chip";
import makeStyles from "@mui/styles/makeStyles";
import Paper from "@mui/material/Paper";
import Grid from "@mui/material/Grid";
import Box from "@mui/material/Box";
import { Link } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import emoji from "emoji-dictionary";
import { showNotification } from "baselayer/components/Notifications";

import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";

// eslint-disable-next-line import/no-unresolved
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import { allowedClasses } from "./classification/ClassificationForm";
import Button from "./Button";

import * as summaryActions from "../ducks/summary";

const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
    fontSize: "1.2rem",
    fontWeight: "bold",
  },
  button: {
    width: "100%",
  },
  buttons: {
    display: "flex",
    flexDirection: "row",
    width: "100%",
    gap: theme.spacing(2),
  },
  source: {},
  commentListContainer: {
    height: "15rem",
    overflowY: "scroll",
    padding: "0.5rem 0",
  },
  tableGrid: {
    width: "100%",
  },
  parameterinline: {
    marginRight: "16px",
    display: "flex",
  },
}));

const SummarySearch = () => {
  const classes = useStyles();
  const summary_sources_classes = useSelector(
    (state) => state.config.summary_sourcesClasses,
  );
  const dispatch = useDispatch();
  const [queryResult, setQueryResult] = useState(null);
  const [runningQuery, setRunningQuery] = useState(false);
  const [formData, setFormData] = useState({});

  // Get unique classification names, in alphabetical order
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const latestTaxonomyList = taxonomyList?.filter((t) => t.isLatest);
  let classifications = [];
  latestTaxonomyList?.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy)?.map(
      (option) => option.class,
    );
    classifications = classifications.concat(currentClasses);
  });
  classifications = Array.from(new Set(classifications)).sort();

  const handleSubmit = () => {
    setRunningQuery(true);
    setQueryResult(null);
    dispatch(summaryActions.fetchSummaryQuery(formData)).then((response) => {
      if (response.status === "success") {
        setQueryResult(response.data);
      } else {
        dispatch(showNotification("Error querying summaries", "error"));
      }
      setRunningQuery(false);
    });
  };

  const emojiSupport = (textComment) =>
    textComment.value.replace(/:\w+:/gi, (name) =>
      emoji.getUnicode(name) ? emoji.getUnicode(name) : name,
    );

  const formSchema = {
    type: "object",
    properties: {
      q: {
        type: "string",
        title: "Query",
      },
      toggleA: {
        type: "boolean",
        title: "Show/Hide Options",
      },
    },
    dependencies: {
      toggleA: {
        oneOf: [
          {
            properties: {
              toggleA: { enum: [true] },
              k: {
                type: "integer",
                title: "(Optional) Number of sources to return",
                default: 5,
                minimum: 1,
                maximum: 25,
              },
              classificationTypes: {
                type: ["array", "null"],
                title:
                  "(Optional) Return sources only with these classifications",
                items: {
                  type: "string",
                  enum: classifications,
                },
                uniqueItems: true,
              },
              z_min: {
                type: ["number", "null"],
                title: "(Optional) Min redshift (can be null)",
              },
              z_max: {
                type: ["number", "null"],
                title: "(Optional) Max redshift (can be null)",
              },
            },
            required: [],
          },
          {
            properties: {
              toggleA: { enum: [false] },
            },
          },
        ],
      },
    },
    required: ["q"],
  };

  const uiSchema = {
    q: {
      "ui:autofocus": true,
      "ui:placeholder": "What sources are associated with NGC galaxies?",
      "ui:help": "Natural language query of the sources summaries.",
    },
    z_min: {
      "ui:placeholder": "0.0",
    },
    z_max: {},
    k: {
      "ui:widget": "updown",
    },
  };

  const validate = (fd, errors) => {
    if (fd.z_min && fd.z_max && fd.z_min > fd.z_max) {
      errors.z_min.addError("Min redshift must be less than max redshift");
      errors.z_max.addError("Min redshift must be less than max redshift");
    }

    if (fd.z_max && fd.z_max < 0) {
      errors.z_max.addError("Max redshift must be greater than 0");
    }

    if (fd.q.length < 10) {
      errors.q.addError("Query must be at least 10 characters long");
    }

    if (!fd.q.includes("?")) {
      errors.q.addError("Query must be in the form of a question.");
    }

    return errors;
  };

  const onClear = () => {
    setFormData({});
  };

  return (
    <Grid
      container
      spacing={3}
      columns={12}
      direction="column"
      alignItems="center"
      justifyContent="center"
    >
      <Grid item xs={12}>
        <div className={classes.source}>
          <Typography variant="h6" gutterBottom>
            Summary Search
          </Typography>
        </div>
      </Grid>
      <Grid item xs={8}>
        <Paper elevation={1}>
          <Form
            schema={formSchema}
            validator={validator}
            uiSchema={uiSchema}
            data-testid="searchform"
            onSubmit={handleSubmit}
            formData={formData}
            onChange={(e) => setFormData(e.formData)}
            customValidate={validate}
          >
            <div className={classes.buttons}>
              <Button
                disabled={runningQuery}
                variant="contained"
                className={classes.button}
                type="submit"
                color="primary"
              >
                Submit
              </Button>
              <Button
                secondary
                disabled={runningQuery}
                type="button"
                onClick={onClear}
              >
                Clear
              </Button>
            </div>
          </Form>
        </Paper>
      </Grid>
      <Grid item xs={12}>
        {runningQuery && (
          <div
            style={{
              display: "flex",
              width: "100%",
              height: "100%",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            <CircularProgress />
          </div>
        )}
        {!runningQuery && queryResult ? (
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Score</TableCell>
                <TableCell>Summary</TableCell>
                <TableCell>Redshift</TableCell>
                <TableCell>Classification(s)</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {queryResult.query_results?.map((source) => {
                let fw = "normal";
                let col = "grey";
                // set the font weight and color based on the score
                // using the summary_sources_classes list
                summary_sources_classes.every((tc) => {
                  if (source.score >= tc.score) {
                    fw = tc.fw;
                    col = tc.col;
                    return false;
                  }
                  return true;
                });

                return (
                  <TableRow key={`query_${source.id}`}>
                    <TableCell>
                      <Link
                        to={`/source/${source.id}`}
                        role="link"
                        key={source.id}
                      >
                        {source.id}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Box component="span" fontWeight={fw} color={col}>
                        {source.score}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <ReactMarkdown components={{ text: emojiSupport }}>
                        {source?.metadata?.summary}
                      </ReactMarkdown>
                    </TableCell>
                    <TableCell>{source?.metadata?.redshift}</TableCell>
                    <TableCell>
                      {source?.metadata?.class?.map((cl) => (
                        <Chip
                          label={`${cl}`}
                          key={`${source.id}_${cl}tb`}
                          size="small"
                          className={classes.chip}
                        />
                      ))}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        ) : null}
      </Grid>
    </Grid>
  );
};

export default SummarySearch;
