import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import { makeStyles, withStyles } from "tss-react/mui";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import TextField from "@mui/material/TextField";
import AddIcon from "@mui/icons-material/Add";
import JoinInnerIcon from "@mui/icons-material/JoinInner";
import LocalOfferIcon from "@mui/icons-material/LocalOffer";
import FilterListIcon from "@mui/icons-material/FilterList";
import Close from "@mui/icons-material/Close";
import { grey } from "@mui/material/colors";

import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import MuiDialogTitle from "@mui/material/DialogTitle";
import Tooltip from "@mui/material/Tooltip";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import ExpandLess from "@mui/icons-material/ExpandLess";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
} from "@mui/x-data-grid";
import { showNotification } from "baselayer/components/Notifications";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";

import { filterOutEmptyValues } from "../../API";
import * as gcnEventsActions from "../../ducks/gcnEvents";
import Spinner from "../Spinner";
import GcnEventsFilterForm from "./GcnEventsFilterForm";
import NewGcnEvent from "./NewGcnEvent";
import DefaultGcnTagPage from "./DefaultGcnTagPage";
import Crossmatch from "./CrossmatchGcnEvents";
import GcnEventAllocationTriggers from "./GcnEventAllocationTriggers";

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const useStyles = makeStyles()((theme) => ({
  tags: {
    margin: "0 1px 1px 0",
    "& > div": {
      margin: "0.25rem",
    },
  },
  gcnEventLink: {
    padding: 0,
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
  },
  list: {
    listStyleType: "none",
    paddingLeft: 0,
    margin: 0,
    "& li:not(:first-child)": {
      position: "relative",
      marginTop: theme.spacing(2),
      "&:before": {
        content: `""`,
        backgroundColor: theme.palette.grey[400],
        position: "absolute",
        top: theme.spacing(-1),
        left: "0",
        width: "20%",
        height: "1px",
      },
    },
    "& div": {
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      "& a": {
        cursor: "pointer",
      },
    },
  },
  smallText: {
    fontSize: "0.7rem",
  },
}));

const dialogTitleStyles = (theme: any) => ({
  root: {
    margin: 0,
    padding: theme.spacing(2),
  },
  title: {
    marginRight: theme.spacing(2),
    fontSize: "1.5rem",
  },
  closeButton: {
    position: "absolute",
    right: theme.spacing(1),
    top: theme.spacing(1),
    color: grey[500],
  },
});

const DialogTitle = withStyles(
  ({ children, classes, onClose }: any) => (
    <MuiDialogTitle className={classes.root}>
      <Typography className={classes.title}>{children}</Typography>
      {onClose ? (
        <IconButton
          aria-label="close"
          className={classes.closeButton}
          onClick={onClose}
        >
          <Close />
        </IconButton>
      ) : null}
    </MuiDialogTitle>
  ),
  dialogTitleStyles,
);

const defaultNumPerPage = 10;

const GcnEvents = () => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const gcnEvents = useAppSelector((state) => state["gcnEvents"]);

  const gcn_tags_classes = useAppSelector(
    (state) => (state as any).config.gcnTagsClasses,
  );

  const [openNew, setOpenNew] = useState(false);
  const [showAllLocalizations, setShowAllLocalizations] = useState<any>(false);
  const [showAllNotices, setShowAllNotices] = useState<any>(false);
  const [openCrossmatch, setOpenCrossmatch] = useState(false);
  const [openDefaultTag, setOpenDefaultTag] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [sortModel, setSortModel] = useState<any[]>([]);

  const [fetchParams, setFetchParams] = useState<any>({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  useEffect(() => {
    dispatch(gcnEventsActions.fetchGcnEvents());
  }, [dispatch]);

  if (!gcnEvents) {
    return <p>No gcnEvents available...</p>;
  }

  const { totalMatches } = gcnEvents as any;

  const handleClose = () => {
    setOpenNew(false);
    setOpenCrossmatch(false);
    setOpenDefaultTag(false);
  };

  const handlePageChange = async (
    pageNumber: number,
    numPerPage: number,
    sortData: any,
  ) => {
    const params = {
      ...fetchParams,
      pageNumber,
      numPerPage,
    };
    if (sortData && Object.keys(sortData).length > 0) {
      params.sortBy = sortData.name;
      params.sortOrder = sortData.direction;
    }
    // Save state for future
    setFetchParams(params);
    await dispatch(gcnEventsActions.fetchGcnEvents(params));
  };

  const handleTableFilter = async (
    pageNumber: number,
    numPerPage: number,
    filterData: any,
  ) => {
    const params = {
      ...fetchParams,
      pageNumber,
      numPerPage,
    };
    if (filterData && Object.keys(filterData).length > 0) {
      params.startDate = filterData.startDate;
      params.endDate = filterData.endDate;
      params.gcnTagKeep = filterData.gcnTagKeep;
      params.gcnTagRemove = filterData.gcnTagRemove;
      params.gcnPropertiesFilter = filterData.gcnPropertiesFilter;
      params.localizationTagKeep = filterData.localizationTagKeep;
      params.localizationTagRemove = filterData.localizationTagRemove;
      params.localizationPropertiesFilter =
        filterData.localizationPropertiesFilter;
    }
    // Save state for future
    setFetchParams(params);
    await dispatch(gcnEventsActions.fetchGcnEvents(params));
  };

  const handleTableSorting = async (sortData: any) => {
    const params = {
      ...fetchParams,
      pageNumber: 1,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setFetchParams(params);
    await dispatch(gcnEventsActions.fetchGcnEvents(params));
  };

  const handleFilterSubmit = async (formData: any) => {
    const data = filterOutEmptyValues(formData, false);
    if ("property" in data) {
      data["propertiesFilter"] =
        `${data["property"]}: ${data["propertyComparatorValue"]}: ${data["propertyComparator"]}`;
    }
    handleTableFilter(1, defaultNumPerPage, data);
    dispatch(showNotification("Filters submitted to server"));
    setFilterOpen(false);
  };

  const handleSearchChange = async (text: string) => {
    const params = {
      ...fetchParams,
      pageNumber: 1,
      partialdateobs: text,
    };
    setFetchParams(params);
    await dispatch(gcnEventsActions.fetchGcnEvents(params));
  };

  const handlePaginationModelChange = (model: any) => {
    const sortData =
      sortModel.length > 0
        ? { name: sortModel[0].field, direction: sortModel[0].sort }
        : {};
    handlePageChange(model.page + 1, model.pageSize, sortData);
  };

  const handleSortModelChange = (model: any) => {
    setSortModel(model);
    if (!model.length) {
      handlePageChange(1, fetchParams.numPerPage, {});
      return;
    }
    const { field, sort } = model[0];
    handleTableSorting({ name: field, direction: sort });
  };

  const renderGcnTags = (params: any) => {
    const gcnTags: any[] = [];
    params.row?.tags?.forEach((tag: any) => {
      gcnTags.push(tag);
    });
    const gcnTagsUnique = [...new Set(gcnTags)];
    return gcnTagsUnique.map((tag) => (
      <Chip
        size="small"
        key={tag}
        label={tag}
        className={classes.tags}
        style={{
          backgroundColor:
            gcn_tags_classes && tag in gcn_tags_classes
              ? gcn_tags_classes[tag]
              : "#999999",
        }}
      />
    ));
  };

  const renderAllocationTriggers = (params: any) => (
    <GcnEventAllocationTriggers gcnEvent={params.row} showPassed />
  );

  const renderLocalizationTags = (params: any) => {
    const localizationTags: any[] = [];
    params.row.localizations?.forEach((loc: any) => {
      loc.tags?.forEach((tag: any) => {
        localizationTags.push(tag.text);
      });
    });
    const localizationTagsUnique = [...new Set(localizationTags)];
    return localizationTagsUnique.map((tag) => (
      <Chip size="small" key={tag} label={tag} className={classes.tags} />
    ));
  };

  const expandButton = (
    setShowAll: (...a: any[]) => void,
    showAll: any,
    cellToProcess: any,
  ) => (
    <div className={(classes as any).expandButton}>
      <IconButton
        aria-label="expandButton"
        onClick={() =>
          setShowAll(showAll === cellToProcess ? false : cellToProcess)
        }
        size="small"
      >
        {showAll === cellToProcess ? <ExpandLess /> : <MoreHorizIcon />}
      </IconButton>
    </div>
  );

  const renderLocalizations = (params: any) => {
    const event = params.row;
    return (
      <ul className={classes.list}>
        {event?.localizations?.map((loc: any, index: number) => (
          <li
            key={loc.id}
            style={
              showAllLocalizations !== event.id && index > 2
                ? { display: "none" }
                : {}
            }
          >
            <p>{loc.localization_name}</p>
          </li>
        ))}
        {event?.localizations?.length > 3 &&
          expandButton(setShowAllLocalizations, showAllLocalizations, event.id)}
      </ul>
    );
  };

  const renderGcnNotices = (params: any) => {
    const event = params.row;
    return (
      <ul className={classes.list}>
        {event?.gcn_notices?.map((gcnNotice: any, index: number) => (
          <li
            key={gcnNotice.id}
            style={
              showAllNotices !== event.id && index > 1
                ? { display: "none" }
                : {}
            }
          >
            <Tooltip title={gcnNotice.ivorn} placement="left">
              <p>{gcnNotice.stream}</p>
            </Tooltip>
            <p className={classes.smallText}>{gcnNotice.notice_type}</p>
            <p className={classes.smallText}>{gcnNotice.date}</p>
          </li>
        ))}
        {event?.gcn_notices?.length > 2 &&
          expandButton(setShowAllNotices, showAllNotices, event.id)}
      </ul>
    );
  };

  const renderDateObs = (params: any) => (
    <Link to={`/gcn_events/${params.row?.dateobs}`}>
      <Button className={classes.gcnEventLink}>{params.row?.dateobs}</Button>
    </Link>
  );

  const renderAliases = (params: any) =>
    params.row?.aliases?.length > 0 ? (
      <p>{params.row?.aliases.join(", ")}</p>
    ) : (
      <p>No aliases</p>
    );

  const columns: any[] = [
    {
      field: "dateobs",
      headerName: "Date Observed",
      flex: 1,
      minWidth: 180,
      filterable: false,
      renderCell: renderDateObs,
    },
    {
      field: "aliases",
      headerName: "Aliases",
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
      renderCell: renderAliases,
    },
    {
      field: "gcn_tags",
      headerName: "Event Tags",
      flex: 1,
      minWidth: 120,
      sortable: false,
      filterable: false,
      renderCell: renderGcnTags,
    },
    {
      field: "allocation_triggers",
      headerName: "Allocation Triggers",
      flex: 1,
      minWidth: 150,
      sortable: false,
      filterable: false,
      renderCell: renderAllocationTriggers,
    },
    {
      field: "localization_tags",
      headerName: "Localization Tags",
      flex: 1,
      minWidth: 150,
      sortable: false,
      filterable: false,
      renderCell: renderLocalizationTags,
    },
    {
      field: "localizations",
      headerName: "Localizations",
      flex: 1,
      minWidth: 150,
      sortable: false,
      filterable: false,
      renderCell: renderLocalizations,
    },
    {
      field: "gcn_notices",
      headerName: "GCN Notices",
      flex: 1,
      minWidth: 150,
      sortable: false,
      filterable: false,
      renderCell: renderGcnNotices,
    },
  ];

  const CustomToolbar = function GcnEventsToolbar() {
    return (
      <GridToolbarContainer>
        <GridToolbarColumnsButton />
        <Tooltip title="Filter Table">
          <IconButton
            size="small"
            data-testid="Filter Table-iconButton"
            onClick={() => setFilterOpen(true)}
          >
            <FilterListIcon />
          </IconButton>
        </Tooltip>
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
          name="new_gcnevent"
          onClick={() => {
            setOpenNew(true);
          }}
        >
          <AddIcon />
        </IconButton>
        <IconButton
          name="crossmatch_gcnevents"
          onClick={() => {
            setOpenCrossmatch(true);
          }}
        >
          <JoinInnerIcon />
        </IconButton>
        <IconButton
          name="default_gcn_tags"
          onClick={() => {
            setOpenDefaultTag(true);
          }}
        >
          <LocalOfferIcon />
        </IconButton>
      </GridToolbarContainer>
    );
  };

  return (
    <Grid container spacing={3}>
      <Grid size={{ md: 12, sm: 12 }}>
        <Paper elevation={1}>
          <div className={(classes as any).paperContent}>
            {gcnEvents ? (
              <>
                <Typography
                  variant="h6"
                  style={{ padding: "0.5rem 0.75rem 0" }}
                >
                  GCN Events
                </Typography>
                <Box sx={{ width: "100%" }}>
                  <StyledDataGrid
                    autoHeight
                    rows={(gcnEvents as any).events || []}
                    columns={columns}
                    getRowId={(row: any) => row.dateobs}
                    paginationMode="server"
                    sortingMode="server"
                    rowCount={totalMatches}
                    paginationModel={{
                      page: fetchParams.pageNumber - 1,
                      pageSize: fetchParams.numPerPage,
                    }}
                    onPaginationModelChange={handlePaginationModelChange}
                    sortModel={sortModel}
                    onSortModelChange={handleSortModelChange}
                    pageSizeOptions={PAGE_SIZE_OPTIONS}
                    disableColumnFilter
                    slots={{ toolbar: CustomToolbar }}
                    showToolbar
                  />
                </Box>
              </>
            ) : (
              <Spinner />
            )}
          </div>
        </Paper>
        <Dialog
          open={filterOpen}
          onClose={() => setFilterOpen(false)}
          fullWidth
        >
          <DialogContent>
            <GcnEventsFilterForm handleFilterSubmit={handleFilterSubmit} />
          </DialogContent>
        </Dialog>
        {openNew && (
          <Dialog open={openNew} onClose={handleClose} maxWidth="md">
            <DialogTitle onClose={handleClose}>New GCN Event</DialogTitle>
            <DialogContent dividers>
              <NewGcnEvent handleClose={handleClose} />
            </DialogContent>
          </Dialog>
        )}
        {openCrossmatch && (
          <Dialog open={openCrossmatch} onClose={handleClose} maxWidth="md">
            <DialogTitle onClose={handleClose}>
              Crossmatch GCN Events
            </DialogTitle>
            <DialogContent dividers>
              <Crossmatch />
            </DialogContent>
          </Dialog>
        )}
        {openDefaultTag && (
          <Dialog open={openDefaultTag} onClose={handleClose} maxWidth="md">
            <DialogTitle onClose={handleClose}>Default Gcn Tags</DialogTitle>
            <DialogContent dividers>
              <DefaultGcnTagPage />
            </DialogContent>
          </Dialog>
        )}
      </Grid>
    </Grid>
  );
};

export default GcnEvents;
