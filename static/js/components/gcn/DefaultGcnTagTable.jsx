import React, { useState } from "react";
import { JSONTree } from "react-json-tree";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import {
  createTheme,
  StyledEngineProvider,
  ThemeProvider,
  useTheme,
} from "@mui/material/styles";
import makeStyles from "@mui/styles/makeStyles";
import CircularProgress from "@mui/material/CircularProgress";

import MUIDataTable from "mui-datatables";

import { showNotification } from "baselayer/components/Notifications";
import DeleteIcon from "@mui/icons-material/Delete";

import * as defaultGcnTagsActions from "../../ducks/default_gcn_tags";
import Button from "../Button";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

const useStyles = makeStyles((theme) => ({
  container: {
    width: "100%",
    minWidth: "40vw",
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

const DefaultGcnTagTable = ({ default_gcn_tags }) => {
  const classes = useStyles();
  const theme = useTheme();

  const dispatch = useDispatch();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [defaultGcnTagToDelete, setDefaultGcnTagToDelete] = useState(null);
  const openDialog = (id) => {
    setDialogOpen(true);
    setDefaultGcnTagToDelete(id);
  };
  const closeDialog = () => {
    setDialogOpen(false);
    setDefaultGcnTagToDelete(null);
  };

  const deleteDefaultGcnTag = () => {
    dispatch(
      defaultGcnTagsActions.deleteDefaultGcnTag(defaultGcnTagToDelete),
    ).then((result) => {
      if (result.status === "success") {
        dispatch(showNotification("DefaultGcnTag deleted"));
        closeDialog();
      }
    });
  };

  const renderDefaultGcnTagName = (dataIndex) => {
    const default_gcn_tag = default_gcn_tags[dataIndex];

    return <div>{default_gcn_tag ? default_gcn_tag.default_tag_name : ""}</div>;
  };

  const renderFilters = (dataIndex) => {
    const default_gcn_tag = default_gcn_tags[dataIndex];

    return (
      <div>
        {default_gcn_tag ? <JSONTree data={default_gcn_tag.filters} /> : ""}
      </div>
    );
  };

  const renderDelete = (dataIndex) => {
    const default_gcn_tag = default_gcn_tags[dataIndex];
    return (
      <div>
        <Button
          key={default_gcn_tag.id}
          id="delete_button"
          classes={{
            root: classes.defaultGcnTagDelete,
          }}
          onClick={() => openDialog(default_gcn_tag.id)}
        >
          <DeleteIcon />
        </Button>
        <ConfirmDeletionDialog
          deleteFunction={deleteDefaultGcnTag}
          dialogOpen={dialogOpen}
          closeDialog={closeDialog}
          resourceName="defaultGcnTag"
        />
      </div>
    );
  };

  const columns = [
    {
      name: "default_tag_name",
      label: "Default Tag Name",
      options: {
        filter: true,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderDefaultGcnTagName,
      },
    },
    {
      name: "filters",
      label: "Filters",
      options: {
        filter: false,
        sort: true,
        sortThirdClickReset: true,
        customBodyRenderLite: renderFilters,
      },
    },
    {
      name: "delete",
      label: " ",
      options: {
        customBodyRenderLite: renderDelete,
      },
    },
  ];

  const options = {
    search: false,
    draggableColumns: { enabled: true },
    selectableRows: "none",
    elevation: 0,
    jumpToPage: true,
    serverSide: true,
    pagination: false,
    filter: true,
    sort: true,
  };

  return (
    <div className={classes.container}>
      {default_gcn_tags ? (
        <StyledEngineProvider injectFirst>
          <ThemeProvider theme={getMuiTheme(theme)}>
            <MUIDataTable
              data={default_gcn_tags}
              options={options}
              columns={columns}
            />
          </ThemeProvider>
        </StyledEngineProvider>
      ) : (
        <CircularProgress />
      )}
    </div>
  );
};

DefaultGcnTagTable.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  default_gcn_tags: PropTypes.arrayOf(PropTypes.any).isRequired,
};

export default DefaultGcnTagTable;
