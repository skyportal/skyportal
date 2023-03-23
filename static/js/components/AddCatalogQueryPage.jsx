import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import Button from "./Button";
import CatalogQueryForm from "./CatalogQueryForm";
import CatalogQueryLists from "./CatalogQueryLists";

import { fetchGcnEventCatalogQueries } from "../ducks/gcnEvent";

const AddCatalogQueryPage = () => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const dispatch = useDispatch();

  const gcnEvent = useSelector((state) => state.gcnEvent);

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  useEffect(() => {
    if (gcnEvent?.id && !gcnEvent?.survey_efficiency) {
      dispatch(fetchGcnEventCatalogQueries({ gcnID: gcnEvent?.id }));
    }
  }, [dispatch, gcnEvent]);

  const catalogQueryList = gcnEvent?.catalog_queries || [];

  return (
    <>
      <Button
        secondary
        size="small"
        onClick={openDialog}
        data-testid={`addCatalogQueryButton_${gcnEvent.id}`}
      >
        Catalog Query
      </Button>
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Catalog Query</DialogTitle>
        <DialogContent>
          <div>
            <CatalogQueryForm gcnevent={gcnEvent} />
            {catalogQueryList?.length > 0 && (
              <CatalogQueryLists catalog_queries={catalogQueryList} />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default AddCatalogQueryPage;
