import React, { useEffect, Suspense } from "react";
import Link from "@material-ui/core/Link";
import { useSelector, useDispatch } from "react-redux";

import Typography from "@material-ui/core/Typography";
import Paper from "@material-ui/core/Paper";
import TableCell from "@material-ui/core/TableCell";
import TableRow from "@material-ui/core/TableRow";
import IconButton from "@material-ui/core/IconButton";
import Grid from "@material-ui/core/Grid";
import Chip from "@material-ui/core/Chip";
import PictureAsPdfIcon from "@material-ui/icons/PictureAsPdf";
import MUIDataTable from "mui-datatables";
import Tooltip from "@material-ui/core/Tooltip";
import GroupIcon from "@material-ui/icons/Group";
import { makeStyles } from "@material-ui/core/styles";
import dayjs from "dayjs";

import styles from "./CommentList.css";
import SearchBox from "./SearchBox";
import * as sourcesActions from "../ducks/sources";
import UninitializedDBMessage from "./UninitializedDBMessage";
import ShowClassification from "./ShowClassification";
import ThumbnailList from "./ThumbnailList";
import UserAvatar from "./UserAvatar";
import { ra_to_hours, dec_to_dms } from "../units";

const VegaPlot = React.lazy(() => import("./VegaPlot"));

const useStyles = makeStyles(() => ({
  paperDiv: {
    padding: "1rem",
    height: "100%",
  },
  tableGrid: {
    width: "100%",
  },
}));

const SourceList = () => {
  const classes = useStyles();
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const sources = useSelector((state) => state.sources);
  const sourceTableEmpty = useSelector(
    (state) => state.dbInfo.source_table_empty
  );

  const dispatch = useDispatch();

  useEffect(() => {
    if (!sources.latest) {
      dispatch(sourcesActions.fetchSources());
    }
  }, [sources.latest, dispatch]);

  // Color styling
  const userColorTheme = useSelector(
    (state) => state.profile.preferences.theme
  );
  const commentStyle =
    userColorTheme === "dark" ? styles.commentDark : styles.comment;

  const groupID = 7; // need to get rid of this

  if (sourceTableEmpty) {
    return <UninitializedDBMessage />;
  }
  if (sources.latest) {
    // This is just passed to MUI datatables options -- not meant to be instantiated directly.
    const renderPullOutRow = (rowData, rowMeta) => {
      const colSpan = rowData.length + 1;
      const source = sources.latest[rowMeta.dataIndex];

      const comments = source.comments || [];

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
                <div className={classes.commentListContainer}>
                  {comments.map(
                    ({
                      id,
                      author,
                      author_info,
                      created_at,
                      text,
                      attachment_name,
                      groups: comment_groups,
                    }) => (
                      <span key={id} className={commentStyle}>
                        <div className={styles.commentUserAvatar}>
                          <UserAvatar
                            size={24}
                            firstName={author_info.first_name}
                            lastName={author_info.last_name}
                            username={author_info.username}
                            gravatarUrl={author_info.gravatar_url}
                          />
                        </div>
                        <div className={styles.commentContent}>
                          <div className={styles.commentHeader}>
                            <span className={styles.commentUser}>
                              <span className={styles.commentUserName}>
                                {author.username}
                              </span>
                            </span>
                            <span className={styles.commentTime}>
                              {dayjs().to(dayjs.utc(`${created_at}Z`))}
                            </span>
                            <div className={styles.commentUserGroup}>
                              <Tooltip
                                title={comment_groups
                                  .map((group) => group.name)
                                  .join(", ")}
                              >
                                <GroupIcon
                                  fontSize="small"
                                  viewBox="0 -2 24 24"
                                />
                              </Tooltip>
                            </div>
                          </div>
                          <div className={styles.wrap} name={`commentDiv${id}`}>
                            <div className={styles.commentMessage}>{text}</div>
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
                    )
                  )}
                </div>
              </Grid>
            </Grid>
          </TableCell>
        </TableRow>
      );
    };

    // This is just passed to MUI datatables options -- not meant to be instantiated directly.
    const renderObjId = (dataIndex) => {
      const objid = sources.latest[dataIndex].id;
      return (
        <a href={`/source/${objid}`} key={`${objid}_objid`}>
          {objid}
        </a>
      );
    };

    // This is just passed to MUI datatables options -- not meant to be instantiated directly.
    const renderAlias = (dataIndex) => {
      const { id: objid, alias } = sources.latest[dataIndex];

      return (
        <a href={`/source/${objid}`} key={`${objid}_alias`}>
          {alias}
        </a>
      );
    };

    // This is just passed to MUI datatables options -- not meant to be instantiated directly.
    const renderRA = (dataIndex) => {
      const source = sources.latest[dataIndex];
      return <div key={`${source.id}_ra`}>{source.ra.toFixed(6)}</div>;
    };

    // This is just passed to MUI datatables options -- not meant to be instantiated directly.
    const renderRASex = (dataIndex) => {
      const source = sources.latest[dataIndex];
      return <div key={`${source.id}_ra_sex`}>{ra_to_hours(source.ra)}</div>;
    };

    // This is just passed to MUI datatables options -- not meant to be instantiated directly.
    const renderDec = (dataIndex) => {
      const source = sources.latest[dataIndex];
      return <div key={`${source.id}_dec`}>{source.dec.toFixed(6)}</div>;
    };

    // This is just passed to MUI datatables options -- not meant to be instantiated directly.
    const renderDecSex = (dataIndex) => {
      const source = sources.latest[dataIndex];
      return <div key={`${source.id}_dec_sex`}>{dec_to_dms(source.dec)}</div>;
    };

    // This is just passed to MUI datatables options -- not meant to be instantiated directly.
    const renderRedshift = (dataIndex) => {
      const source = sources.latest[dataIndex];
      return <div key={`${source.id}_redshift`}>{source.redshift}</div>;
    };

    // This is just passed to MUI datatables options -- not meant to be instantiated directly.
    const renderClassification = (dataIndex) => {
      const source = sources.latest[dataIndex];
      return (
        <Suspense fallback={<div>Loading classifications</div>}>
          <ShowClassification
            classifications={source.classifications.filter((cls) => {
              return cls.groups.find((g) => {
                return g.id === groupID;
              });
            })}
            taxonomyList={taxonomyList}
            shortened
          />
        </Suspense>
      );
    };

    // This is just passed to MUI datatables options -- not meant to be instantiated directly.
    const renderGroups = (dataIndex) => {
      const source = sources.latest[dataIndex];
      return (
        <div key={`${source.id}_groups`}>
          {source.groups
            .filter((group) => group.active)
            .map((group) => (
              <div key={group.name}>
                <Chip
                  label={group.name.substring(0, 15)}
                  key={group.id}
                  size="small"
                  className={classes.chip}
                />
                <br />
              </div>
            ))}
        </div>
      );
    };

    // This is just passed to MUI datatables options -- not meant to be instantiated directly.
    const renderDateSaved = (dataIndex) => {
      const source = sources.latest[dataIndex];

      const group = source.groups.find((g) => {
        return g.id === groupID;
      });
      return (
        <div key={`${source.id}_date_saved`}>
          {group.saved_at.substring(0, 19)}
        </div>
      );
    };

    // This is just passed to MUI datatables options -- not meant to be instantiated directly.
    const renderFinderButton = (dataIndex) => {
      const source = sources.latest[dataIndex];
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
        name: "Alias",
        options: {
          filter: true,
          display: false,
          customBodyRenderLite: renderAlias,
        },
      },
      {
        name: "RA (deg)",
        options: {
          filter: false,
          customBodyRenderLite: renderRA,
        },
      },
      {
        name: "Dec (deg)",
        options: {
          filter: false,
          customBodyRenderLite: renderDec,
        },
      },
      {
        name: "RA (hh:mm:ss)",
        options: {
          filter: false,
          display: false,
          customBodyRenderLite: renderRASex,
        },
      },
      {
        name: "Dec (dd:mm:ss)",
        options: {
          filter: false,
          display: false,
          customBodyRenderLite: renderDecSex,
        },
      },
      {
        name: "Redshift",
        options: {
          filter: false,
          customBodyRenderLite: renderRedshift,
        },
      },
      {
        name: "Classification",
        options: {
          filter: true,
          customBodyRenderLite: renderClassification,
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
        name: "Date Saved",
        options: {
          filter: false,
          customBodyRenderLite: renderDateSaved,
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

    const data = sources.latest.map((source) => [
      source.id,
      source.alias,
      source.ra,
      source.dec,
      ra_to_hours(source.ra),
      dec_to_dms(source.dec),
      source.redshift,
      source.groups.map((group) => {
        return group.name;
      }),
    ]);

    return (
      <Paper elevation={1}>
        <div className={classes.paperDiv}>
          <Typography variant="h6" display="inline">
            Sources
          </Typography>
          <SearchBox sources={sources} />
          {!sources.queryInProgress && (
            <Grid item className={classes.tableGrid}>
              <MUIDataTable columns={columns} data={data} options={options} />
            </Grid>
          )}
          {sources.queryInProgress && (
            <div>
              <br />
              <br />
              <i>Query in progress...</i>
            </div>
          )}
        </div>
      </Paper>
    );
  }
  return <div>Loading sources...</div>;
};

export default SourceList;
