import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import { showNotification } from "baselayer/components/Notifications";
import Paper from "@mui/material/Paper";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Tooltip from "@mui/material/Tooltip";
import IconButton from "@mui/material/IconButton";

import MUIDataTable from "mui-datatables";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";
import LocalizationPlot from "../localization/LocalizationPlot";
import NewMovingObject from "./NewMovingObject";

import * as movingObjectActions from "../../ducks/moving_object";

const useStyles = makeStyles((theme) => ({
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
  localizationContainer: {
    maxWidth: "20vw",
  },
}));

// Tweak responsive styling
const getMuiTheme = (theme) =>
  createTheme({
    palette: theme.palette,
    components: {
      MUIDataTablePagination: {
        styleOverrides: {
          toolbar: {
            flexFlow: "row wrap",
            justifyContent: "flex-end",
            padding: "0.5rem 1rem 0",
            [theme.breakpoints.up("sm")]: {
              // Cancel out small screen styling and replace
              padding: "0px",
              paddingRight: "2px",
              flexFlow: "row nowrap",
            },
          },
          tableCellContainer: {
            padding: "1rem",
          },
          selectRoot: {
            marginRight: "0.5rem",
            [theme.breakpoints.up("sm")]: {
              marginLeft: "0",
              marginRight: "2rem",
            },
          },
        },
      },
    },
  });

const MovingObjectTable = ({
  movingObjects,
  paginateCallback,
  totalMatches,
  numPerPage,
  sortingCallback,
}) => {
  const classes = useStyles();
  const theme = useTheme();
  const dispatch = useDispatch();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [movingObjectToDelete, setMovingObjectToDelete] = useState(null);

  const openDialog = (id) => {
    setDialogOpen(true);
    setMovingObjectToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setMovingObjectToDelete(null);
  };

  const deleteMovingObject = () => {
    dispatch(movingObjectActions.deleteMovingObject(movingObjectToDelete)).then(
      (result) => {
        if (result.status === "success") {
          dispatch(showNotification("Moving object deleted"));
          closeDialog();
        }
      },
    );
  };

  const [rowsPerPage, setRowsPerPage] = useState(numPerPage);

  const renderMovingObjectName = (dataIndex) => {
    const movingObject = movingObjects[dataIndex];

    return <div>{movingObject?.id || ""}</div>;
  };

  const renderLocalization = (dataIndex) => {
    const movingObject = movingObjects[dataIndex];
    const options = { localization: true };

    return (
      <div className={classes.localizationContainer}>
        <LocalizationPlot
          localization={movingObject}
          options={options}
          height={600}
          width={600}
          projection="orthographic"
        />
      </div>
    );
  };

  const renderDelete = (dataIndex) => {
    const movingObject = movingObjects[dataIndex];
    return (
      <div>
        <Button
          key={movingObject.id}
          id="delete_button"
          classes={{
            root: classes.movingObjectDelete,
            disabled: classes.movingObjectDeleteDisabled,
          }}
          onClick={() => openDialog(movingObject.id)}
        >
          <DeleteIcon />
        </Button>
        <ConfirmDeletionDialog
          deleteFunction={deleteMovingObject}
          dialogOpen={dialogOpen}
          closeDialog={closeDialog}
          resourceName="movingObject"
        />
      </div>
    );
  };

  const handleSearchChange = (searchText) => {
    const data = { moving_objectID: searchText };
    if (searchText === "") {
      delete data.moving_objectID;
    }
    paginateCallback(1, rowsPerPage, {}, data);
  };

  const handleTableChange = (action, tableState) => {
    switch (action) {
      case "changePage":
      case "changeRowsPerPage":
        setRowsPerPage(tableState.rowsPerPage);
        paginateCallback(
          tableState.page + 1,
          tableState.rowsPerPage,
          tableState.sortOrder,
        );
        break;
      case "sort":
        if (tableState.sortOrder.direction === "none") {
          paginateCallback(1, tableState.rowsPerPage, {});
        } else {
          sortingCallback(tableState.sortOrder);
        }
        break;
      default:
    }
  };

  const columns = [
    {
      name: "name",
      label: "Name",
      options: {
        filter: true,
        // sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderMovingObjectName,
      },
    },
  ];
  columns.push({
    name: "skymap",
    label: "Skymap",
    options: {
      customBodyRenderLite: renderLocalization,
    },
  });
  columns.push({
    name: "delete",
    label: " ",
    options: {
      customBodyRenderLite: renderDelete,
    },
  });

  const [openNew, setOpenNew] = useState(false);

  const options = {
    search: true,
    onSearchChange: handleSearchChange,
    selectableRows: "none",
    rowHover: false,
    print: false,
    elevation: 1,
    onTableChange: handleTableChange,
    jumpToPage: true,
    serverSide: true,
    pagination: true,
    rowsPerPage,
    rowsPerPageOptions: [1, 10, 20, 50, 100],
    count: totalMatches,
    filter: true,
    sort: true,
    customToolbar: () => (
      <Tooltip title="Add new moving object">
        <IconButton
          onClick={() => {
            setOpenNew(true);
          }}
        >
          <AddIcon />
        </IconButton>
      </Tooltip>
    ),
  };

  return (
    <div>
      {movingObjects ? (
        <Paper className={classes.container}>
          <StyledEngineProvider injectFirst>
            <ThemeProvider theme={getMuiTheme(theme)}>
              <MUIDataTable
                data={movingObjects}
                options={options}
                columns={columns}
              />
            </ThemeProvider>
          </StyledEngineProvider>
        </Paper>
      ) : (
        <CircularProgress />
      )}
      <Dialog
        open={openNew}
        onClose={() => setOpenNew(false)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>Add New Moving Object</DialogTitle>
        <DialogContent>
          <NewMovingObject onSubmit={() => setOpenNew(false)} />
        </DialogContent>
      </Dialog>
    </div>
  );
};

MovingObjectTable.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  movingObjects: PropTypes.arrayOf(PropTypes.any).isRequired,
  // eslint-disable-next-line react/forbid-prop-types
  paginateCallback: PropTypes.func.isRequired,
  sortingCallback: PropTypes.func,
  totalMatches: PropTypes.number,
  numPerPage: PropTypes.number,
};

MovingObjectTable.defaultProps = {
  totalMatches: 0,
  numPerPage: 10,
  sortingCallback: null,
};

export default MovingObjectTable;
