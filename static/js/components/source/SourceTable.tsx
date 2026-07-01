import { useGetProfileQuery } from "../../ducks/profile";
import React, {
  Suspense,
  useEffect,
  useState,
  useMemo,
  useCallback,
} from "react";
import { Link, useNavigate } from "react-router-dom";
import { Controller, useForm } from "react-hook-form";

import IconButton from "@mui/material/IconButton";
import FormControlLabel from "@mui/material/FormControlLabel";
import Grid from "@mui/material/Grid";
import AddIcon from "@mui/icons-material/Add";
import Chip from "@mui/material/Chip";
import DeleteIcon from "@mui/icons-material/Delete";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import ThumbUp from "@mui/icons-material/ThumbUp";
import ThumbDown from "@mui/icons-material/ThumbDown";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import FilterListIcon from "@mui/icons-material/FilterList";
import DownloadIcon from "@mui/icons-material/Download";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";
import Box from "@mui/material/Box";
import { makeStyles } from "tss-react/mui";
import Checkbox from "@mui/material/Checkbox";
import CheckIcon from "@mui/icons-material/Check";
import ClearIcon from "@mui/icons-material/Clear";
import InfoIcon from "@mui/icons-material/Info";
import QuestionMarkIcon from "@mui/icons-material/QuestionMark";
import PriorityHigh from "@mui/icons-material/PriorityHigh";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import Collapse from "@mui/material/Collapse";
import List from "@mui/material/List";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { isMobileOnly } from "react-device-detect";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import Button from "../Button";
import StyledDataGridBase, { DataGridToolbar } from "../StyledDataGrid";
import DisplayPhotStats from "./DisplayPhotStats";

import { dec_to_dms, mjd_to_utc, ra_to_hours } from "../../units";
import ThumbnailList from "../thumbnail/ThumbnailList";
import ShowClassification from "../classification/ShowClassification";
import ShowSummaries from "../summary/ShowSummaries";
import ShowSummaryHistory from "../summary/ShowSummaryHistory";
import SourceTableFilterForm from "./SourceTableFilterForm";
import StartBotSummary from "../StartBotSummary";
import VegaPhotometry from "../plot/VegaPhotometry";
import FavoritesButton from "../listing/FavoritesButton";
import MultipleClassificationsForm from "../classification/MultipleClassificationsForm";
import UpdateSourceSummary from "./UpdateSourceSummary";
import {
  useDeleteClassificationsMutation,
  useAddClassificationVoteMutation,
  useAddSourceLabelsMutation,
  useDeleteSourceLabelsMutation,
  useAcceptSaveRequestMutation,
  useDeclineSaveRequestMutation,
} from "../../ducks/source";
import {
  useLazyFetchPendingGroupSourcesQuery,
  useLazyFetchSavedGroupSourcesQuery,
} from "../../ducks/sources";
import { photometryApi } from "../../ducks/photometry";
import { useGetSourcesInGcnQuery } from "../../ducks/sourcesingcn";
import { useGetGcnEventQuery } from "../../ducks/gcnEvent";
import { useGetTagOptionsQuery } from "../../ducks/objectTags";
import { useGetTaxonomiesQuery } from "../../ducks/taxonomies";
import { getContrastColor } from "../ObjectTags";
import { filterOutEmptyValues } from "../../API";
import { getAnnotationValueString } from "../candidate/ScanningPageCandidateAnnotations";
import ConfirmSourceInGCN from "./ConfirmSourceInGCN";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import NewSource from "./NewSource";

const VegaSpectrum = React.lazy(() => import("../plot/VegaSpectrum"));
const VegaHR = React.lazy(() => import("../plot/VegaHR"));

// StyledDataGrid is a .jsx component whose propTypes make `sx` look required to
// tsc; cast to any so call sites don't need to pass it.
const StyledDataGrid: any = StyledDataGridBase;

// Page-size options preserved from the previous mui-datatables config.
const PAGE_SIZE_OPTIONS = [1, 5, 10, 25, 50, 75, 100, 200];

// Map each DataGrid column `field` to the field name the server expects for
// sorting. Columns absent from this map are not server-sortable.
const SERVER_SORT_FIELD: Record<string, string> = {
  id: "id",
  alias: "alias",
  origin: "origin",
  ra: "ra",
  dec: "dec",
  ra_sex: "ra",
  dec_sex: "dec",
  l: "l",
  b: "b",
  redshift: "redshift",
  host: "host",
  host_offset: "host_offset",
  saved_at: "saved_at",
  gcn_status: "gcn_status",
};

const useStyles = makeStyles()((theme) => ({
  tableGrid: {
    width: "100%",
  },
  objId: {
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
  },
  filterAlert: {
    marginTop: "1rem",
    display: "flex",
    alignItems: "center",
    fontSize: "1rem",
  },
  annotations: {
    overflowWrap: "break-word",
  },
  root: {
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
  classificationDelete: {
    cursor: "pointer",
    fontSize: "2em",
    position: "absolute",
    padding: 0,
    right: 0,
    top: 0,
  },
  classificationDeleteDisabled: {
    opacity: 0,
  },
  widgetIcon: {
    display: "none",
  },
  groupChips: {
    display: "flex",
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    gap: "0.25rem",
    maxWidth: "120px",
  },
  filterChips: {
    display: "flex",
    flexWrap: "wrap",
    gap: "0.25rem",
    marginBottom: "0.5rem",
  },
}));

const RenderShowClassification = React.memo(({ source }: { source: any }) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [deleteClassificationsMutation] = useDeleteClassificationsMutation();
  const [addClassificationVote] = useAddClassificationVoteMutation();
  const { data: currentUser } = useGetProfileQuery();
  // The old global `group` slice (a single most-recently-fetched group) no
  // longer exists: the group duck is now RTK Query keyed by id, and no specific
  // group id is in scope here. As before, when no group is loaded the
  // membership lookup resolves to undefined.
  const groupUsers: any = undefined;
  const currentGroupUser = groupUsers?.filter(
    (groupUser: any) => groupUser.user_id === currentUser?.id,
  )[0];

  useEffect(() => {
    if (
      currentGroupUser?.admin !== undefined &&
      currentGroupUser?.admin !== null
    ) {
      window.localStorage.setItem(
        "CURRENT_GROUP_ADMIN",
        JSON.stringify(currentGroupUser.admin),
      );
    }
  }, [currentGroupUser]);

  const isGroupAdmin = JSON.parse(
    window.localStorage.getItem("CURRENT_GROUP_ADMIN") as any,
  );

  const { data: taxonomyList = [] } = useGetTaxonomiesQuery();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [classificationSourceToDelete, setClassificationSourceToDelete] =
    useState<any>(null);
  const openDialog = () => {
    setDialogOpen(true);
    setClassificationSourceToDelete(source.id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setClassificationSourceToDelete(null);
  };

  const deleteClassifications = () => {
    deleteClassificationsMutation(classificationSourceToDelete)
      .unwrap()
      .then(() => {
        dispatch(showNotification("Classification deleted"));
        closeDialog();
      })
      .catch(() => {
        // error notification handled by the baseQuery
      });
  };

  const addVotes = (vote: any) => {
    let success = true;
    source.classifications?.forEach((c: any) => {
      addClassificationVote({ classification_id: c.id, data: { vote } })
        .unwrap()
        .catch(() => {
          success = false;
        });
    });
    if (success) {
      dispatch(showNotification("Votes registered"));
    }
  };

  let upvoteColor: any = "disabled";
  let downvoteColor: any = "disabled";
  let upvoteValue = 1;
  let downvoteValue = -1;
  const upvoterIds: any[] = [];
  const downvoterIds: any[] = [];

  source.classifications?.forEach((classification: any) => {
    classification.votes?.forEach((s: any) => {
      if (s.voter_id === currentUser?.id) {
        if (s.vote === 1) {
          upvoterIds.push(classification.id);
        } else if (s.vote === -1) {
          downvoterIds.push(classification.id);
        }
      }
    });
  });

  if (source.classifications?.length === upvoterIds.length) {
    upvoteColor = "success";
    upvoteValue = 0;
  } else if (source.classifications?.length === downvoterIds.length) {
    downvoteColor = "error";
    downvoteValue = 0;
  }

  const permission =
    currentUser?.permissions.includes("System admin") ||
    currentUser?.permissions.includes("Manage groups") ||
    isGroupAdmin;

  return (
    <div>
      <Tooltip
        key={`${source.id}`}
        placement="top-end"
        disableFocusListener
        disableTouchListener
        title={
          <>
            <br />
            <b>All Classifications:</b>
            <br />
            <Button
              key={source.id}
              id="delete_classifications"
              classes={{
                root: classes.classificationDelete,
                disabled: classes.classificationDeleteDisabled,
              }}
              onClick={() => openDialog()}
              disabled={!permission}
            >
              <DeleteIcon />
            </Button>
            <ConfirmDeletionDialog
              deleteFunction={deleteClassifications}
              dialogOpen={dialogOpen}
              closeDialog={closeDialog}
              resourceName="classifications"
            />
            <div>
              <Button
                key={source.id}
                id="down_vote"
                onClick={() => addVotes(downvoteValue)}
              >
                <ThumbDown color={downvoteColor} />
              </Button>
            </div>
            <div>
              <Button
                key={source.id}
                id="up_vote"
                onClick={() => addVotes(upvoteValue)}
              >
                <ThumbUp color={upvoteColor} />
              </Button>
            </div>
          </>
        }
      >
        <div>
          <ShowClassification
            classifications={source.classifications}
            taxonomyList={taxonomyList}
            shortened
            fontSize="0.95rem"
          />
        </div>
      </Tooltip>
    </div>
  );
});
RenderShowClassification.displayName = "RenderShowClassification";

const RenderShowLabelling = React.memo(({ source }: { source: any }) => {
  const [addSourceLabels] = useAddSourceLabelsMutation();
  const [deleteSourceLabels] = useDeleteSourceLabelsMutation();
  const { control } = useForm();
  const [checked, setChecked] = useState(false);

  const { data: currentUser } = useGetProfileQuery();

  const labellerUsernames = source.labellers
    ? source.labellers.map((s: any) => s.username)
    : [];
  const defaultChecked = labellerUsernames.includes(currentUser?.username);

  useEffect(() => {
    setChecked(defaultChecked);
  }, [setChecked, defaultChecked]);

  const labelledSource = (check: any) => {
    const groupIds: any[] = [];
    source.groups?.forEach((g: any) => {
      groupIds.push(g.id);
    });

    if (check === true) {
      addSourceLabels({ id: source.id, data: { groupIds } });
    } else {
      deleteSourceLabels({ id: source.id, data: { groupIds } });
    }
  };

  const checkBox = (event: any) => {
    setChecked(event.target.checked);
  };

  return (
    <div>
      <FormControlLabel
        key={source.id}
        control={
          <Controller
            render={() => (
              <Checkbox
                onChange={(event) => {
                  checkBox(event);
                  labelledSource(event.target.checked);
                }}
                checked={checked}
                data-testid={`labellingCheckBox${source.id}`}
              />
            )}
            name={`labellingCheckBox${source.id}`}
            control={control}
          />
        }
        label={`Labelled By:  ${labellerUsernames.join(",")}`}
      />
    </div>
  );
});
RenderShowLabelling.displayName = "RenderShowLabelling";

// The pull-out detail panel previously rendered by mui-datatables'
// renderExpandableRow. Extracted into a memoized component that subscribes to
// photometry itself, so incoming photometry (e.g. at Argus alert rates) updates
// only the expanded panels and never forces the parent grid's columns to rebuild.
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
          justifyContent="center"
          alignItems="center"
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
                    className={classes.root}
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

interface SourceTableProps {
  sources: any[];
  title?: string;
  sourceStatus?: string;
  groupID?: number;
  paginateCallback: (...a: any[]) => any;
  pageNumber?: number;
  totalMatches?: number;
  numPerPage?: number;
  sortingCallback?: ((...a: any[]) => any) | null;
  downloadCallback?: ((...a: any[]) => any) | null;
  includeGcnStatus?: boolean;
  sourceInGcnFilter?: any;
  gcnEventDateobs?: string | null;
  fixedHeader?: boolean;
}

// Data grid with pull-out rows containing a summary of each source.
// This component is used in GroupSources, SourceList and Favorites page.
const SourceTable = ({
  sources,
  title = "Sources",
  sourceStatus = "saved",
  groupID,
  paginateCallback,
  pageNumber = 1,
  totalMatches = 0,
  numPerPage = 30,
  sortingCallback = null,
  downloadCallback = null,
  includeGcnStatus = false,
  sourceInGcnFilter = {},
  gcnEventDateobs = null,
  fixedHeader = false,
}: SourceTableProps) => {
  // sourceStatus should be one of either "saved" (default) or "requested" to add a button to agree to save the source.
  // If groupID is not given, show all data available to user's accessible groups

  const dispatch = useAppDispatch();
  const [acceptSaveRequest] = useAcceptSaveRequestMutation();
  const [declineSaveRequest] = useDeclineSaveRequestMutation();
  const [fetchPendingGroupSourcesTrigger] =
    useLazyFetchPendingGroupSourcesQuery();
  const [fetchSavedGroupSourcesTrigger] = useLazyFetchSavedGroupSourcesQuery();
  const { data: taxonomyList = [] } = useGetTaxonomiesQuery();

  const { classes } = useStyles() as { classes: any };

  const [searchBy, setSearchBy] = useState("name");
  const [searchText, setSearchText] = useState("");
  const [openNew, setOpenNew] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);

  const [openedRows, setOpenedRows] = useState<any[]>([]);
  const [sortModel, setSortModel] = useState<any[]>([]);

  const [filterFormSubmitted, setFilterFormSubmitted] = useState(false);
  const [tableFilterList, setTableFilterList] = useState<any[]>([]);
  const [filterFormData, setFilterFormData] = useState<any>(null);

  const [rowsPerPage, setRowsPerPage] = useState(numPerPage);
  const [loading, setLoading] = useState(false);

  const { data: gcnEvent } = useGetGcnEventQuery(gcnEventDateobs as string, {
    skip: !gcnEventDateobs,
  });
  const { data: sourcesingcn = [] } = useGetSourcesInGcnQuery(
    {
      dateobs: gcnEvent?.dateobs as string,
      localizationName: sourceInGcnFilter?.localizationName,
      sourcesIdList: sources?.map((s: any) => s.id),
    },
    { skip: !includeGcnStatus || !gcnEvent?.dateobs || !sources },
  );
  const { data: tagOptions = [] } = useGetTagOptionsQuery();

  // Columns hidden by default, keyed by DataGrid field. Mirrors the previous
  // defaultDisplayedColumns list (which only enumerated visible labels).
  const [columnVisibilityModel, setColumnVisibilityModel] = useState<
    Record<string, boolean>
  >(() => {
    const hidden = [
      "alias",
      "origin",
      "ra_sex",
      "dec_sex",
      "l",
      "b",
      "labelling",
      "saved_by",
      "peak_mag",
      "latest_mag",
      "mpc_name",
    ];
    if (!includeGcnStatus) {
      hidden.push("host", "host_offset");
    }
    return hidden.reduce((acc: Record<string, boolean>, field) => {
      acc[field] = false;
      return acc;
    }, {});
  });

  useEffect(() => {
    if (sources) {
      setLoading(false);
    }
  }, [sources]);

  useEffect(() => {
    const data = {
      ...filterFormData,
    };
    if (data?.sourceID?.length > 0 && searchBy === "comment") {
      data.commentsFilter = data.sourceID;
      delete data.sourceID;
      paginateCallback(1, rowsPerPage, {}, data);
      setFilterFormData(data);
    } else if (data?.commentsFilter?.length > 0 && searchBy === "name") {
      data.sourceID = data.commentsFilter;
      delete data.commentsFilter;
      paginateCallback(1, rowsPerPage, {}, data);
      setFilterFormData(data);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchBy]);

  const currentSortOrder = useCallback(
    () =>
      sortModel.length
        ? {
            name: SERVER_SORT_FIELD[sortModel[0].field] || sortModel[0].field,
            direction: sortModel[0].sort,
          }
        : {},
    [sortModel],
  );

  const handlePaginationModelChange = (model: any) => {
    setRowsPerPage(model.pageSize);
    setLoading(true);
    paginateCallback(
      model.page + 1,
      model.pageSize,
      currentSortOrder(),
      filterFormData,
    );
  };

  const handleSortModelChange = (model: any) => {
    setSortModel(model);
    setLoading(true);
    if (!model.length) {
      paginateCallback(1, rowsPerPage, {}, filterFormData);
      return;
    }
    const { field, sort } = model[0];
    sortingCallback?.(
      { name: SERVER_SORT_FIELD[field] || field, direction: sort },
      filterFormData,
    );
  };

  const handleSaveSource = async (sourceID: any) => {
    try {
      await acceptSaveRequest({ sourceID, groupID: groupID! }).unwrap();
      fetchPendingGroupSourcesTrigger({
        group_ids: [groupID],
        pageNumber: 1,
        numPerPage: 10,
      });
      fetchSavedGroupSourcesTrigger({
        group_ids: [groupID],
        pageNumber: 1,
        numPerPage: 10,
      });
    } catch {
      // error notification handled by the baseQuery
    }
  };

  const handleIgnoreSource = async (sourceID: any) => {
    try {
      await declineSaveRequest({ sourceID, groupID: groupID! }).unwrap();
      fetchPendingGroupSourcesTrigger({
        group_ids: [groupID],
        pageNumber: 1,
        numPerPage: 10,
      });
    } catch {
      // error notification handled by the baseQuery
    }
  };

  const toggleExpand = (id: any) => {
    setOpenedRows((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  // helper functions shared by renderers and CSV download
  const getGroups = (source: any) =>
    source.groups?.filter((group: any) => group.active);
  const navigate = useNavigate();

  const getDate = (source: any) => {
    if (!source.groups) {
      return undefined;
    }
    if (groupID !== undefined) {
      const group = source.groups.find((g: any) => g.id === groupID);
      return group?.saved_at;
    }
    const dates = source.groups.map((g: any) => g.saved_at).sort();
    return dates[dates.length - 1];
  };

  const getSavedBy = (source: any) => {
    if (!source.groups) {
      return undefined;
    }
    if (groupID !== undefined) {
      const group = source.groups.find((g: any) => g.id === groupID);
      return group?.saved_by?.username;
    }
    // `source.groups` is frozen RTK Query data, so copy before sorting in place.
    const usernames = [...source.groups]
      .sort((g1: any, g2: any) => (g1.saved_at < g2.saved_at ? -1 : 1))
      .map((g: any) => g.saved_by?.username);
    return usernames[usernames.length - 1];
  };

  // Build the DataGrid column definitions. Each renderCell receives the row
  // (the source object) directly, replacing mui-datatables' dataIndex lookups.
  const columns = useMemo(() => {
    const renderObjId = (params: any) => {
      const objid = params.row.id;
      return (
        <Link
          to={`/source/${objid}`}
          key={`${objid}_objid`}
          data-testid={`${objid}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <span className={classes.objId}>{objid}</span>
        </Link>
      );
    };

    const renderTNSName = (params: any) => {
      const source = params.row;
      if (source.tns_name) {
        return (
          <a
            key={source.tns_name}
            href={`https://www.wis-tns.org/object/${
              source.tns_name.trim().includes(" ")
                ? source.tns_name.split(" ")[1]
                : source.tns_name
            }`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ whiteSpace: "nowrap" }}
          >
            {`${source.tns_name} `}
          </a>
        );
      }
      return null;
    };

    const renderAlias = (params: any) => {
      const { id: objid, alias } = params.row;
      if (alias) {
        const alias_str = Array.isArray(alias)
          ? alias.map((name: any) => <div key={name}> {name} </div>)
          : alias;
        return (
          <Link to={`/source/${objid}`} key={`${objid}_alias`}>
            {alias_str}
          </Link>
        );
      }
      return null;
    };

    const renderOrigin = (params: any) => {
      const { id: objid, origin } = params.row;
      return (
        <Link to={`/source/${objid}`} key={`${objid}_origin`}>
          {origin}
        </Link>
      );
    };

    const renderRA = (params: any) => (
      <div key={`${params.row.id}_ra`}>{params.row.ra?.toFixed(6)}</div>
    );
    const renderRASex = (params: any) => (
      <div key={`${params.row.id}_ra_sex`}>{ra_to_hours(params.row.ra)}</div>
    );
    const renderDec = (params: any) => (
      <div key={`${params.row.id}_dec`}>{params.row.dec?.toFixed(6)}</div>
    );
    const renderDecSex = (params: any) => (
      <div key={`${params.row.id}_dec_sex`}>{dec_to_dms(params.row.dec)}</div>
    );
    const renderGalLon = (params: any) => (
      <div key={`${params.row.id}_gal_lon`}>
        {params.row.gal_lon?.toFixed(6)}
      </div>
    );
    const renderGalLat = (params: any) => (
      <div key={`${params.row.id}_gal_lat`}>
        {params.row.gal_lat?.toFixed(6)}
      </div>
    );
    const renderHost = (params: any) => (
      <div key={`${params.row.id}_host`}>{params.row.host?.name}</div>
    );
    const renderHostOffset = (params: any) => (
      <div key={`${params.row.id}_host_offset`}>
        {params.row.host_offset?.toFixed(3)}
      </div>
    );

    const renderClassification = (params: any) => (
      <Suspense
        fallback={
          <div>
            <CircularProgress color="secondary" />
          </div>
        }
      >
        <div>
          <RenderShowClassification source={params.row} />
        </div>
      </Suspense>
    );

    const renderPhotStats = (params: any) => (
      <Suspense
        fallback={
          <div>
            <CircularProgress color="secondary" />
          </div>
        }
      >
        <div>
          <DisplayPhotStats
            photstats={params.row.photstats?.[0]}
            display_header={false}
          />
        </div>
      </Suspense>
    );

    const renderLabelling = (params: any) => (
      <Suspense
        fallback={
          <div>
            <CircularProgress color="secondary" />
          </div>
        }
      >
        <div>
          <RenderShowLabelling source={params.row} />
        </div>
      </Suspense>
    );

    const renderGroups = (params: any) => {
      const source = params.row;
      return (
        <div key={`${source.id}_groups`} className={classes.groupChips}>
          {(getGroups(source) || []).map((group: any) => (
            <div key={group.name}>
              <Chip
                label={group.name.substring(0, 15)}
                key={group.id}
                size="small"
                onClick={() => navigate(`/group/${group.id}`)}
              />
              <br />
            </div>
          ))}
        </div>
      );
    };

    const renderDateSaved = (params: any) => (
      <div key={`${params.row.id}_date_saved`}>
        {getDate(params.row)?.substring(0, 19)}
      </div>
    );

    const renderFinderButton = (params: any) => (
      <IconButton size="small" key={`${params.row.id}_actions`}>
        <a href={`/api/sources/${params.row.id}/finder`}>
          <PictureAsPdfIcon />
        </a>
      </IconButton>
    );

    const renderSaveIgnore = (params: any) => {
      const source = params.row;
      return (
        <>
          <Button
            secondary
            size="small"
            onClick={() => {
              handleSaveSource(source.id);
            }}
            data-testid={`saveSourceButton_${source.id}`}
          >
            Save
          </Button>
          &nbsp;
          <Button
            secondary
            size="small"
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

    const renderPeakMagnitude = (params: any) => {
      const photstats = params.row.photstats?.[0];
      if (!photstats) {
        return <div>No photometry</div>;
      }
      return photstats.peak_mag_global ? (
        <Tooltip title={mjd_to_utc(photstats.peak_mjd_global)}>
          <div>{`${photstats.peak_mag_global.toFixed(4)}`}</div>
        </Tooltip>
      ) : (
        <div>No photometry</div>
      );
    };

    const renderLatestMagnitude = (params: any) => {
      const photstats = params.row.photstats?.[0];
      if (!photstats) {
        return <div>No photometry</div>;
      }
      return photstats.last_detected_mag ? (
        <Tooltip title={mjd_to_utc(photstats.last_detected_mjd)}>
          <div>{`${photstats.last_detected_mag.toFixed(4)}`}</div>
        </Tooltip>
      ) : (
        <div>No photometry</div>
      );
    };

    const renderMPCName = (params: any) => (
      <div>{params.row.mpc_name ? params.row.mpc_name : ""}</div>
    );

    const renderTags = (params: any) => {
      const source = params.row;
      const tags = source.tags || [];
      if (tags.length === 0) {
        return null;
      }
      const tagsWithColors = tags.map((tag: any) => {
        const tagOption = tagOptions.find(
          (option: any) => option.id === tag.objtagoption_id,
        );
        return {
          ...tag,
          color: tagOption?.color || "#dddfe2",
        };
      });
      return (
        <div key={`${source.id}_tags`} className={classes.groupChips}>
          {tagsWithColors.map((tag: any) => (
            <Chip
              key={tag.id}
              label={tag.name}
              size="small"
              style={{
                backgroundColor: tag.color,
                color: getContrastColor(tag.color),
              }}
            />
          ))}
        </div>
      );
    };

    const renderSavedBy = (params: any) => getSavedBy(params.row);

    const renderGcnStatus = (params: any) => {
      const source = params.row;
      let statusIcon = null;
      if (
        sourcesingcn.filter((s: any) => s.obj_id === source.id).length === 0
      ) {
        statusIcon = <PriorityHigh color="primary" />;
      } else if (
        sourcesingcn.filter((s: any) => s.obj_id === source.id)[0]
          ?.confirmed === true
      ) {
        statusIcon = <CheckIcon color={"green" as any} />;
      } else if (
        sourcesingcn.filter((s: any) => s.obj_id === source.id)[0]
          ?.confirmed === false
      ) {
        statusIcon = <ClearIcon color="secondary" />;
      } else {
        statusIcon = <QuestionMarkIcon color="primary" />;
      }
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "center",
          }}
          {...({ name: `${source.id}_gcn_status` } as any)}
        >
          {statusIcon}
          <ConfirmSourceInGCN
            dateobs={gcnEvent?.dateobs as string}
            localization_name={sourceInGcnFilter.localizationName}
            localization_cumprob={sourceInGcnFilter.localizationCumprob}
            source_id={source.id}
            start_date={sourceInGcnFilter.startDate}
            end_date={sourceInGcnFilter.endDate}
            sources_id_list={sources.map((s: any) => s.id)}
          />
        </div>
      );
    };

    const renderGcnStatusExplanation = (params: any) => {
      const source = params.row;
      let statusExplanation = null;
      if (
        sourcesingcn.filter((s: any) => s.obj_id === source.id).length === 0
      ) {
        statusExplanation = "";
      } else {
        statusExplanation =
          sourcesingcn.filter((s: any) => s.obj_id === source.id)[0]
            ?.explanation ?? "";
      }
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "center",
          }}
          {...({ name: `${source.id}_gcn_status_explanation` } as any)}
        >
          {statusExplanation}
        </div>
      );
    };

    const renderGcnNotes = (params: any) => {
      const source = params.row;
      let notes = "";
      if (sourcesingcn.filter((s: any) => s.obj_id === source.id).length) {
        notes =
          sourcesingcn.filter((s: any) => s.obj_id === source.id)[0]?.notes ??
          "";
      }
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {notes}
        </div>
      );
    };

    // Leading expand/detail column. For normal rows it renders the expand
    // toggle; for the synthetic detail rows it renders the pull-out panel,
    // spanning the full width of the grid via colSpan.
    const cols: any[] = [
      {
        field: "__expand",
        headerName: "",
        width: 56,
        sortable: false,
        filterable: false,
        hideable: false,
        disableColumnMenu: true,
        colSpan: (_value: any, row: any) => (row.__detail ? 100 : 1),
        renderCell: (params: any) => {
          if (params.row.__detail) {
            return (
              <SourceDetailPanel
                source={params.row.__source}
                groupID={groupID}
                taxonomyList={taxonomyList}
              />
            );
          }
          const expanded = openedRows.includes(params.row.id);
          return (
            <IconButton
              id="expandable-button"
              size="small"
              aria-label="expand row"
              onClick={() => toggleExpand(params.row.id)}
            >
              {expanded ? (
                <KeyboardArrowDownIcon />
              ) : (
                <KeyboardArrowRightIcon />
              )}
            </IconButton>
          );
        },
      },
      {
        field: "id",
        headerName: "Source ID",
        flex: 1,
        minWidth: 120,
        renderCell: renderObjId,
      },
      {
        field: "tns",
        headerName: "TNS",
        flex: 1,
        minWidth: 90,
        sortable: false,
        renderCell: renderTNSName,
      },
      {
        field: "alias",
        headerName: "Alias",
        flex: 1,
        minWidth: 90,
        renderCell: renderAlias,
      },
      {
        field: "origin",
        headerName: "Origin",
        flex: 1,
        minWidth: 90,
        renderCell: renderOrigin,
      },
      {
        field: "ra",
        headerName: "RA (deg)",
        flex: 1,
        minWidth: 100,
        renderCell: renderRA,
      },
      {
        field: "dec",
        headerName: "Dec (deg)",
        flex: 1,
        minWidth: 100,
        renderCell: renderDec,
      },
      {
        field: "ra_sex",
        headerName: "RA (hh:mm:ss)",
        flex: 1,
        minWidth: 120,
        renderCell: renderRASex,
      },
      {
        field: "dec_sex",
        headerName: "Dec (dd:mm:ss)",
        flex: 1,
        minWidth: 120,
        renderCell: renderDecSex,
      },
      {
        field: "l",
        headerName: "l (deg)",
        flex: 1,
        minWidth: 90,
        renderCell: renderGalLon,
      },
      {
        field: "b",
        headerName: "b (deg)",
        flex: 1,
        minWidth: 90,
        renderCell: renderGalLat,
      },
      {
        field: "redshift",
        headerName: "Redshift",
        flex: 1,
        minWidth: 90,
        valueGetter: (_value: any, row: any) => row.redshift,
      },
      {
        field: "tags",
        headerName: "Tags",
        flex: 1,
        minWidth: 120,
        maxWidth: 200,
        sortable: false,
        renderCell: renderTags,
      },
      {
        field: "classification",
        headerName: "Classification",
        flex: 1,
        minWidth: 120,
        maxWidth: 200,
        sortable: false,
        renderCell: renderClassification,
      },
      {
        field: "host",
        headerName: "Host",
        flex: 1,
        minWidth: 90,
        renderCell: renderHost,
      },
      {
        field: "host_offset",
        headerName: "Host Offset (arcsec)",
        flex: 1,
        minWidth: 120,
        renderCell: renderHostOffset,
      },
      {
        field: "photstats",
        headerName: " ",
        width: 80,
        sortable: false,
        renderCell: renderPhotStats,
      },
      {
        field: "labelling",
        headerName: "Labelling",
        flex: 1,
        minWidth: 120,
        renderCell: renderLabelling,
      },
      {
        field: "groups",
        headerName: "Groups",
        flex: 1,
        minWidth: 120,
        sortable: false,
        renderCell: renderGroups,
      },
      {
        field: "saved_at",
        headerName: "Saved at",
        flex: 1,
        minWidth: 150,
        renderCell: renderDateSaved,
      },
      {
        field: "saved_by",
        headerName: groupID ? "Saved To Group By" : "Last Saved By",
        flex: 1,
        minWidth: 120,
        sortable: false,
        renderCell: renderSavedBy,
      },
      {
        field: "peak_mag",
        headerName: "Peak Magnitude",
        flex: 1,
        minWidth: 120,
        sortable: false,
        renderCell: renderPeakMagnitude,
      },
      {
        field: "latest_mag",
        headerName: "Latest Magnitude",
        flex: 1,
        minWidth: 120,
        sortable: false,
        renderCell: renderLatestMagnitude,
      },
      {
        field: "mpc_name",
        headerName: "MPC Name",
        flex: 1,
        minWidth: 100,
        sortable: false,
        renderCell: renderMPCName,
      },
      {
        field: "favorites",
        headerName: " ",
        width: 80,
        sortable: false,
        renderCell: (params: any) => (
          <FavoritesButton sourceID={params.row.id} />
        ),
      },
      {
        field: "finder",
        headerName: "Finder",
        width: 80,
        sortable: false,
        renderCell: renderFinderButton,
      },
    ];

    if (includeGcnStatus) {
      // Insert GCN columns right after the classification column, matching the
      // previous splice positions.
      const insertAt = cols.findIndex((c) => c.field === "classification") + 1;
      cols.splice(
        insertAt,
        0,
        {
          field: "gcn_status",
          headerName: "GCN Status",
          flex: 1,
          minWidth: 110,
          renderCell: renderGcnStatus,
        },
        {
          field: "gcn_explanation",
          headerName: "Explanation",
          flex: 1,
          minWidth: 120,
          sortable: false,
          renderCell: renderGcnStatusExplanation,
        },
        {
          field: "gcn_notes",
          headerName: "Notes",
          flex: 1,
          minWidth: 120,
          sortable: false,
          renderCell: renderGcnNotes,
        },
      );
    }

    if (sourceStatus === "requested") {
      cols.push({
        field: "save_decline",
        headerName: "Save/Decline",
        flex: 1,
        minWidth: 140,
        sortable: false,
        renderCell: renderSaveIgnore,
      });
    }

    return cols;
  }, [
    classes,
    navigate,
    taxonomyList,
    tagOptions,
    sourcesingcn,
    gcnEvent,
    sourceInGcnFilter,
    sources,
    groupID,
    includeGcnStatus,
    sourceStatus,
    openedRows,
  ]);

  // Interleave a synthetic detail row after each expanded source. getRowHeight
  // returns "auto" for those rows so the pull-out content sizes itself.
  const displayRows = useMemo(() => {
    const out: any[] = [];
    (sources || []).forEach((source: any) => {
      out.push(source);
      if (openedRows.includes(source.id)) {
        out.push({
          id: `${source.id}__detail`,
          __detail: true,
          __source: source,
        });
      }
    });
    return out;
  }, [sources, openedRows]);

  const getRowHeight = useCallback(
    (params: any) => (params.model.__detail ? "auto" : null),
    [],
  );

  const handleSearchChange = (text: any) => {
    const data: any = {
      ...filterFormData,
    };
    if (searchBy === "name") {
      data.sourceID = text;
      delete data.commentsFilter;
    } else if (searchBy === "comment") {
      data.commentsFilter = text;
      delete data.sourceID;
    } else {
      dispatch(showNotification("Invalid searchBy parameter", "error"));
    }
    setLoading(true);
    paginateCallback(1, rowsPerPage, {}, data);
    setFilterFormData(data);
  };

  const handleFilterSubmit = async (formData: any) => {
    setLoading(true);
    // Remove empty position
    if (
      !formData.position.ra &&
      !formData.position.dec &&
      !formData.position.radius
    ) {
      delete formData.position;
    }

    const data: any = filterOutEmptyValues(formData);

    // the method above drops any empty or false params, but we make sure to keep requireDetections
    // if it is False, as it's default is to be True
    if (formData.requireDetections === false) {
      data.requireDetections = false;
    }

    setTableFilterList(
      Object.entries(data).map(([key, value]: [string, any]) => {
        if (key === "position") {
          return `position: ${value.ra} (RA), ${value.dec} (Dec), ${value.radius} (Radius)`;
        }
        return `${key}: ${value}`;
      }),
    );

    // Expand cone search params
    if ("position" in data) {
      data.ra = data.position.ra;
      data.dec = data.position.dec;
      data.radius = data.position.radius;
      delete data.position;
    }

    setFilterFormData(data);
    paginateCallback(1, rowsPerPage, {}, data);
    setFilterFormSubmitted(true);
    setFilterOpen(false);
  };

  const handleFilterChipDelete = (chip: any) => {
    const remaining = tableFilterList.filter((c) => c !== chip);
    const data: any = {};
    remaining.forEach((filterChip) => {
      const [key, value] = filterChip.split(": ");
      if (key === "position") {
        [data.ra, data.dec, data.radius] = value.split(/\s*\(\D*\),*\s*/);
      } else {
        data[key] = value;
      }
    });
    setTableFilterList(remaining);
    setFilterFormData(data);
    setLoading(true);
    paginateCallback(1, rowsPerPage, {}, data);
  };

  const handleClose = () => {
    setOpenNew(false);
  };

  const handleDownload = () => {
    const renderDownloadClassification = (source: any) =>
      (source?.classifications || [])
        .map((x: any) => x.classification)
        .join(";");
    const renderDownloadProbability = (source: any) =>
      (source?.classifications || []).map((x: any) => x.probability).join(";");
    const renderDownloadAnnotationKey = (source: any) => {
      const annotationKeys: any[] = [];
      source?.annotations.forEach((x: any) => {
        Object.entries(x.data).forEach((keyValuePair) => {
          annotationKeys.push(keyValuePair[0]);
        });
      });
      return annotationKeys.join(";");
    };
    const renderDownloadAnnotationOrigin = (source: any) =>
      (source?.annotations || []).map((x: any) => x.origin).join(";");
    const renderDownloadAnnotationOriginKeyValuePairCount = (source: any) =>
      (source?.annotations || [])
        .map((x: any) => Object.entries(x.data).length)
        .join(";");
    const renderDownloadAnnotationValue = (source: any) => {
      const annotationValues: any[] = [];
      source?.annotations.forEach((x: any) => {
        Object.entries(x.data).forEach((keyValuePair) => {
          annotationValues.push(keyValuePair[1]);
        });
      });
      return annotationValues.join(";");
    };
    const renderDownloadGroups = (source: any) =>
      (source?.groups || []).map((x: any) => x.name).join(";");
    const renderDownloadDateSaved = (source: any) =>
      getDate(source)?.substring(0, 19);
    const renderDownloadAlias = (source: any) => {
      const { alias } = source || {};
      if (alias) {
        return Array.isArray(alias) ? alias.join(";") : alias;
      }
      return "";
    };
    const renderDownloadTNSName = (source: any) => source?.tns_name || "";

    downloadCallback?.().then((data: any) => {
      if (!data?.length) {
        return;
      }
      const head = [
        "id",
        "ra [deg]",
        "dec [deg]",
        "redshift",
        "classification",
        "probability",
        "annotation origin",
        "annotation origin key-value pair count",
        "annotation key",
        "annotation value",
        "groups",
        "Saved at",
        "Alias",
        "Origin",
        "TNS",
      ];
      if (includeGcnStatus) {
        head.push("GCN Status", "Explanation", "Notes");
      }

      const csvCell = (value: any) =>
        `"${String(value ?? "").replace(/"/g, '""')}"`;

      const rows = data.map((x: any) => {
        const cells = [
          x.id,
          x.ra,
          x.dec,
          x.redshift,
          renderDownloadClassification(x),
          renderDownloadProbability(x),
          renderDownloadAnnotationOrigin(x),
          renderDownloadAnnotationOriginKeyValuePairCount(x),
          renderDownloadAnnotationKey(x),
          renderDownloadAnnotationValue(x),
          renderDownloadGroups(x),
          renderDownloadDateSaved(x),
          renderDownloadAlias(x),
          x.origin,
          renderDownloadTNSName(x),
        ];
        if (includeGcnStatus) {
          cells.push(
            x.gcn ? x.gcn.status : "",
            x.gcn ? x.gcn.explanation : "",
            x.gcn ? x.gcn.notes : "",
          );
        }
        return cells.map(csvCell).join(",");
      });

      const result = `${head.map(csvCell).join(",")}\n${rows.join("\n")}`;
      const blob = new Blob([result], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "sources.csv");
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    });
  };

  const showDownload =
    downloadCallback !== null && downloadCallback !== undefined;

  const CustomToolbar = useMemo(
    () =>
      function SourceTableToolbar() {
        return (
          <DataGridToolbar showQuickFilter={false}>
            <Tooltip title="Filter Table">
              <IconButton
                size="small"
                data-testid="Filter Table-iconButton"
                onClick={() => {
                  setFilterFormSubmitted(false);
                  setFilterOpen(true);
                }}
              >
                <FilterListIcon />
              </IconButton>
            </Tooltip>
            <Select
              label="Search by"
              variant="standard"
              value={searchBy}
              onChange={(event) => setSearchBy(event.target.value)}
              style={{ marginLeft: "10px" }}
              size="small"
            >
              <MenuItem value="name">ID/IAU</MenuItem>
              <MenuItem value="comment">Comment</MenuItem>
            </Select>
            <TextField
              variant="standard"
              size="small"
              placeholder="Search"
              value={searchText}
              onChange={(event) => {
                setSearchText(event.target.value);
                handleSearchChange(event.target.value);
              }}
            />
            <IconButton
              name="new_source"
              size="small"
              onClick={() => setOpenNew(true)}
            >
              <AddIcon />
            </IconButton>
            {showDownload && (
              <Tooltip title="Download CSV">
                <IconButton
                  size="small"
                  aria-label="Download CSV"
                  data-testid="download-sources-button"
                  onClick={handleDownload}
                >
                  <DownloadIcon />
                </IconButton>
              </Tooltip>
            )}
          </DataGridToolbar>
        );
      },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [searchBy, searchText, showDownload],
  );

  return (
    <div className={classes.source} data-testid={`source_table_${title}`}>
      <div>
        <Grid
          container
          direction="column"
          alignItems="flex-start"
          justifyContent="flex-start"
          spacing={3}
        >
          <Grid className={classes.tableGrid}>
            {title && (
              <Typography variant="h6" style={{ marginBottom: "0.5rem" }}>
                {title}
              </Typography>
            )}
            {tableFilterList.length > 0 && (
              <div className={classes.filterChips}>
                {tableFilterList.map((chip) => (
                  <Chip
                    key={chip}
                    label={chip}
                    size="small"
                    onDelete={() => handleFilterChipDelete(chip)}
                  />
                ))}
              </div>
            )}
            <Box
              sx={{
                height: fixedHeader ? "calc(100vh - 201px)" : "65vh",
                width: "100%",
              }}
            >
              <StyledDataGrid
                rows={displayRows}
                columns={columns}
                loading={loading}
                getRowHeight={getRowHeight}
                columnVisibilityModel={columnVisibilityModel}
                onColumnVisibilityModelChange={setColumnVisibilityModel}
                paginationMode="server"
                sortingMode="server"
                rowCount={totalMatches}
                paginationModel={{
                  page: pageNumber - 1,
                  pageSize: rowsPerPage,
                }}
                onPaginationModelChange={handlePaginationModelChange}
                sortModel={sortModel}
                onSortModelChange={handleSortModelChange}
                pageSizeOptions={PAGE_SIZE_OPTIONS}
                disableColumnFilter
                // Keep all columns mounted so colSpan on the detail row works;
                // row virtualization stays on, which is the performance win.
                columnBufferPx={3000}
                slots={{ toolbar: CustomToolbar }}
                showToolbar
              />
            </Box>
          </Grid>
        </Grid>
      </div>
      <Dialog open={filterOpen} onClose={() => setFilterOpen(false)} fullWidth>
        <DialogContent>
          {filterFormSubmitted ? (
            <div className={classes.filterAlert}>
              <InfoIcon /> &nbsp; Filters submitted to server!
            </div>
          ) : (
            <SourceTableFilterForm handleFilterSubmit={handleFilterSubmit} />
          )}
        </DialogContent>
      </Dialog>
      <div>
        {openNew && (
          <Dialog open={openNew} onClose={handleClose} maxWidth="md">
            <DialogContent dividers>
              <NewSource onClose={handleClose} />
            </DialogContent>
          </Dialog>
        )}
      </div>
    </div>
  );
};

export default SourceTable;
