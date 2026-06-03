import { useState } from "react";
import { JSONTree } from "react-json-tree";
import CircularProgress from "@mui/material/CircularProgress";

import { showNotification } from "baselayer/components/Notifications";
import DeleteIcon from "@mui/icons-material/Delete";

import { useAppDispatch } from "../../types/hooks";
import * as defaultGcnTagsActions from "../../ducks/default_gcn_tags";
import Button from "../Button";
import StyledDataGrid from "../StyledDataGrid";
import ConfirmDeletionDialog from "../ConfirmDeletionDialog";

interface DefaultGcnTagTableProps {
  default_gcn_tags: any[];
}

const DefaultGcnTagTable = ({ default_gcn_tags }: DefaultGcnTagTableProps) => {
  const dispatch = useAppDispatch();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [defaultGcnTagToDelete, setDefaultGcnTagToDelete] = useState<any>(null);
  const openDialog = (id: any) => {
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
    ).then((result: any) => {
      if (result.status === "success") {
        dispatch(showNotification("DefaultGcnTag deleted"));
        closeDialog();
      }
    });
  };

  const columns: any[] = [
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
      renderCell: (params: any) =>
        params.row ? <JSONTree data={params.row.filters} /> : "",
    },
    {
      field: "delete",
      headerName: " ",
      width: 70,
      sortable: false,
      filterable: false,
      renderCell: (params: any) => (
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
        getRowId={(row: any) => row.id}
        hideFooter
        initialState={{ pagination: { paginationModel: { pageSize: 100 } } }}
        showToolbar
      />
    </div>
  );
};

export default DefaultGcnTagTable;
