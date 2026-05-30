import React, { useState } from "react";
import { JSONTree } from "react-json-tree";
import { useDispatch } from "react-redux";
import PropTypes from "prop-types";
import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";
import DeleteIcon from "@mui/icons-material/Delete";

import * as defaultGcnTagsActions from "../../ducks/default_gcn_tags";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

const DefaultGcnTagTable = ({ default_gcn_tags }) => {
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

  const columns = [
    {
      field: "default_tag_name",
      headerName: "Default Tag Name",
      flex: 1,
      minWidth: 160,
    },
    {
      field: "filters",
      headerName: "Filters",
      flex: 1,
      minWidth: 200,
      sortable: false,
      renderCell: (params) =>
        params.row ? <JSONTree data={params.row.filters} /> : "",
    },
    {
      field: "delete",
      headerName: " ",
      width: 70,
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <>
          <Button id="delete_button" onClick={() => openDialog(params.row.id)}>
            <DeleteIcon />
          </Button>
          <ConfirmDeletionDialog
            deleteFunction={deleteDefaultGcnTag}
            dialogOpen={dialogOpen}
            closeDialog={closeDialog}
            resourceName="defaultGcnTag"
          />
        </>
      ),
    },
  ];

  if (!default_gcn_tags) return <CircularProgress />;

  return (
    <div style={{ width: "100%", minWidth: "40vw", overflow: "scroll" }}>
      <StyledDataGrid
        autoHeight
        rows={default_gcn_tags}
        columns={columns}
        getRowId={(row) => row.id}
        hideFooter
        initialState={{ pagination: { paginationModel: { pageSize: 100 } } }}
        showToolbar
      />
    </div>
  );
};

DefaultGcnTagTable.propTypes = {
  // eslint-disable-next-line react/forbid-prop-types
  default_gcn_tags: PropTypes.arrayOf(PropTypes.any).isRequired,
};

export default DefaultGcnTagTable;
