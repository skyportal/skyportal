import React, { Suspense, useState } from "react";
import PropTypes from "prop-types";
import { useSelector, useDispatch } from "react-redux";

import TableCell from "@material-ui/core/TableCell";
import TableRow from "@material-ui/core/TableRow";

import Typography from "@material-ui/core/Typography";
import IconButton from "@material-ui/core/IconButton";
import Button from "@material-ui/core/Button";
import Grid from "@material-ui/core/Grid";
import Chip from "@material-ui/core/Chip";
import Link from "@material-ui/core/Link";
import PictureAsPdfIcon from "@material-ui/icons/PictureAsPdf";
import CircularProgress from "@material-ui/core/CircularProgress";
import Popover from "@material-ui/core/Popover";
import SortIcon from "@material-ui/icons/Sort";
import ArrowUpward from "@material-ui/icons/ArrowUpward";
import ArrowDownward from "@material-ui/icons/ArrowDownward";
import Form from "@rjsf/material-ui";
import MUIDataTable from "mui-datatables";
import { makeStyles } from "@material-ui/core/styles";
import Tooltip from "@material-ui/core/Tooltip";
import GroupIcon from "@material-ui/icons/Group";

import dayjs from "dayjs";

import { ra_to_hours, dec_to_dms } from "../units";
import styles from "./CommentList.css";
import ThumbnailList from "./ThumbnailList";
import UserAvatar from "./UserAvatar";
import ShowClassification from "./ShowClassification";
import * as sourceActions from "../ducks/source";
import * as sourcesActions from "../ducks/sources";

const VegaPlot = React.lazy(() => import("./VegaPlot"));
const VegaSpectrum = React.lazy(() => import("./VegaSpectrum"));

const useStyles = makeStyles((theme) => ({
  chip: {
    margin: theme.spacing(0.5),
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
  sortButtton: {
    "&:hover": {
      color: theme.palette.primary.main,
    },
  },
  icon: {
    verticalAlign: "top",
  },
  sortFormContainer: {
    padding: "1rem",
  },
}));

// MUI data table with pull out rows containing a summary of each source.
// This component is used in GroupSources and SourceList.
const SourceTable = ({
  sources,
  title,
  sourceStatus = "saved",
  groupID,
  paginateCallback,
  pageNumber,
  totalMatches,
  numPerPage,
  sortingCallback,
}) => {
  // sourceStatus should be one of either "saved" (default) or "requested" to add a button to agree to save the source.
  // If groupID is not given, show all data available to user's accessible groups

  const dispatch = useDispatch();
  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const classes = useStyles();

  const [sortAnchorEl, setSortAnchorEl] = useState(null);
  const handleSortClick = (event) => {
    setSortAnchorEl(event.currentTarget);
  };
  const handleSortClose = () => {
    setSortAnchorEl(null);
  };
  const sortOpen = Boolean(sortAnchorEl);
  const sortId = sortOpen ? "sort-popover" : undefined;
  const [currentSortColumn, setCurrentSortColumn] = useState(null);

  // Color styling
  const userColorTheme = useSelector(
    (state) => state.profile.preferences.theme
  );
  const commentStyle =
    userColorTheme === "dark" ? styles.commentDark : styles.comment;

  if (!sources) {
    return (
      <div>
        <CircularProgress color="secondary" />
      </div>
    );
  }

  const handleTableChange = (action, tableState) => {
    switch (action) {
      case "changePage":
      case "changeRowsPerPage":
        paginateCallback(tableState.page + 1, tableState.rowsPerPage);
        break;
      default:
    }
  };

  const handleSaveSource = async (sourceID) => {
    const result = await dispatch(
      sourceActions.acceptSaveRequest({ sourceID, groupID })
    );
    if (result.status === "success") {
      dispatch(
        sourcesActions.fetchPendingGroupSources({
          group_ids: [groupID],
          pageNumber: 1,
          numPerPage: 10,
        })
      );
      dispatch(
        sourcesActions.fetchSavedGroupSources({
          group_ids: [groupID],
          pageNumber: 1,
          numPerPage: 10,
        })
      );
    }
  };

  const handleIgnoreSource = async (sourceID) => {
    const result = await dispatch(
      sourceActions.declineSaveRequest({ sourceID, groupID })
    );
    if (result.status === "success") {
      dispatch(
        sourcesActions.fetchPendingGroupSources({
          group_ids: [groupID],
          pageNumber: 1,
          numPerPage: 10,
        })
      );
    }
  };

  if (sources.length === 0 && sourceStatus === "saved") {
    return (
      <Grid item>
        <div>
          <Typography
            variant="h4"
            gutterBottom
            color="textSecondary"
            align="center"
          >
            <b>No sources have been saved...</b>
          </Typography>
        </div>
      </Grid>
    );
  }
  if (sources.length === 0 && sourceStatus === "requested") {
    return null;
  }

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderPullOutRow = (rowData, rowMeta) => {
    const colSpan = rowData.length + 1;
    const source = sources[rowMeta.dataIndex];

    const comments = source.comments || [];

    return (
      <TableRow data-testid={`groupSourceExpand_${source.id}`}>
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
              <Suspense fallback={<div>Loading spectra...</div>}>
                <VegaSpectrum dataUrl={`/api/sources/${source.id}/spectra`} />
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
    const objid = sources[dataIndex].id;
    return (
      <a href={`/source/${objid}`} key={`${objid}_objid`}>
        {objid}
      </a>
    );
  };

  const renderAlias = (dataIndex) => {
    const { id: objid, alias } = sources[dataIndex];

    return (
      <a href={`/source/${objid}`} key={`${objid}_alias`}>
        {alias}
      </a>
    );
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.

  const renderRA = (dataIndex) => {
    const source = sources[dataIndex];
    return <div key={`${source.id}_ra`}>{source.ra.toFixed(6)}</div>;
  };

  const renderRASex = (dataIndex) => {
    const source = sources[dataIndex];
    return <div key={`${source.id}_ra_sex`}>{ra_to_hours(source.ra)}</div>;
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderDec = (dataIndex) => {
    const source = sources[dataIndex];
    return <div key={`${source.id}_dec`}>{source.dec.toFixed(6)}</div>;
  };

  const renderDecSex = (dataIndex) => {
    const source = sources[dataIndex];
    return <div key={`${source.id}_dec_sex`}>{dec_to_dms(source.dec)}</div>;
  };

  // helper function to get the classifications
  const getClassifications = (source) => {
    if (groupID !== undefined) {
      return source.classifications.filter((cls) => {
        return cls.groups.find((g) => {
          return g.id === groupID;
        });
      });
    }
    return source.classifications;
  };

  const renderClassification = (dataIndex) => {
    const source = sources[dataIndex];

    return (
      <Suspense fallback={<div>Loading classifications</div>}>
        <ShowClassification
          classifications={getClassifications(source)}
          taxonomyList={taxonomyList}
          shortened
        />
      </Suspense>
    );
  };

  // helper function to get the source groups
  const getGroups = (source) => {
    return source.groups.filter((group) => group.active);
  };

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderGroups = (dataIndex) => {
    const source = sources[dataIndex];
    return (
      <div key={`${source.id}_groups`}>
        {getGroups(source).map((group) => (
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

  // helper function to get the source saved_at date
  const getDate = (source) => {
    if (groupID !== undefined) {
      const group = source.groups.find((g) => {
        return g.id === groupID;
      });
      return group?.saved_at;
    }
    const dates = source.groups
      .map((g) => {
        return g.saved_at;
      })
      .sort();
    return dates[dates.length - 1];
  };

  const renderDateSaved = (dataIndex) => {
    const source = sources[dataIndex];

    return (
      <div key={`${source.id}_date_saved`}>
        {getDate(source)?.substring(0, 19)}
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

  // This is just passed to MUI datatables options -- not meant to be instantiated directly.
  const renderSaveIgnore = (dataIndex) => {
    const source = sources[dataIndex];
    return (
      <>
        <Button
          size="small"
          variant="contained"
          onClick={() => {
            handleSaveSource(source.id);
          }}
          data-testid={`saveSourceButton_${source.id}`}
        >
          Save
        </Button>
        &nbsp;
        <Button
          size="small"
          variant="contained"
          onClick={() => {
            handleIgnoreSource(source.id);
          }}
          data-testid={`declineRequestButton_${source.id}`}
        >
          Ignore
        </Button>
      </>
    );
  };

  const renderHeader = (name, label) => {
    const sortedOn = currentSortColumn && currentSortColumn.column === name;
    return (
      <div>
        {label}
        {sortedOn && currentSortColumn.ascending && (
          <ArrowUpward fontSize="small" className={classes.icon} />
        )}
        {sortedOn && !currentSortColumn.ascending && (
          <ArrowDownward fontSize="small" className={classes.icon} />
        )}
      </div>
    );
  };

  const handleSortSubmit = ({ formData }) => {
    setCurrentSortColumn(formData);
    handleSortClose();
    sortingCallback(formData);
  };
  const sortingFormSchema = {
    description: "Sort by column",
    type: "object",
    properties: {
      column: {
        type: "string",
        title: "Column",
        enum: ["id", "ra", "dec", "redshift", "saved_at"],
        enumNames: ["Source ID", "RA", "Dec", "Redshift", "Date Saved"],
      },
      ascending: {
        title: "Order",
        type: "boolean",
        enumNames: ["Ascending", "Descending"],
      },
    },
  };

  const sortingFormUISchema = {
    ascending: {
      "ui:widget": "radio",
    },
  };

  const renderSortForm = () => {
    return (
      <>
        <Tooltip title="Sort">
          <span>
            <IconButton
              aria-describedby={sortId}
              onClick={handleSortClick}
              className={classes.sortButtton}
              data-testid="sortButton"
            >
              <SortIcon />
            </IconButton>
          </span>
        </Tooltip>

        <Popover
          id={sortId}
          open={sortOpen}
          onClose={handleSortClose}
          anchorEl={sortAnchorEl}
          anchorOrigin={{
            vertical: "center",
            horizontal: "left",
          }}
          transformOrigin={{
            vertical: "top",
            horizontal: "right",
          }}
        >
          <div className={classes.sortFormContainer}>
            <Form
              schema={sortingFormSchema}
              onSubmit={handleSortSubmit}
              uiSchema={sortingFormUISchema}
            />
          </div>
        </Popover>
      </>
    );
  };

  const columns = [
    {
      name: "id",
      label: "Source ID",
      options: {
        filter: true,
        customBodyRenderLite: renderObjId,
        customHeadLabelRender: () => renderHeader("id", "Source ID"),
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
      name: "ra",
      label: "RA (deg)",
      options: {
        filter: false,
        customBodyRenderLite: renderRA,
        customHeadLabelRender: () => renderHeader("ra", "RA (deg)"),
      },
    },
    {
      name: "dec",
      label: "Dec (deg)",
      options: {
        filter: false,
        customBodyRenderLite: renderDec,
        customHeadLabelRender: () => renderHeader("dec", "Dec (deg)"),
      },
    },
    {
      name: "ra",
      label: "RA (hh:mm:ss)",
      options: {
        filter: false,
        display: false,
        customBodyRenderLite: renderRASex,
        customHeadLabelRender: () => renderHeader("ra", "RA (hh:mm:ss)"),
      },
    },
    {
      name: "dec",
      label: "Dec (dd:mm:ss)",
      options: {
        filter: false,
        display: false,
        customBodyRenderLite: renderDecSex,
        customHeadLabelRender: () => renderHeader("dec", "Dec (dd:mm:ss)"),
      },
    },
    {
      name: "redshift",
      label: "Redshift",
      options: {
        filter: false,
        customHeadLabelRender: () => renderHeader("redshift", "Redshift"),
      },
    },
    {
      name: "classification",
      label: "Classification",
      options: {
        filter: true,
        customBodyRenderLite: renderClassification,
        customHeadLabelRender: () =>
          renderHeader("classification", "Classification"),
      },
    },
    {
      name: "groups",
      label: "Groups",
      options: {
        filter: false,
        customBodyRenderLite: renderGroups,
      },
    },
    {
      name: "saved_at",
      label: "Date Saved",
      options: {
        filter: false,
        customBodyRenderLite: renderDateSaved,
        customHeadLabelRender: () => renderHeader("saved_at", "Date Saved"),
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
    sort: false,
    customToolbar: renderSortForm,
    onTableChange: handleTableChange,
    serverSide: true,
    rowsPerPage: numPerPage,
    page: pageNumber - 1,
    rowsPerPageOptions: [10, 25, 50, 75, 100, 200],
    jumpToPage: true,
    pagination: true,
    count: totalMatches,
    filter: false,
    search: false,
  };

  if (sourceStatus === "requested") {
    columns.push({
      name: "Save/Decline",
      options: {
        filter: false,
        customBodyRenderLite: renderSaveIgnore,
      },
    });
  }

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
          <Grid item className={classes.tableGrid}>
            <MUIDataTable
              title={title}
              columns={columns}
              data={sources}
              options={options}
            />
          </Grid>
        </Grid>
      </div>
    </div>
  );
};

SourceTable.propTypes = {
  sources: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      ra: PropTypes.number,
      dec: PropTypes.number,
      alias: PropTypes.string,
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
      groups: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number,
          name: PropTypes.string,
        })
      ),
    })
  ).isRequired,
  sourceStatus: PropTypes.string,
  groupID: PropTypes.number,
  title: PropTypes.string,
  paginateCallback: PropTypes.func.isRequired,
  pageNumber: PropTypes.number,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
  sortingCallback: PropTypes.func,
};

SourceTable.defaultProps = {
  sourceStatus: "saved",
  groupID: undefined,
  title: "",
  pageNumber: 1,
  totalMatches: 0,
  numPerPage: 10,
  sortingCallback: null,
};

export default SourceTable;
