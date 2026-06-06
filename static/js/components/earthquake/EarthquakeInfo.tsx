import { useState } from "react";
import { Link } from "react-router-dom";
import Typography from "@mui/material/Typography";
import { makeStyles } from "tss-react/mui";
import Grid from "@mui/material/Grid";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import Box from "@mui/material/Box";
import InfoIcon from "@mui/icons-material/Info";
import FilterListIcon from "@mui/icons-material/FilterList";
import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
} from "@mui/x-data-grid";

import { filterOutEmptyValues } from "../../API";
import { useGetEarthquakesQuery } from "../../ducks/earthquake";
import StyledDataGrid from "../StyledDataGrid";
import Spinner from "../Spinner";
import EarthquakesFilterForm from "./EarthquakesFilterForm";

const useStyles = makeStyles()((theme) => ({
  container: {
    width: "100%",
    overflow: "scroll",
  },
  eventTags: {
    marginLeft: "0.5rem",
    "& > div": {
      margin: "0.25rem",
      color: "white",
      background: theme.palette.primary.main,
    },
  },
  gcnEventLink: {
    color:
      theme.palette.mode === "dark"
        ? theme.palette.secondary.main
        : theme.palette.primary.main,
  },
}));

const defaultNumPerPage = 10;

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

const Earthquake = () => {
  const { classes } = useStyles();
  const [filterFormSubmitted, setFilterFormSubmitted] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [sortModel, setSortModel] = useState<any[]>([]);

  const [fetchParams, setFetchParams] = useState<any>({
    pageNumber: 1,
    numPerPage: defaultNumPerPage,
  });

  const { data: earthquakes } = useGetEarthquakesQuery(fetchParams);

  if (earthquakes == null) return <Spinner />;

  const { events, totalMatches } = earthquakes;

  const handlePageChange = (
    pageNumber: number,
    numPerPage: number,
    sortData: any,
  ) => {
    const params: any = {
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
  };

  const handleTableFilter = (
    pageNumber: number,
    numPerPage: number,
    filterData: any,
  ) => {
    const params: any = {
      ...fetchParams,
      pageNumber,
      numPerPage,
    };
    if (filterData && Object.keys(filterData).length > 0) {
      params.startDate = filterData.startDate;
      params.endDate = filterData.endDate;
      params.tagKeep = filterData.tagKeep;
      params.tagRemove = filterData.tagRemove;
    }
    // Save state for future
    setFetchParams(params);
  };

  const handleTableSorting = (sortData: any) => {
    const params = {
      ...fetchParams,
      pageNumber: 1,
      sortBy: sortData.name,
      sortOrder: sortData.direction,
    };
    setFetchParams(params);
  };

  const handleFilterSubmit = async (formData: any) => {
    const data = filterOutEmptyValues(formData);

    handleTableFilter(1, defaultNumPerPage, data);
    setFilterFormSubmitted(true);
  };

  const handlePaginationModelChange = (model: any) => {
    const currentSort = sortModel.length
      ? { name: sortModel[0].field, direction: sortModel[0].sort }
      : {};
    handlePageChange(model.page + 1, model.pageSize, currentSort);
  };

  const handleSortModelChange = (model: any) => {
    setSortModel(model);
    if (!model.length) {
      handlePageChange(1, fetchParams.numPerPage, {});
      return;
    }
    handleTableSorting({ name: model[0].field, direction: model[0].sort });
  };

  const renderNotices = (params: any) => (
    <ul>
      {params.row?.notices?.map((gcnNotice: any) => (
        <li key={gcnNotice.id}>
          {["date", "magnitude", "lat", "lon", "depth", "country"].map(
            (attr) => (
              <p key={attr}>
                {attr}: {gcnNotice[attr]}
              </p>
            ),
          )}
        </li>
      ))}
    </ul>
  );

  const renderEvent = (params: any) => (
    <Link to={`/earthquakes/${params.row?.event_id}`}>
      <Button className={classes.gcnEventLink}>{params.row?.event_id}</Button>
    </Link>
  );

  const columns: any[] = [
    {
      field: "event_id",
      headerName: "ID",
      flex: 1,
      minWidth: 120,
      filterable: false,
      renderCell: renderEvent,
    },
    {
      field: "notices",
      headerName: "Notices",
      flex: 1,
      minWidth: 200,
      sortable: false,
      filterable: false,
      renderCell: renderNotices,
    },
  ];

  const CustomToolbar = () => (
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
    </GridToolbarContainer>
  );

  return (
    <Grid container spacing={3}>
      <Grid size={{ md: 12, sm: 12 }}>
        <Typography variant="h5">Earthquake Events</Typography>
        <Box className={classes.container} sx={{ width: "100%" }}>
          <StyledDataGrid
            autoHeight
            rows={events || []}
            columns={columns}
            getRowId={(row: any) => row.event_id}
            paginationMode="server"
            sortingMode="server"
            rowCount={totalMatches || 0}
            paginationModel={{
              page: fetchParams.pageNumber - 1,
              pageSize: fetchParams.numPerPage,
            }}
            onPaginationModelChange={handlePaginationModelChange}
            sortModel={sortModel}
            onSortModelChange={handleSortModelChange}
            pageSizeOptions={PAGE_SIZE_OPTIONS}
            slots={{ toolbar: CustomToolbar }}
            showToolbar
          />
        </Box>
        <Dialog
          open={filterOpen}
          onClose={() => setFilterOpen(false)}
          fullWidth
        >
          <DialogContent>
            {filterFormSubmitted ? (
              <div>
                <InfoIcon /> &nbsp; Filters submitted to server!
              </div>
            ) : (
              <EarthquakesFilterForm handleFilterSubmit={handleFilterSubmit} />
            )}
          </DialogContent>
        </Dialog>
      </Grid>
    </Grid>
  );
};

export default Earthquake;
