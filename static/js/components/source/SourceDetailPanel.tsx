import React, { Suspense, useState } from "react";

import CircularProgress from "@mui/material/CircularProgress";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import Grid from "@mui/material/Grid";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import { makeStyles } from "tss-react/mui";
import { isMobileOnly } from "react-device-detect";

import { useAppSelector } from "../../types/hooks";
import { photometryApi } from "../../ducks/photometry";
import ThumbnailList from "../thumbnail/ThumbnailList";
import VegaPhotometry from "../plot/VegaPhotometry";
import ShowSummaries from "../summary/ShowSummaries";
import ShowSummaryHistory from "../summary/ShowSummaryHistory";
import StartBotSummary from "../StartBotSummary";
import MultipleClassificationsForm from "../classification/MultipleClassificationsForm";
import UpdateSourceSummary from "./UpdateSourceSummary";
import { getAnnotationValueString } from "../candidate/ScanningPageCandidateAnnotations";

const VegaSpectrum = React.lazy(() => import("../plot/VegaSpectrum"));
const VegaHR = React.lazy(() => import("../plot/VegaHR"));

const useStyles = makeStyles()((theme) => ({
  annotations: {
    overflowWrap: "break-word",
  },
  annotationList: {
    width: "100%",
    background: theme.palette.background.paper,
    padding: theme.spacing(1),
    maxHeight: "15rem",
    overflowY: "scroll",
  },
  nested: {
    paddingLeft: theme.spacing(4),
    paddingTop: 0,
    paddingBottom: 0,
  },
}));

// The pull-out detail panel of the source table. Subscribes to photometry
// itself, so incoming photometry (e.g. at Argus alert rates) updates only the
// expanded panels and never forces the parent grid's columns to rebuild.
const SourceDetailPanel = React.memo(
  ({
    source,
    groupID,
    taxonomyList = [],
  }: {
    source: any;
    groupID?: number | undefined;
    taxonomyList?: any[] | undefined;
  }) => {
    const { classes } = useStyles();
    // Read any already-cached full photometry for this source without triggering
    // a fetch (the folded plot only renders when photometry is already loaded,
    // e.g. on the Source page).
    const photometry = useAppSelector(
      (state) =>
        photometryApi.endpoints.fetchSourcePhotometry.select({
          id: source.id,
        })(state as any).data,
    );
    const [openedOrigins, setOpenedOrigins] = useState<Record<string, any>>({});

    const annotations = source.annotations || [];

    const handleClick = (origin: any) => {
      setOpenedOrigins((prev) => ({ ...prev, [origin]: !prev[origin] }));
    };

    const plotWidth = isMobileOnly ? 200 : 400;
    const specPlotHeight = isMobileOnly ? 150 : 200;
    const legendOrient = isMobileOnly ? "bottom" : "right";

    return (
      <div
        data-testid={`groupSourceExpand_${source.id}`}
        style={{ width: "100%" }}
      >
        <Grid
          container
          direction="row"
          spacing={3}
          sx={{
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <ThumbnailList
            thumbnails={source.thumbnails}
            ra={source.ra}
            dec={source.dec}
            useGrid={false}
          />
          <Grid>
            <VegaPhotometry sourceId={source.id} />
          </Grid>
          <Grid>
            {(photometry?.length ?? 0) > 0 && (
              <VegaPhotometry
                sourceId={source.id}
                annotations={annotations}
                folded
              />
            )}
          </Grid>
          <Grid>
            {source.color_magnitude?.length > 0 && (
              <div data-testid={`hr_diagram_${source.id}`}>
                <Suspense fallback={<CircularProgress color="secondary" />}>
                  <VegaHR
                    data={source.color_magnitude}
                    width={200}
                    height={200}
                  />
                </Suspense>
              </div>
            )}
          </Grid>
          <Grid>
            <Suspense fallback={<CircularProgress color="secondary" />}>
              <VegaSpectrum
                sourceId={source.id}
                width={plotWidth}
                height={specPlotHeight}
                legendOrient={legendOrient}
                normalization="median"
              />
            </Suspense>
          </Grid>
          <Grid>
            <div className={classes.annotations}>
              {annotations?.length > 0 && (
                <>
                  <Typography variant="subtitle2">Annotations:</Typography>
                  <List
                    component="nav"
                    aria-labelledby="nested-list-subheader"
                    className={classes.annotationList}
                    dense
                  >
                    {annotations.map((annotation: any) => (
                      <div key={`annotation_${annotation.origin}`}>
                        <Divider />
                        <ListItem
                          onClick={() => handleClick(annotation.origin)}
                        >
                          <ListItemText
                            primary={`${annotation.origin}`}
                            slotProps={{ primary: { variant: "button" } }}
                          />
                          {openedOrigins[annotation.origin] ? (
                            <ExpandLess />
                          ) : (
                            <ExpandMore />
                          )}
                        </ListItem>
                        <Collapse
                          in={openedOrigins[annotation.origin]}
                          timeout="auto"
                          unmountOnExit
                        >
                          <List component="div" dense disablePadding>
                            {Object.entries(annotation.data).map(
                              ([key, value]) => (
                                <ListItem
                                  key={`key_${annotation.origin}_${key}`}
                                  className={classes.nested}
                                >
                                  <ListItemText
                                    secondary={`${key}: ${getAnnotationValueString(
                                      value,
                                    )}`}
                                  />
                                </ListItem>
                              ),
                            )}
                          </List>
                        </Collapse>
                        <Divider />
                      </div>
                    ))}
                  </List>
                </>
              )}
            </div>
          </Grid>
          <Grid size={12}>
            <MultipleClassificationsForm
              objId={source.id}
              taxonomyList={taxonomyList}
              groupId={groupID}
              currentClassifications={source.classifications}
            />
          </Grid>
          <Grid size={12}>
            <ShowSummaries summaries={source.summary_history} />
            {source.summary_history?.length < 1 ||
            !source.summary_history ||
            source.summary_history[0].summary === null ? (
              <div>
                <b>Summarize: &nbsp;</b>
              </div>
            ) : null}
            <UpdateSourceSummary source={source} />
            {source.classifications?.length > 0 ? (
              <StartBotSummary obj_id={source.id} />
            ) : null}
            {source.summary_history?.length > 0 ? (
              <ShowSummaryHistory
                summaries={source.summary_history}
                obj_id={source.id}
              />
            ) : null}
          </Grid>
        </Grid>
      </div>
    );
  },
);
SourceDetailPanel.displayName = "SourceDetailPanel";

export default SourceDetailPanel;
