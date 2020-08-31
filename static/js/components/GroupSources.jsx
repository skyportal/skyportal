import React, { useEffect, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import TableCell from "@material-ui/core/TableCell";
import TableRow from "@material-ui/core/TableRow";

import Typography from "@material-ui/core/Typography";
import IconButton from "@material-ui/core/IconButton";
import Grid from "@material-ui/core/Grid";
// import BuildIcon from "@material-ui/icons/Build";

import Link from "@material-ui/core/Link";
import PictureAsPdfIcon from "@material-ui/icons/PictureAsPdf";

import MUIDataTable from "mui-datatables";
import ThumbnailList from "./ThumbnailList";
import styles from "./RunSummary.css";
import * as SourcesAction from "../ducks/sources";
import { ra_to_hours, dec_to_hours } from "../units";

const VegaPlot = React.lazy(() => import("./VegaPlot"));

const GroupSources = ({ route }) => {
  const dispatch = useDispatch();
  const sources = useSelector((state) => state.sources.latest);
  const groups = useSelector((state) => state.groups.user);

  // Load the group sources
  useEffect(() => {
    dispatch(SourcesAction.fetchSources({ group_id: route.id }));
  }, [route.id, dispatch]);

  if (sources === undefined || sources === null) {
    return "Loading Sources...";
  }

  const group_id = parseInt(route.id, 10);
  let group_name = "";

  if (groups !== undefined && groups !== null) {
    const group = groups.find((g) => {
      // find the object for the group
      return g.id === group_id;
    });

    if (group === undefined || group === null) {
      // couldn't find a group object
      group_name = "";
    } else {
      group_name = group.name;
    }
  }

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderPullOutRow = (rowData, rowMeta) => {
    if (sources === undefined) {
      return "Loading...";
    }

    const colSpan = rowData.length + 1;
    const source = sources[rowMeta.rowIndex];

    return (
      <TableRow>
        <TableCell
          style={{ paddingBottom: 0, paddingTop: 0 }}
          colSpan={colSpan}
        >
          <Grid
            container
            direction="row"
            spacing={3}
            justify="center"
            alignItems="center"
          >
            <ThumbnailList
              thumbnails={source.thumbnails}
              ra={source.ra}
              dec={source.dec}
              useGrid={false}
            />
            <Grid item>
              <Suspense fallback={<div>Loading plot...</div>}>
                <VegaPlot dataUrl={`/api/sources/${source.id}/photometry`} />
              </Suspense>
            </Grid>
          </Grid>
        </TableCell>
      </TableRow>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderObjId = (dataIndex) => {
    const objid = sources[dataIndex].id;
    return (
      <a href={`/source/${objid}`} key={`${objid}_objid`}>
        {objid}
      </a>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.

  const renderRA = (dataIndex) => {
    const source = sources[dataIndex];
    return (
      <div key={`${source.id}_ra`}>
        {source.ra}
        <br />
        {ra_to_hours(source.ra)}
      </div>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderDec = (dataIndex) => {
    const source = sources[dataIndex];
    return (
      <div key={`${source.id}_dec`}>
        {source.dec}
        <br />
        {dec_to_hours(source.dec)}
      </div>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderFinderButton = (dataIndex) => {
    const source = sources[dataIndex];
    return (
      <IconButton size="small" key={`${source.id}_actions`}>
        <Link href={`/api/sources/${source.id}/finder`}>
          <PictureAsPdfIcon />
        </Link>
      </IconButton>
    );
  };

  const columns = [
    {
      name: "Source ID",
      options: {
        filter: true,
        customBodyRenderLite: renderObjId,
      },
    },
    {
      name: "RA",
      options: {
        filter: false,
        customBodyRenderLite: renderRA,
      },
    },
    {
      name: "Dec",
      options: {
        filter: false,
        customBodyRenderLite: renderDec,
      },
    },
    {
      name: "Redshift",
      options: {
        filter: false,
      },
    },
    {
      name: "Finder",
      options: {
        filter: false,
        customBodyRenderLite: renderFinderButton,
      },
    },
  ];

  const options = {
    draggableColumns: { enabled: true },
    expandableRows: true,
    renderExpandableRow: renderPullOutRow,
    selectableRows: "none",
  };

  const data = sources.map((source) => [
    source.id,
    source.ra,
    source.dec,
    source.redshift,
  ]);

  return (
    <div className={styles.source}>
      <div>
        <Grid
          container
          direction="column"
          alignItems="center"
          justify="flex-start"
          spacing={3}
        >
          <Grid item>
            <div>
              <Typography
                variant="h4"
                gutterBottom
                color="textSecondary"
                align="center"
              >
                <em>Group Sources:</em>
              </Typography>
              <Typography
                variant="h4"
                gutterBottom
                color="textSecondary"
                align="center"
              >
                <b>Sources for {group_name}</b>
              </Typography>
            </div>
          </Grid>
          <Grid item>
            <MUIDataTable
              title="Sources"
              columns={columns}
              data={data}
              options={options}
            />
          </Grid>
        </Grid>
      </div>
    </div>
  );
};

GroupSources.propTypes = {
  route: PropTypes.shape({
    id: PropTypes.string,
  }).isRequired,
};

export default GroupSources;
