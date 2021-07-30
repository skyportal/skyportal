import React, { useRef, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";
import { Link } from "react-router-dom";

import Button from "@material-ui/core/Button";
import Chip from "@material-ui/core/Chip";
import { makeStyles } from "@material-ui/core/styles";
import CircularProgress from "@material-ui/core/CircularProgress";
import IconButton from "@material-ui/core/IconButton";
import GetAppIcon from "@material-ui/icons/GetApp";
import Typography from "@material-ui/core/Typography";

import * as d3 from "d3";
// eslint-disable-next-line
import d3GeoZoom from "d3-geo-zoom";
// eslint-disable-next-line
import GeoPropTypes from "geojson-prop-types";
import { tip as d3tip } from "d3-v6-tip";

import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";

import SourceTable from "./SourceTable";
import * as gcnEventActions from "../ducks/gcnEvent";
import * as localizationActions from "../ducks/localization";
import * as sourcesActions from "../ducks/sources";

dayjs.extend(relativeTime);
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
}));

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
  if (sources.sources.length === 0) {
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

      {!!sources.sources && (
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
      )}
    </div>
  );
};

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

const Globe = ({ data, sources }) => {
  const projRef = useRef(d3.geoOrthographic());

  function renderMap(svg) {
    const path = d3.geoPath().projection(projRef.current).pointRadius(5);
    const tip = d3tip()
      .attr("class", "d3-tip")
      .offset([-10, 0])
      .style("background-color", "white")
      .style("color", "#fff")
      .style("text-align", "center")
      .style("padding", "5px")
      .style("border-radius", "6px")
      .html((event, d) => d.properties.name);
    svg.call(tip);

    function render() {
      svg.selectAll("path").attr("d", path);
    }

    d3GeoZoom().projection(projRef.current).onMove(render)(svg.node());

    if (sources) {
      svg
        .selectAll("path")
        .data(sources.features)
        .enter()
        .append("path")
        .attr("class", (d) => d.properties.name)
        .attr("d", path)
        .attr("fill", "#b8b8b8")
        .style("stroke", "black")
        .style("opacity", 0.3)
        .on("mouseover", () => d3.select(this).style("fill", "#111"))
        .on("mouseout", () => d3.select(this).style("fill", "#b8b8b8"))
        .on("mouseenter.tip", tip.show)
        .on("mouseleave.tip", tip.hide);
    }

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

const Localization = ({ loc, sources }) => {
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
      <Globe data={localization.contour} sources={sources} />
    </>
  );
};

const GcnEventPage = ({ route }) => {
  const mapRef = useRef();
  const dispatch = useDispatch();
  const styles = useStyles();

  const gcnEvent = useSelector((state) => state.gcnEvent);
  const gcnEventSources = useSelector((state) => state.sources.gcnEventSources);

  useEffect(() => {
    dispatch(gcnEventActions.fetchGcnEvent(route.dateobs));
  }, [route, dispatch]);

  useEffect(() => {
    dispatch(sourcesActions.fetchGcnEventSources(route.dateobs, {}));
  }, [route, dispatch]);

  if (!gcnEvent) {
    return <CircularProgress />;
  }

  if (!gcnEventSources) {
    return <CircularProgress />;
  }


  return (
    <div>
      <h1 style={{ display: "inline-block" }}>Event Information</h1>
      <div>
        &nbsp; -&nbsp;
        <Link to={`/gcn_events/${gcnEvent.dateobs}`}>
          <Button color="primary">
            {dayjs(gcnEvent.dateobs).format("YYMMDD HH:mm:ss")}
          </Button>
        </Link>
        ({dayjs().to(dayjs.utc(`${gcnEvent.dateobs}Z`))})
      </div>
      {gcnEvent.lightcurve && (
        <div>
          {" "}
          <h3 style={{ display: "inline-block" }}>Light Curve</h3> &nbsp;
          -&nbsp; <img src={gcnEvent.lightcurve} alt="loading..." />{" "}
        </div>
      )}
      <h3 style={{ display: "inline-block" }}>Tags</h3>
      <div>
        &nbsp; -&nbsp;
        <div className={styles.eventTags}>
          {gcnEvent.tags?.map((tag) => (
            <Chip className={styles[tag]} size="small" label={tag} key={tag} />
          ))}
        </div>
      </div>
      <h3>Skymaps</h3>
      <div>
        &nbsp; -&nbsp;
        {gcnEvent.localizations?.map((localization) => (
          <li key={localization.localization_name}>
            <div id="map" ref={mapRef}>
              <Localization
                loc={localization}
                sources={gcnEventSources.geojson}
              />
            </div>
          </li>
        ))}
      </div>
      <h3 style={{ display: "inline-block" }}>GCN Notices</h3>
      <div>
        &nbsp; -&nbsp;
        {gcnEvent.gcn_notices?.map((gcn_notice) => (
          <li key={gcn_notice.ivorn}>
            <DownloadXMLButton gcn_notice={gcn_notice} />
          </li>
        ))}
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
  sources: PropTypes.shape({
    length: PropTypes.number,
    features: GeoPropTypes.FeatureCollection,
  }).isRequired,
};

DownloadXMLButton.propTypes = {
  gcn_notice: PropTypes.shape({
    content: PropTypes.string,
    ivorn: PropTypes.string,
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
  sources: PropTypes.shape({
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
};

GcnEventSourcesPage.defaultProps = {
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
};

export default GcnEventPage;
