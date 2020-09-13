import React, { useEffect, Suspense } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import TableCell from "@material-ui/core/TableCell";
import TableRow from "@material-ui/core/TableRow";

import Typography from "@material-ui/core/Typography";
import IconButton from "@material-ui/core/IconButton";
import Grid from "@material-ui/core/Grid";
import Chip from "@material-ui/core/Chip";
import Link from "@material-ui/core/Link";
import PictureAsPdfIcon from "@material-ui/icons/PictureAsPdf";

import MUIDataTable from "mui-datatables";
import { makeStyles } from "@material-ui/core/styles";

import Tooltip from "@material-ui/core/Tooltip";
import GroupIcon from "@material-ui/icons/Group";

import dayjs from "dayjs";

import { ra_to_hours, dec_to_hours } from "../units";
import * as SourcesAction from "../ducks/sources";
// import styles from "./GroupSources.css";
import ThumbnailList from "./ThumbnailList";
import UserAvatar from "./UserAvatar";
import ShowClassification from "./ShowClassification";

const VegaPlot = React.lazy(() => import("./VegaPlot"));

const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
  },
  source: {},
  commentContent: {
    display: "flex",
    flexFlow: "column nowrap",
    padding: "0.3125rem 0.625rem 0.3125rem 0.875rem",
    borderRadius: "15px",
  },
  comment: {
    fontSize: "90%",
    display: "flex",
    flexDirection: "row",
    padding: "0.125rem",
    marginBottom: "0.125rem",
    marginRight: "0.125rem",
    borderRadius: "1rem",
    "& > commentContent": {
      backgroundColor: "#e0e0e0",
    },
    "&:hover": {
      backgroundColor: "#e0e0e0",
    },
  },
  commentDark: {
    fontSize: "90%",
    display: "flex",
    flexDirection: "row",
    padding: "0.125rem",
    marginBottom: "0.125rem",
    marginRight: "0.125rem",
    borderRadius: "1rem",
    "& > commentContent": {
      backgroundColor: "#3a3a3a",
    },
    "&:hover": {
      backgroundColor: "#3a3a3a",
    },
  },
  commentHeader: {
    flexGrow: 4,
    paddingTop: "0.5rem",
    paddingBottom: "0.5rem",
    maxWidth: "25rem",
  },
  commentUser: {},
  commentUserName: {
    fontWeight: "bold",
    marginRight: "0.5rem",
  },
  commentTime: {
    color: "gray",
    fontSize: "80%",
    marginRight: "1rem",
  },
  commentUserGroup: {
    display: "inline-block",
  },
  "& > svg": {
    fontSize: "1rem",
  },
  commentMessage: {
    maxWidth: "20rem",
  },
  commentUserAvatar: {
    display: "block",
    margin: "0.5rem",
  },
  commentsList: {
    overflowY: "scroll",
    maxHeight: "350px",
  },
  wrap: {
    display: "flex",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    minHeight: "27px",
    maxWidth: "20rem",
  },
}));

const GroupSources = ({ route }) => {
  const dispatch = useDispatch();
  const sources = useSelector((state) => state.sources.groupSources);
  const groups = useSelector((state) => state.groups.user);
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const classes = useStyles();

  // Color styling
  const userColorTheme = useSelector(
    (state) => state.profile.preferences.theme
  );

  const commentStyle =
    userColorTheme === "dark" ? classes.commentDark : classes.comment;

  // Load the group sources
  useEffect(() => {
    dispatch(SourcesAction.fetchGroupSources({ group_id: route.id }));
  }, [route.id, dispatch]);

  if (!sources) {
    return "Loading Sources...";
  }

  const group_id = parseInt(route.id, 10);
  let group_name = "";

  if (groups) {
    const group = groups.find((g) => {
      // find the object for the group
      return g.id === group_id;
    });
    group_name = group?.name;
  }

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderPullOutRow = (rowData, rowMeta) => {
    if (!sources) {
      return "Loading...";
    }

    const colSpan = rowData.length + 1;
    const source = sources[rowMeta.rowIndex];

    const comments = source.comments || [];

    const items = comments.map(
      ({
        id,
        author,
        author_info,
        created_at,
        text,
        attachment_name,
        groups: comment_groups,
      }) => {
        return (
          <span key={id} className={commentStyle}>
            <div className={classes.commentUserAvatar}>
              <UserAvatar
                size={24}
                firstName={author_info.first_name}
                lastName={author_info.last_name}
                username={author_info.username}
                gravatarUrl={author_info.gravatar_url}
              />
            </div>
            <div className={classes.commentContent}>
              <div className={classes.commentHeader}>
                <span className={classes.commentUser}>
                  <span className={classes.commentUserName}>
                    {author.username}
                  </span>
                </span>
                <span className={classes.commentTime}>
                  {dayjs().to(dayjs.utc(`${created_at}Z`))}
                </span>
                <div className={classes.commentUserGroup}>
                  <Tooltip
                    title={comment_groups.map((group) => group.name).join(", ")}
                  >
                    <GroupIcon fontSize="small" viewBox="0 -2 24 24" />
                  </Tooltip>
                </div>
              </div>
              <div className={classes.wrap} name={`commentDiv${id}`}>
                <div className={classes.commentMessage}>{text}</div>
              </div>
              <span>
                {attachment_name && (
                  <div>
                    Attachment:&nbsp;
                    <a href={`/api/comment/${id}/attachment`}>
                      {attachment_name}
                    </a>
                  </div>
                )}
              </span>
            </div>
          </span>
        );
      }
    );

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
            <Grid item>
              <div className={classes.commentsList}>{items}</div>
            </Grid>
            <Grid item>
              <Suspense fallback={<div>Loading classifications</div>}>
                <ShowClassification
                  classifications={source.classifications}
                  taxonomyList={taxonomyList}
                />
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
  const renderGroups = (dataIndex) => {
    const source = sources[dataIndex];
    return (
      <div key={`${source.id}_groups`}>
        {source.groups.map((group) => (
          <Chip
            label={group.name.substring(0, 15)}
            key={group.id}
            size="small"
            className={classes.chip}
          />
        ))}
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
      name: "Groups",
      options: {
        filter: false,
        customBodyRenderLite: renderGroups,
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
    source.classifications,
    source.groups,
    source.recent_comments,
  ]);

  return (
    <div className={classes.source}>
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
                <b>Sources saved to {group_name}</b>
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
