import {
  useGetProfileQuery,
  useIsReadOnly,
  useUpdateUserPreferencesMutation,
} from "../../ducks/profile";
import React, {
  Suspense,
  useEffect,
  useState,
  useMemo,
  useCallback,
  useRef,
} from "react";
import { Link, useNavigate } from "react-router-dom";

import IconButton from "@mui/material/IconButton";
import FormControlLabel from "@mui/material/FormControlLabel";
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
import Divider from "@mui/material/Divider";
import TextField from "@mui/material/TextField";
import Box from "@mui/material/Box";
import InputAdornment from "@mui/material/InputAdornment";
import Popover from "@mui/material/Popover";
import Checkbox from "@mui/material/Checkbox";
import CheckIcon from "@mui/icons-material/Check";
import ClearIcon from "@mui/icons-material/Clear";
import InfoIcon from "@mui/icons-material/Info";
import QuestionMarkIcon from "@mui/icons-material/QuestionMark";
import PriorityHigh from "@mui/icons-material/PriorityHigh";
import PlaylistAddIcon from "@mui/icons-material/PlaylistAdd";
import SearchIcon from "@mui/icons-material/Search";
import CircularProgress from "@mui/material/CircularProgress";
import Tooltip from "@mui/material/Tooltip";
import SearchableSelect from "../SearchableSelect";
import { showNotification } from "baselayer/components/Notifications";
import { useAppDispatch } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid, {
  DataGridToolbar,
  FULL_PAGE_HEIGHT,
} from "../StyledDataGrid";
import ExpandableCell from "../ExpandableCell";
import DisplayPhotStats from "./DisplayPhotStats";

import { dec_to_dms, mjd_to_utc, ra_to_hours } from "../../units";
import ShowClassification from "../classification/ShowClassification";
import FavoritesButton from "../listing/FavoritesButton";
import {
  useDeleteClassificationsMutation,
  useAddClassificationVoteMutation,
  useAddSourceLabelsMutation,
  useDeleteSourceLabelsMutation,
  useAcceptSaveRequestMutation,
  useDeclineSaveRequestMutation,
} from "../../ducks/source";
import { useGetAltdataInfoQuery } from "../../ducks/sources";
import { useGetSourcesInGcnQuery } from "../../ducks/sourcesingcn";
import { useGetGcnEventQuery } from "../../ducks/gcnEvent";
import { useGetTagOptionsQuery } from "../../ducks/objectTags";
import { useGetTaxonomiesQuery } from "../../ducks/taxonomies";
import { useGetAnnotationsInfoQuery } from "../../ducks/candidate/candidates";
import { getContrastColor } from "../ObjectTags";
import { filterOutEmptyValues } from "../../API";
import useDebounced from "../../hooks/useDebounced";
import { getAnnotationValueString } from "../candidate/ScanningPageCandidateAnnotations";
import {
  altdataKeyForField,
  buildAltdataColumnMeta,
  buildAnnotationColumnMeta,
  buildColumnPickerOptions,
  filterColumnPickerOptions,
  originKeyForAnnotationField,
} from "./sourceTableColumns";
import ConfirmSourceInGCN from "./ConfirmSourceInGCN";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

const SourceDetailPanel = React.lazy(() => import("./SourceDetailPanel"));
const SourceTableFilterForm = React.lazy(
  () => import("./SourceTableFilterForm"),
);
const NewSource = React.lazy(() => import("./NewSource"));

// Inline `= []` defaults would invalidate the `columns` memo every render.
const EMPTY_ARRAY: any[] = [];
const EMPTY_OBJECT: Record<string, any> = {};

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

const RenderShowClassification = React.memo(({ source }: { source: any }) => {
  const dispatch = useAppDispatch();
  const [deleteClassificationsMutation] = useDeleteClassificationsMutation();
  const [addClassificationVote] = useAddClassificationVoteMutation();
  const { data: currentUser } = useGetProfileQuery();
  const { data: taxonomyList = [] } = useGetTaxonomiesQuery();
  const [dialogOpen, setDialogOpen] = useState(false);

  const deleteClassifications = async () => {
    try {
      await deleteClassificationsMutation(source.id).unwrap();
      dispatch(showNotification("Classification deleted"));
      setDialogOpen(false);
    } catch {
      // error notification handled by the baseQuery
    }
  };

  const addVotes = (vote: number) => {
    source.classifications?.forEach((c: any) =>
      addClassificationVote({ classification_id: c.id, data: { vote } }),
    );
    dispatch(showNotification("Votes registered"));
  };

  const votedAll = (vote: number) =>
    source.classifications?.every((c: any) =>
      c.votes?.some(
        (v: any) => v.voter_id === currentUser?.id && v.vote === vote,
      ),
    );
  const upvoted = votedAll(1);
  const downvoted = !upvoted && votedAll(-1);

  const permission =
    currentUser?.permissions.includes("System admin") ||
    currentUser?.permissions.includes("Manage groups") ||
    JSON.parse(window.localStorage.getItem("CURRENT_GROUP_ADMIN") as any);

  return (
    <Tooltip
      placement="top-end"
      disableFocusListener
      disableTouchListener
      title={
        <Box sx={{ display: "flex", flexDirection: "column", pt: 2 }}>
          <b>All Classifications:</b>
          <Button
            id="delete_classifications"
            onClick={() => setDialogOpen(true)}
            disabled={!permission}
            sx={{
              fontSize: "2em",
              position: "absolute",
              p: 0,
              right: 0,
              top: 0,
              "&.Mui-disabled": { opacity: 0 },
            }}
          >
            <DeleteIcon />
          </Button>
          <ConfirmDeletionDialog
            deleteFunction={deleteClassifications}
            dialogOpen={dialogOpen}
            closeDialog={() => setDialogOpen(false)}
            resourceName="classifications"
          />
          <Button id="down_vote" onClick={() => addVotes(downvoted ? 0 : -1)}>
            <ThumbDown color={downvoted ? "error" : "disabled"} />
          </Button>
          <Button id="up_vote" onClick={() => addVotes(upvoted ? 0 : 1)}>
            <ThumbUp color={upvoted ? "success" : "disabled"} />
          </Button>
        </Box>
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
  );
});
RenderShowClassification.displayName = "RenderShowClassification";

const RenderShowLabelling = React.memo(({ source }: { source: any }) => {
  const [addSourceLabels] = useAddSourceLabelsMutation();
  const [deleteSourceLabels] = useDeleteSourceLabelsMutation();
  const { data: currentUser } = useGetProfileQuery();
  const labellerUsernames = (source.labellers ?? []).map(
    (s: any) => s.username,
  );
  const defaultChecked = labellerUsernames.includes(currentUser?.username);
  const [checked, setChecked] = useState(defaultChecked);

  useEffect(() => setChecked(defaultChecked), [defaultChecked]);

  const toggleLabelled = (check: boolean) => {
    setChecked(check);
    const data = { groupIds: (source.groups ?? []).map((g: any) => g.id) };
    if (check) addSourceLabels({ id: source.id, data });
    else deleteSourceLabels({ id: source.id, data });
  };

  return (
    <FormControlLabel
      control={
        <Checkbox
          checked={checked}
          onChange={(event) => toggleLabelled(event.target.checked)}
        />
      }
      label={`Labelled By:  ${labellerUsernames.join(",")}`}
    />
  );
});
RenderShowLabelling.displayName = "RenderShowLabelling";

// Module scope: defined inside the table it remounts the search input and drops focus.
const SourceTableToolbar = ({
  title,
  searchBy,
  searchText,
  onSearchByChange,
  onSearchTextChange,
  onOpenFilter,
  onNewSource,
  onDownload,
  columnPickerOptions,
  onAddColumn,
}: any) => {
  const [columnAnchor, setColumnAnchor] = useState<HTMLElement | null>(null);

  return (
    <DataGridToolbar
      title={title}
      showExport={false}
      showQuickFilter={false}
      showExpandAll
    >
      {columnPickerOptions.length > 0 && (
        <>
          <Tooltip title="Add an annotation or altdata column">
            <IconButton
              size="small"
              aria-label="Add column"
              data-testid="add-column-button"
              onClick={(event) => setColumnAnchor(event.currentTarget)}
            >
              <PlaylistAddIcon />
            </IconButton>
          </Tooltip>
          <Popover
            open={Boolean(columnAnchor)}
            anchorEl={columnAnchor}
            onClose={() => setColumnAnchor(null)}
            anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
          >
            <Box sx={{ padding: "0.75rem", width: "22rem" }}>
              <SearchableSelect
                options={columnPickerOptions}
                getOptionLabel={(o: any) => o.label}
                filterOptions={(opts: any, state: any) =>
                  filterColumnPickerOptions(opts, state.inputValue)
                }
                onChange={(_e: any, value: any) => {
                  if (!value) return;
                  onAddColumn(value.field);
                  setColumnAnchor(null);
                }}
                value={null}
                blurOnSelect
                clearOnBlur
                label="Add a column"
                placeholder="annotation or altdata field…"
                textFieldProps={{
                  autoFocus: true,
                  "data-testid": "add-column-picker",
                }}
              />
            </Box>
          </Popover>
        </>
      )}
      <Tooltip title="Filter Table">
        <IconButton
          size="small"
          data-testid="Filter Table-iconButton"
          onClick={onOpenFilter}
        >
          <FilterListIcon />
        </IconButton>
      </Tooltip>
      {onNewSource && (
        <Tooltip title="Add a source">
          <IconButton name="new_source" size="small" onClick={onNewSource}>
            <AddIcon />
          </IconButton>
        </Tooltip>
      )}
      {onDownload && (
        <Tooltip title="Download CSV">
          <IconButton
            size="small"
            aria-label="Download CSV"
            onClick={onDownload}
          >
            <DownloadIcon />
          </IconButton>
        </Tooltip>
      )}
      <TextField
        size="small"
        placeholder="Search"
        value={searchText}
        onChange={(event) => onSearchTextChange(event.target.value)}
        sx={{ width: "20rem" }}
        slotProps={{
          input: {
            startAdornment: (
              <InputAdornment position="start" sx={{ marginRight: 0 }}>
                <SearchIcon fontSize="small" sx={{ marginRight: "0.25rem" }} />
                <Select
                  variant="standard"
                  disableUnderline
                  value={searchBy}
                  onChange={(event) => onSearchByChange(event.target.value)}
                  sx={{
                    fontSize: "0.875rem",
                    "& .MuiSelect-select": { paddingY: 0 },
                  }}
                >
                  <MenuItem value="name">ID/IAU</MenuItem>
                  <MenuItem value="comment">Comment</MenuItem>
                </Select>
                <Divider
                  orientation="vertical"
                  flexItem
                  sx={{ marginX: "0.5rem", marginY: "0.25rem" }}
                />
              </InputAdornment>
            ),
            endAdornment: searchText ? (
              <InputAdornment position="end">
                <IconButton
                  size="small"
                  aria-label="Clear search"
                  onClick={() => onSearchTextChange("")}
                >
                  <ClearIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ) : null,
          },
        }}
      />
    </DataGridToolbar>
  );
};

const TOOLBAR_SLOT = { toolbar: SourceTableToolbar };

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
  isLoading?: boolean;
}

const SourceTable = ({
  sources,
  title = "Sources",
  sourceStatus = "saved",
  groupID,
  paginateCallback,
  pageNumber = 1,
  totalMatches = 0,
  numPerPage = 25,
  sortingCallback = null,
  downloadCallback = null,
  includeGcnStatus = false,
  sourceInGcnFilter = EMPTY_OBJECT,
  gcnEventDateobs = null,
  fixedHeader = false,
  isLoading = false,
}: SourceTableProps) => {
  const [acceptSaveRequest] = useAcceptSaveRequestMutation();
  const [declineSaveRequest] = useDeclineSaveRequestMutation();
  const { data: taxonomyList = EMPTY_ARRAY } = useGetTaxonomiesQuery();

  const isReadOnly = useIsReadOnly();
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
  const { data: sourcesingcn = EMPTY_ARRAY } = useGetSourcesInGcnQuery(
    {
      dateobs: gcnEvent?.dateobs as string,
      sourcesIDList: sources?.map((s: any) => s.id),
    },
    { skip: !includeGcnStatus || !gcnEvent?.dateobs || !sources },
  );
  const { data: tagOptions = EMPTY_ARRAY } = useGetTagOptionsQuery();
  const { data: annotationsInfo } = useGetAnnotationsInfoQuery(undefined);
  const { data: altdataInfo } = useGetAltdataInfoQuery();
  const { data: currentUser } = useGetProfileQuery();
  const [updateUserPreferences] = useUpdateUserPreferencesMutation();
  const savedAnnotationColumns: string[] = useMemo(
    () => (currentUser?.preferences as any)?.sourceTableAnnotationColumns || [],
    [currentUser],
  );
  const savedAltdataColumns: string[] = useMemo(
    () => (currentUser?.preferences as any)?.sourceTableAltdataColumns || [],
    [currentUser],
  );

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

  const annotationColumnMeta = useMemo(
    () => buildAnnotationColumnMeta(annotationsInfo),
    [annotationsInfo],
  );
  const altdataColumnMeta = useMemo(
    () => buildAltdataColumnMeta(altdataInfo),
    [altdataInfo],
  );

  const columnPickerOptions = useMemo(
    () => buildColumnPickerOptions(annotationColumnMeta, altdataColumnMeta),
    [annotationColumnMeta, altdataColumnMeta],
  );

  const handleAddColumn = useCallback(
    (field: string) => {
      if (!field) return;
      if (field.startsWith("annotation.")) {
        if (savedAnnotationColumns.includes(field)) return;
        updateUserPreferences({
          sourceTableAnnotationColumns: [...savedAnnotationColumns, field],
        });
      } else if (field.startsWith("altdata.")) {
        if (savedAltdataColumns.includes(field)) return;
        updateUserPreferences({
          sourceTableAltdataColumns: [...savedAltdataColumns, field],
        });
      }
    },
    [savedAnnotationColumns, savedAltdataColumns, updateUserPreferences],
  );

  const handleColumnVisibilityModelChange = useCallback(
    (model: Record<string, boolean>) => {
      setColumnVisibilityModel(model);
      const prefs: Record<string, string[]> = {};
      const visibleAnnotation = savedAnnotationColumns.filter(
        (f) => model[f] !== false,
      );
      if (visibleAnnotation.length !== savedAnnotationColumns.length) {
        prefs["sourceTableAnnotationColumns"] = visibleAnnotation;
      }
      const visibleAltdata = savedAltdataColumns.filter(
        (f) => model[f] !== false,
      );
      if (visibleAltdata.length !== savedAltdataColumns.length) {
        prefs["sourceTableAltdataColumns"] = visibleAltdata;
      }
      if (Object.keys(prefs).length > 0) {
        updateUserPreferences(prefs);
      }
    },
    [savedAnnotationColumns, savedAltdataColumns, updateUserPreferences],
  );

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

  const debouncedSearchText = useDebounced(searchText, 400);
  const appliedSearchText = useRef("");
  useEffect(() => {
    if (debouncedSearchText === appliedSearchText.current) return;
    appliedSearchText.current = debouncedSearchText;
    const data: any = { ...filterFormData };
    if (searchBy === "name") {
      data.sourceID = debouncedSearchText;
      delete data.commentsFilter;
    } else {
      data.commentsFilter = debouncedSearchText;
      delete data.sourceID;
    }
    setLoading(true);
    paginateCallback(1, rowsPerPage, {}, data);
    setFilterFormData(data);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearchText]);

  const currentSortOrder = () =>
    sortModel.length
      ? {
          name: SERVER_SORT_FIELD[sortModel[0].field] || sortModel[0].field,
          direction: sortModel[0].sort,
        }
      : {};

  const handlePaginationModelChange = (model: any) => {
    // The grid also emits this when clamping the page; refetching on no-ops loops.
    if (model.page === pageNumber - 1 && model.pageSize === rowsPerPage) {
      return;
    }
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

  const toggleExpand = (id: any) => {
    setOpenedRows((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const navigate = useNavigate();

  const savedGroup = (source: any) =>
    groupID !== undefined
      ? source.groups?.find((g: any) => g.id === groupID)
      : // `source.groups` is frozen RTK Query data, so copy before sorting in place.
        [...(source.groups ?? [])]
          .sort((g1: any, g2: any) => (g1.saved_at < g2.saved_at ? -1 : 1))
          .pop();
  const getDate = (source: any) =>
    savedGroup(source)?.saved_at?.substring(0, 19);

  const columns = useMemo(() => {
    const sourceInGcn = (source: any) =>
      sourcesingcn.find((s: any) => s.obj_id === source.id);

    const renderMagnitude = (row: any, magKey: string, mjdKey: string) => {
      const photstats = row.photstats?.[0];
      if (!photstats?.[magKey]) return "No photometry";
      return (
        <Tooltip title={mjd_to_utc(photstats[mjdKey])}>
          <div>{photstats[magKey].toFixed(4)}</div>
        </Tooltip>
      );
    };

    const renderGcnStatus = ({ row }: any) => {
      const inGcn = sourceInGcn(row);
      let statusIcon = <QuestionMarkIcon color="primary" />;
      if (!inGcn) statusIcon = <PriorityHigh color="primary" />;
      else if (inGcn.status === "confirmed")
        statusIcon = <CheckIcon color={"green" as any} />;
      else if (inGcn.status === "rejected")
        statusIcon = <ClearIcon color="secondary" />;
      return (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {statusIcon}
          <ConfirmSourceInGCN
            dateobs={gcnEvent?.dateobs as string}
            localization_name={sourceInGcnFilter.localizationName}
            localization_cumprob={sourceInGcnFilter.localizationCumprob}
            source_id={row.id}
            start_date={sourceInGcnFilter.startDate}
            end_date={sourceInGcnFilter.endDate}
            sources_id_list={sources.map((s: any) => s.id)}
          />
        </Box>
      );
    };

    const cols: any[] = [
      {
        field: "__expand",
        headerName: "",
        width: 64,
        sortable: false,
        filterable: false,
        hideable: false,
        disableColumnMenu: true,
        colSpan: (_value: any, row: any) => (row.__detail ? 100 : 1),
        renderCell: (params: any) => {
          if (params.row.__detail) {
            return (
              <Suspense fallback={<CircularProgress color="secondary" />}>
                <SourceDetailPanel
                  source={params.row.__source}
                  groupID={groupID}
                  taxonomyList={taxonomyList}
                />
              </Suspense>
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
        minWidth: 120,
        renderCell: ({ value }: any) => (
          <Link
            to={`/source/${value}`}
            data-testid={value}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Box
              component="span"
              sx={(theme) => ({
                color:
                  theme.palette.mode === "dark"
                    ? theme.palette.secondary.main
                    : theme.palette.primary.main,
              })}
            >
              {value}
            </Box>
          </Link>
        ),
      },
      {
        field: "tns",
        headerName: "TNS",
        minWidth: 90,
        sortable: false,
        renderCell: ({ row }: any) =>
          row.tns_name && (
            <Box
              component="a"
              href={`https://www.wis-tns.org/object/${
                row.tns_name.trim().includes(" ")
                  ? row.tns_name.split(" ")[1]
                  : row.tns_name
              }`}
              target="_blank"
              rel="noopener noreferrer"
              sx={{ whiteSpace: "nowrap" }}
            >
              {row.tns_name}
            </Box>
          ),
      },
      {
        field: "alias",
        headerName: "Alias",
        minWidth: 90,
        renderCell: ({ row }: any) =>
          row.alias && (
            <Link to={`/source/${row.id}`}>
              {Array.isArray(row.alias)
                ? row.alias.map((name: any) => <div key={name}>{name}</div>)
                : row.alias}
            </Link>
          ),
      },
      {
        field: "origin",
        headerName: "Origin",
        minWidth: 90,
        renderCell: ({ row }: any) => (
          <Link to={`/source/${row.id}`}>{row.origin}</Link>
        ),
      },
      {
        field: "ra",
        headerName: "RA (deg)",
        minWidth: 100,
        valueFormatter: (value: number) => value?.toFixed(6),
      },
      {
        field: "dec",
        headerName: "Dec (deg)",
        minWidth: 100,
        valueFormatter: (value: number) => value?.toFixed(6),
      },
      {
        field: "ra_sex",
        headerName: "RA (hh:mm:ss)",
        minWidth: 120,
        valueGetter: (_value: any, row: any) => ra_to_hours(row.ra),
      },
      {
        field: "dec_sex",
        headerName: "Dec (dd:mm:ss)",
        minWidth: 120,
        valueGetter: (_value: any, row: any) => dec_to_dms(row.dec),
      },
      {
        field: "l",
        headerName: "l (deg)",
        minWidth: 90,
        valueGetter: (_value: any, row: any) => row.gal_lon?.toFixed(6),
      },
      {
        field: "b",
        headerName: "b (deg)",
        minWidth: 90,
        valueGetter: (_value: any, row: any) => row.gal_lat?.toFixed(6),
      },
      { field: "redshift", headerName: "Redshift", minWidth: 90 },
      {
        field: "tags",
        headerName: "Tags",
        minWidth: 120,
        maxWidth: 200,
        sortable: false,
        renderCell: ({ row }: any) => (
          <ExpandableCell
            items={(row.tags ?? []).map((tag: any) => {
              const color =
                tagOptions.find((o: any) => o.id === tag.objtagoption_id)
                  ?.color || "#dddfe2";
              return (
                <Chip
                  key={tag.id}
                  label={tag.name}
                  size="small"
                  sx={{ bgcolor: color, color: getContrastColor(color) }}
                />
              );
            })}
          />
        ),
      },
      {
        field: "classification",
        headerName: "Classification",
        minWidth: 120,
        maxWidth: 200,
        sortable: false,
        renderCell: ({ row }: any) => <RenderShowClassification source={row} />,
      },
      {
        field: "host",
        headerName: "Host",
        minWidth: 90,
        valueGetter: (_value: any, row: any) => row.host?.name,
      },
      {
        field: "host_offset",
        headerName: "Host Offset (arcsec)",
        minWidth: 120,
        valueFormatter: (value: number) => value?.toFixed(3),
      },
      {
        field: "photstats",
        headerName: " ",
        width: 80,
        sortable: false,
        renderCell: ({ row }: any) => (
          <DisplayPhotStats photstats={row.photstats?.[0]} />
        ),
      },
      {
        field: "labelling",
        headerName: "Labelling",
        minWidth: 120,
        renderCell: ({ row }: any) => <RenderShowLabelling source={row} />,
      },
      {
        field: "groups",
        headerName: "Groups",
        minWidth: 120,
        sortable: false,
        renderCell: ({ row }: any) => (
          <ExpandableCell
            items={(row.groups ?? [])
              .filter((group: any) => group.active)
              .map((group: any) => (
                <Chip
                  label={group.name.substring(0, 15)}
                  key={group.id}
                  size="small"
                  onClick={() => navigate(`/group/${group.id}`)}
                />
              ))}
          />
        ),
      },
      {
        field: "saved_at",
        headerName: "Saved at",
        minWidth: 150,
        valueGetter: (_value: any, row: any) => getDate(row),
      },
      {
        field: "saved_by",
        headerName: groupID ? "Saved To Group By" : "Last Saved By",
        minWidth: 120,
        sortable: false,
        valueGetter: (_value: any, row: any) =>
          savedGroup(row)?.saved_by?.username,
      },
      {
        field: "peak_mag",
        headerName: "Peak Magnitude",
        minWidth: 120,
        sortable: false,
        renderCell: ({ row }: any) =>
          renderMagnitude(row, "peak_mag_global", "peak_mjd_global"),
      },
      {
        field: "latest_mag",
        headerName: "Latest Magnitude",
        minWidth: 120,
        sortable: false,
        renderCell: ({ row }: any) =>
          renderMagnitude(row, "last_detected_mag", "last_detected_mjd"),
      },
      {
        field: "mpc_name",
        headerName: "MPC Name",
        minWidth: 100,
        sortable: false,
      },
      {
        field: "favorites",
        headerName: " ",
        width: 80,
        sortable: false,
        renderCell: ({ row }: any) => <FavoritesButton sourceID={row.id} />,
      },
      {
        field: "finder",
        headerName: "Finder",
        width: 80,
        sortable: false,
        renderCell: ({ row }: any) => (
          <IconButton size="small" href={`/api/sources/${row.id}/finder`}>
            <PictureAsPdfIcon />
          </IconButton>
        ),
      },
    ];

    if (includeGcnStatus) {
      const insertAt = cols.findIndex((c) => c.field === "classification") + 1;
      cols.splice(
        insertAt,
        0,
        {
          field: "gcn_status",
          headerName: "GCN Status",
          minWidth: 110,
          renderCell: renderGcnStatus,
        },
        {
          field: "gcn_explanation",
          headerName: "Explanation",
          minWidth: 120,
          sortable: false,
          align: "center",
          valueGetter: (_value: any, row: any) => sourceInGcn(row)?.explanation,
        },
        {
          field: "gcn_notes",
          headerName: "Notes",
          minWidth: 120,
          sortable: false,
          align: "center",
          valueGetter: (_value: any, row: any) => sourceInGcn(row)?.notes,
        },
      );
    }

    if (sourceStatus === "requested") {
      cols.push({
        field: "save_decline",
        headerName: "Save/Decline",
        minWidth: 140,
        sortable: false,
        renderCell: ({ row }: any) => (
          <Box sx={{ display: "flex", gap: 0.5 }}>
            <Button
              secondary
              size="small"
              onClick={() =>
                acceptSaveRequest({ sourceID: row.id, groupID: groupID! })
              }
              data-testid={`saveSourceButton_${row.id}`}
            >
              Save
            </Button>
            <Button
              secondary
              size="small"
              onClick={() =>
                declineSaveRequest({ sourceID: row.id, groupID: groupID! })
              }
            >
              Ignore
            </Button>
          </Box>
        ),
      });
    }

    savedAnnotationColumns.forEach((field) => {
      const { origin, key } = originKeyForAnnotationField(
        field,
        annotationColumnMeta,
      );
      cols.push({
        field,
        headerName: `${key} (${origin})`,
        minWidth: 120,
        valueGetter: (_value: any, row: any) => {
          const ann = (row.annotations || []).find(
            (a: any) => a.origin === origin,
          );
          const value = ann?.data?.[key];
          return value === undefined ? null : getAnnotationValueString(value);
        },
      });
    });

    savedAltdataColumns.forEach((field) => {
      const key = altdataKeyForField(field, altdataColumnMeta);
      cols.push({
        field,
        headerName: `${key} (altdata)`,
        minWidth: 120,
        valueGetter: (_value: any, row: any) => {
          const value = row.altdata?.[key];
          return value === undefined || value === null
            ? null
            : getAnnotationValueString(value);
        },
      });
    });

    return cols.map((col) => (col.width ? col : { flex: 1, ...col }));
  }, [
    annotationColumnMeta,
    altdataColumnMeta,
    savedAnnotationColumns,
    savedAltdataColumns,
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

  // Must be stable: an inline literal makes the grid re-emit page changes in a loop.
  const paginationModel = useMemo(
    () => ({ page: pageNumber - 1, pageSize: rowsPerPage }),
    [pageNumber, rowsPerPage],
  );

  const handleFilterSubmit = (formData: any) => {
    setLoading(true);
    if (
      !formData.position.ra &&
      !formData.position.dec &&
      !formData.position.radius
    ) {
      delete formData.position;
    }

    const data: any = filterOutEmptyValues(formData);

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

  const handleDownload = () => {
    const joined = (values: any[] | undefined) => (values ?? []).join(";");
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
        const annotations = x.annotations ?? [];
        const cells = [
          x.id,
          x.ra,
          x.dec,
          x.redshift,
          joined(x.classifications?.map((c: any) => c.classification)),
          joined(x.classifications?.map((c: any) => c.probability)),
          joined(annotations.map((a: any) => a.origin)),
          joined(annotations.map((a: any) => Object.keys(a.data).length)),
          joined(annotations.flatMap((a: any) => Object.keys(a.data))),
          joined(annotations.flatMap((a: any) => Object.values(a.data))),
          joined(x.groups?.map((g: any) => g.name)),
          getDate(x),
          Array.isArray(x.alias) ? joined(x.alias) : x.alias,
          x.origin,
          x.tns_name,
        ];
        if (includeGcnStatus) {
          cells.push(x.gcn?.status, x.gcn?.explanation, x.gcn?.notes);
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

  const toolbarSlotProps = {
    toolbar: {
      title,
      searchBy,
      searchText,
      onSearchByChange: setSearchBy,
      onSearchTextChange: setSearchText,
      onOpenFilter: () => {
        setFilterFormSubmitted(false);
        setFilterOpen(true);
      },
      onNewSource: isReadOnly ? null : () => setOpenNew(true),
      onDownload: downloadCallback ? handleDownload : null,
      columnPickerOptions,
      onAddColumn: handleAddColumn,
    },
  };

  return (
    <>
      <Box
        data-testid={`source_table_${title}`}
        sx={{
          display: "flex",
          flexDirection: "column",
          width: "100%",
          height: fixedHeader ? FULL_PAGE_HEIGHT : "65vh",
        }}
      >
        {tableFilterList.length > 0 && (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 1 }}>
            {tableFilterList.map((chip) => (
              <Chip
                key={chip}
                label={chip}
                size="small"
                onDelete={() => handleFilterChipDelete(chip)}
              />
            ))}
          </Box>
        )}
        <StyledDataGrid
          rows={displayRows}
          columns={columns}
          loading={loading || isLoading}
          getRowHeight={() => "auto"}
          columnVisibilityModel={columnVisibilityModel}
          onColumnVisibilityModelChange={handleColumnVisibilityModelChange}
          paginationMode="server"
          sortingMode="server"
          rowCount={totalMatches}
          paginationModel={paginationModel}
          onPaginationModelChange={handlePaginationModelChange}
          sortModel={sortModel}
          onSortModelChange={handleSortModelChange}
          disableColumnFilter
          // Keeps all columns mounted so colSpan on the detail row works.
          columnBufferPx={3000}
          slots={TOOLBAR_SLOT}
          slotProps={toolbarSlotProps}
          showToolbar
          sx={{ flex: 1, minHeight: 0 }}
        />
      </Box>
      <Dialog open={filterOpen} onClose={() => setFilterOpen(false)} fullWidth>
        <DialogContent>
          {filterFormSubmitted ? (
            <Box sx={{ mt: 2, display: "flex", alignItems: "center", gap: 1 }}>
              <InfoIcon /> Filters submitted to server!
            </Box>
          ) : (
            <Suspense fallback={<CircularProgress color="secondary" />}>
              <SourceTableFilterForm handleFilterSubmit={handleFilterSubmit} />
            </Suspense>
          )}
        </DialogContent>
      </Dialog>
      <Dialog open={openNew} onClose={() => setOpenNew(false)} maxWidth="md">
        <DialogContent dividers>
          <Suspense fallback={<CircularProgress color="secondary" />}>
            <NewSource onClose={() => setOpenNew(false)} />
          </Suspense>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default SourceTable;
