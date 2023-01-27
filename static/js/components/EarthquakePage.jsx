import React, { useEffect, useState, useRef } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import makeStyles from "@mui/styles/makeStyles";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import IconButton from "@mui/material/IconButton";
import GetAppIcon from "@mui/icons-material/GetApp";
import Grid from "@mui/material/Grid";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";

import * as earthquakeActions from "../ducks/earthquake";

import Spinner from "./Spinner";

import EarthquakePredictionForm from "./EarthquakePredictionForm";
import EarthquakePredictionLists from "./EarthquakePredictionLists";
import EarthquakeMeasurementLists from "./EarthquakeMeasurementLists";

import CommentList from "./CommentList";
import Reminders from "./Reminders";

import withRouter from "./withRouter";

dayjs.extend(utc);

const useStyles = makeStyles((theme) => ({
  header: {},
  eventTags: {
    marginLeft: "1rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
  },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
  earthquakeContainer: {
    display: "flex",
    overflow: "hidden",
    flexDirection: "column",
  },
  comments: {
    width: "100%",
  },
  columnItem: {
    marginBottom: theme.spacing(2),
  },
  noSources: {
    padding: theme.spacing(2),
    display: "flex",
    flexDirection: "row",
  },
  sourceList: {
    padding: "0",
  },
}));

const DownloadXMLButton = ({ notice }) => {
  const blob = new Blob([notice.content], { type: "text/plain" });

  return (
    <div>
      <Chip size="small" label={notice.created_at} key={notice.created_at} />
      <IconButton
        href={URL.createObjectURL(blob)}
        download={notice.event_id}
        size="large"
      >
        <GetAppIcon />
      </IconButton>
    </div>
  );
};

DownloadXMLButton.propTypes = {
  notice: PropTypes.shape({
    content: PropTypes.string,
    event_id: PropTypes.string,
    created_at: PropTypes.string,
  }).isRequired,
};

const sidebarWidth = 190;

const EarthquakePage = ({ route }) => {
  const ref = useRef(null);
  const theme = useTheme();
  const initialWidth =
    window.innerWidth - sidebarWidth - 2 * parseInt(theme.spacing(2), 10);
  const [width, setWidth] = useState(initialWidth);

  const earthquake = useSelector((state) => state.earthquake);
  const dispatch = useDispatch();
  const styles = useStyles();

  useEffect(() => {
    const handleResize = () => {
      if (ref.current !== null) {
        setWidth(ref.current.offsetWidth);
      }
    };

    window.addEventListener("resize", handleResize);
  }, [ref]);

  useEffect(() => {
    const fetchEarthquake = async (event_id) => {
      await dispatch(earthquakeActions.fetchEarthquake(event_id));
    };
    fetchEarthquake(route.event_id);
  }, [route, dispatch]);

  if (!earthquake) {
    return <Spinner />;
  }

  if (!earthquake?.event_id) {
    return <Spinner />;
  }

  let xs = 7;
  if (width < 600) {
    xs = 14;
  }

  return (
    <div ref={ref}>
      <Grid container spacing={2} className={styles.source}>
        <Grid item xs={xs}>
          <div className={styles.columnItem}>
            <Accordion defaultExpanded>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="earthquake-content"
                id="info-header"
              >
                <Typography className={styles.accordionHeading}>
                  Event Information
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <div className={styles.earthquakeContainer}>
                  <Link to={`/earthquakes/${earthquake.event_id}`}>
                    <Button color="primary">{earthquake.event_id}</Button>
                  </Link>
                </div>
                <div className={styles.eventTags}>{earthquake.lat}</div>
              </AccordionDetails>
            </Accordion>
          </div>
          <div className={styles.columnItem}>
            <Accordion>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="earthquake-content"
                id="prediction-header"
              >
                <Typography className={styles.accordionHeading}>
                  Predictions
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <div className={styles.earthquakeContainer}>
                  <EarthquakePredictionForm
                    earthquake={earthquake}
                    action="createNew"
                  />
                  <EarthquakePredictionLists earthquake={earthquake} />
                </div>
              </AccordionDetails>
            </Accordion>
          </div>
          <div className={styles.columnItem}>
            <Accordion>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                aria-controls="earthquake-content"
                id="measurement-header"
              >
                <Typography className={styles.accordionHeading}>
                  Measurements
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <div className={styles.earthquakeContainer}>
                  <EarthquakeMeasurementLists earthquake={earthquake} />
                </div>
              </AccordionDetails>
            </Accordion>
          </div>
        </Grid>

        {width > 600 && (
          <Grid item xs={5}>
            <div className={styles.columnItem}>
              <Accordion
                defaultExpanded
                className={styles.comments}
                data-testid="comments-accordion"
              >
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  aria-controls="comments-content"
                  id="comments-header"
                >
                  <Typography className={styles.accordionHeading}>
                    Comments
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <CommentList
                    associatedResourceType="earthquake"
                    earthquakeID={earthquake.id.toString()}
                  />
                </AccordionDetails>
              </Accordion>
            </div>
            <div className={styles.columnItem}>
              <Accordion defaultExpanded>
                <AccordionDetails>
                  <div className={styles.earthquakeContainer}>
                    <Reminders
                      resourceId={earthquake.id.toString()}
                      resourceType="earthquake"
                    />
                  </div>
                </AccordionDetails>
              </Accordion>
            </div>
            <div className={styles.columnItem}>
              <Accordion defaultExpanded>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  aria-controls="earthquake-content"
                  id="gcnnotices-header"
                >
                  <Typography className={styles.accordionHeading}>
                    Notices
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <div className={styles.earthquakeContainer}>
                    {earthquake.notices?.map((notice) => (
                      <li key={notice.date}>
                        <DownloadXMLButton notice={notice} />
                      </li>
                    ))}
                  </div>
                </AccordionDetails>
              </Accordion>
            </div>
          </Grid>
        )}
      </Grid>
    </div>
  );
};

EarthquakePage.propTypes = {
  route: PropTypes.shape({
    event_id: PropTypes.string,
  }).isRequired,
};

export default withRouter(EarthquakePage);
