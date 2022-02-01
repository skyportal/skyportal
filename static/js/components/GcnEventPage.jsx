import React, { useRef, useEffect, useState, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import Accordion from "@material-ui/core/Accordion";
import AccordionSummary from "@material-ui/core/AccordionSummary";
import AccordionDetails from "@material-ui/core/AccordionDetails";
import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";
import { makeStyles } from "@material-ui/core/styles";
import CircularProgress from "@material-ui/core/CircularProgress";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";
import IconButton from "@material-ui/core/IconButton";
import GetAppIcon from "@material-ui/icons/GetApp";
import Typography from "@material-ui/core/Typography";

import * as d3 from "d3";
// eslint-disable-next-line
import d3GeoZoom from "d3-geo-zoom";
// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import * as gcnEventActions from "../ducks/gcnEvent";
import * as localizationActions from "../ducks/localization";
import * as sourcesActions from "../ducks/sources";

import SourceTable from "./SourceTable";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const SkymapPlot = React.lazy(() =>
  import(/* webpackChunkName: "SkymapPlot" */ "./SkymapPlot")
);

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
  BNS: {
    background: "#468847!important",
  },
  NSBH: {
    background: "#b94a48!important",
  },
  BBH: {
    background: "#333333!important",
  },
  GRB: {
    background: "#f89406!important",
  },
  AMON: {
    background: "#3a87ad!important",
  },
  Terrestrial: {
    background: "#999999!important",
  },
  accordionHeading: {
    fontSize: "1.25rem",
    fontWeight: theme.typography.fontWeightRegular,
  },
  gcnEventContainer: {
    display: "flex",
    overflow: "hidden",
    flexDirection: "column",
  },
  columnItem: {
    marginBottom: theme.spacing(2),
  },
}));

const DownloadXMLButton = ({ gcn_notice }) => {
  const blob = new Blob([gcn_notice.content], { type: "text/plain" });

  return (
    <div>
      <Chip size="small" label={gcn_notice.ivorn} key={gcn_notice.ivorn} />
      <IconButton href={URL.createObjectURL(blob)} download={gcn_notice.ivorn}>
        <GetAppIcon />
      </IconButton>
    </div>
  );
};

const useD3 = (renderChartFn) => {
  const ref = useRef();

  useEffect(() => {
    renderChartFn(d3.select(ref.current));
    return () => {};
  }, [renderChartFn, ref]);
  return ref;
};

const Globe = ({ data }) => {
  const projRef = useRef(d3.geoOrthographic());

  function renderMap(svg) {
    const path = d3.geoPath().projection(projRef.current);

    function render() {
      svg.selectAll("path").attr("d", path);
    }

    d3GeoZoom().projection(projRef.current).onMove(render)(svg.node());

    if (data) {
      svg
        .selectAll("path")
        .data(data.features)
        .enter()
        .append("path")
        .attr("class", (d) => d.properties.name)
        .attr("d", path)
        .style("fill", "none")
        .style("stroke", "black")
        .style("stroke-width", "0.5px");
    }

    svg
      .selectAll("path")
      .data([{ type: "Feature", geometry: d3.geoGraticule10() }])
      .enter()
      .append("path")
      .attr("class", "graticule")
      .attr("d", path)
      .style("fill", "none")
      .style("stroke", "lightgray")
      .style("stroke-width", "0.5px");
  }

  const svgRef = useD3(renderMap);

  useEffect(() => {
    const height = svgRef.current.clientHeight;
    const width = svgRef.current.clientWidth;
    projRef.current.translate([width / 2, height / 2]);
  }, [data, svgRef]);

  return <svg id="globe" ref={svgRef} />;
};

const Localization = ({ loc }) => {
  const localization = useSelector((state) => state.localization);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(
      localizationActions.fetchLocalization(loc.dateobs, loc.localization_name)
    );
  }, [loc, dispatch]);

  if (!localization) {
    return <CircularProgress />;
  }

  return (
    <>
      <Chip
        size="small"
        label={localization.localization_name}
        key={localization.localization_name}
      />
      <Globe data={localization.contour} />
    </>
  );
};

const GcnEventSourcesPage = ({ route, sources }) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const [sourcesRowsPerPage, setSourcesRowsPerPage] = useState(100);

  const handleSourcesTableSorting = (sortData, filterData) => {
    dispatch(
      sourcesActions.fetchGcnEventSources(route.dateobs, {
        ...filterData,
        pageNumber: 1,
        numPerPage: sourcesRowsPerPage,
        sortBy: sortData.name,
        sortOrder: sortData.direction,
      })
    );
  };

  const handleSourcesTablePagination = (
    pageNumber,
    numPerPage,
    sortData,
    filterData
  ) => {
    setSourcesRowsPerPage(numPerPage);
    const data = {
      ...filterData,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      data.sortBy = sortData.name;
      data.sortOrder = sortData.direction;
    }
    dispatch(sourcesActions.fetchGcnEventSources(route.dateobs, data));
  };

  // eslint-disable-next-line
  if (sources?.sources.length === 0) {
    return (
      <div className={classes.source}>
        <Typography variant="h4" gutterBottom align="center">
          Event sources
        </Typography>
        <br />
        <Typography variant="h5" align="center">
          No sources within localization.
        </Typography>
      </div>
    );
  }

  return (
    <div className={classes.source}>
      <Typography variant="h4" gutterBottom align="center">
        Event sources
      </Typography>
      <SourceTable
        sources={sources.sources}
        title="Event Sources"
        paginateCallback={handleSourcesTablePagination}
        pageNumber={sources.pageNumber}
        totalMatches={sources.totalMatches}
        numPerPage={sources.numPerPage}
        sortingCallback={handleSourcesTableSorting}
        favoritesRemoveButton
      />
    </div>
  );
};

const GcnEventPage = ({ route }) => {
  const gcnEvent = useSelector((state) => state.gcnEvent);
  const dispatch = useDispatch();
  const styles = useStyles();
  const gcnEventSources = useSelector(
    (state) => state?.sources?.gcnEventSources
  );

  useEffect(() => {
    dispatch(gcnEventActions.fetchGcnEvent(route.dateobs));
  }, [route, dispatch]);

  useEffect(() => {
    dispatch(sourcesActions.fetchGcnEventSources(route.dateobs));
  }, [route, dispatch]);

  if (!gcnEvent || !gcnEventSources) {
    return <CircularProgress />;
  }

  return (
    <div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="info-header"
          >
            <Typography className={styles.accordionHeading}>
              Event Information
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.gcnEventContainer}>
              <Link to={`/gcn_events/${gcnEvent.dateobs}`}>
                <Button color="primary">
                  {dayjs(gcnEvent.dateobs).format("YYMMDD HH:mm:ss")}
                </Button>
              </Link>
              ({dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))})
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="lightcurve-header"
          >
            <Typography className={styles.accordionHeading}>
              Light curve
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.gcnEventContainer}>
              {gcnEvent.lightcurve && (
                <div>
                  {" "}
                  <img src={gcnEvent.lightcurve} alt="loading..." />{" "}
                </div>
              )}
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="eventtags-header"
          >
            <Typography className={styles.accordionHeading}>
              Event Tags
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.eventTags}>
              {gcnEvent.tags?.map((tag) => (
                <Chip
                  className={styles[tag]}
                  size="small"
                  label={tag}
                  key={tag}
                />
              ))}
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="skymap-header"
          >
            <Typography className={styles.accordionHeading}>Skymaps</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Suspense fallback={<div>Loading skymap plot...</div>}>
              <SkymapPlot plotData={gcnEvent.localizations[0].contour} />
            </Suspense>
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="gcnnotices-header"
          >
            <Typography className={styles.accordionHeading}>
              GCN Notices
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.gcnEventContainer}>
              {gcnEvent.gcn_notices?.map((gcn_notice) => (
                <li key={gcn_notice.ivorn}>
                  <DownloadXMLButton gcn_notice={gcn_notice} />
                </li>
              ))}
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
      <div className={styles.columnItem}>
        <Accordion defaultExpanded>
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="gcnEvent-content"
            id="sources-header"
          >
            <Typography className={styles.accordionHeading}>
              Event Sources
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <div className={styles.gcnEventContainer}>
              <GcnEventSourcesPage route={route} sources={gcnEventSources} />
            </div>
          </AccordionDetails>
        </Accordion>
      </div>
      <div>
        <GcnEventSourcesPage route={route} sources={gcnEventSources} />
      </div>
    </div>
  );
};

Localization.propTypes = {
  loc: PropTypes.shape({
    dateobs: PropTypes.string,
    localization_name: PropTypes.string,
  }).isRequired,
};

Localization.propTypes = {
  loc: PropTypes.shape({
    dateobs: PropTypes.string,
    localization_name: PropTypes.string,
  }).isRequired,
};

GcnEventPage.propTypes = {
  route: PropTypes.shape({
    dateobs: PropTypes.string,
  }).isRequired,
};

Globe.propTypes = {
  data: PropTypes.shape({
    length: PropTypes.number,
    features: GeoPropTypes.FeatureCollection,
  }).isRequired,
};

GcnEventSourcesPage.propTypes = {
  route: PropTypes.shape({
    dateobs: PropTypes.string,
  }).isRequired,
  sources: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      ra: PropTypes.number,
      dec: PropTypes.number,
      origin: PropTypes.string,
      alias: PropTypes.arrayOf(PropTypes.string),
      redshift: PropTypes.number,
      classifications: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          classification: PropTypes.string,
          created_at: PropTypes.string,
          groups: PropTypes.arrayOf(
            PropTypes.shape({
              id: PropTypes.number,
              name: PropTypes.string,
            })
          ),
        })
      ),
      recent_comments: PropTypes.arrayOf(PropTypes.shape({})),
      altdata: PropTypes.shape({
        tns: PropTypes.shape({
          name: PropTypes.string,
        }),
      }),
      spectrum_exists: PropTypes.bool,
      last_detected_at: PropTypes.string,
      last_detected_mag: PropTypes.number,
      peak_detected_at: PropTypes.string,
      peak_detected_mag: PropTypes.number,
      groups: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          name: PropTypes.string,
        })
      ),
    })
  ).isRequired,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  data: PropTypes.shape({
    length: PropTypes.number,
    features: GeoPropTypes.FeatureCollection,
  }).isRequired,
};

GcnEventSourcesPage.defaultProps = {
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
};

DownloadXMLButton.propTypes = {
  gcn_notice: PropTypes.shape({
    content: PropTypes.string,
    ivorn: PropTypes.string,
  }).isRequired,
};

export default GcnEventPage;
