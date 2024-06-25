import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid";

import Button from "../Button";
import CatalogQueryForm from "./CatalogQueryForm";
import CatalogQueryLists from "./CatalogQueryLists";

import { fetchGcnEventCatalogQueries } from "../../ducks/gcnEvent";

const AddCatalogQueryPage = () => {
  const dispatch = useDispatch();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [fetchingCatalogQueries, setFetchingCatalogQueries] = useState(false);

  const gcnEvent = useSelector((state) => state.gcnEvent);

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  useEffect(() => {
    if (gcnEvent?.id && !gcnEvent?.catalog_queries && !fetchingCatalogQueries) {
      setFetchingCatalogQueries(true);
      dispatch(fetchGcnEventCatalogQueries({ gcnID: gcnEvent?.id })).then(
        () => {
          setFetchingCatalogQueries(false);
        },
      );
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
        maxWidth="xlg"
      >
        <DialogTitle>Catalog Query</DialogTitle>
        <DialogContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <CatalogQueryForm gcnevent={gcnEvent} />
            </Grid>
            <Grid item xs={12} md={8}>
              <CatalogQueryLists catalog_queries={catalogQueryList || []} />
            </Grid>
          </Grid>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default AddCatalogQueryPage;
