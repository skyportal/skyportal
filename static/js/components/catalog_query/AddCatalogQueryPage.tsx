import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid";
import { skipToken } from "@reduxjs/toolkit/query";

import Button from "../Button";
import CatalogQueryForm from "./CatalogQueryForm";
import CatalogQueryLists from "./CatalogQueryLists";

import {
  useGetGcnEventQuery,
  useGetGcnEventCatalogQueriesQuery,
} from "../../ducks/gcnEvent";

interface AddCatalogQueryPageProps {
  dateobs: string;
}

const AddCatalogQueryPage = ({ dateobs }: AddCatalogQueryPageProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: gcnEvent } = useGetGcnEventQuery(dateobs ?? skipToken);
  const { data: catalogQueries } = useGetGcnEventCatalogQueriesQuery(
    gcnEvent?.id != null ? { gcnID: gcnEvent["id"] } : skipToken,
  );

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  const catalogQueryList = catalogQueries || [];

  return (
    <>
      <Button
        secondary
        size="small"
        onClick={openDialog}
        data-testid={`addCatalogQueryButton_${gcnEvent?.id}`}
      >
        Catalog Query
      </Button>
      <Dialog open={dialogOpen} onClose={closeDialog} maxWidth={"xlg" as any}>
        <DialogTitle>Catalog Query</DialogTitle>
        <DialogContent>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 4 }}>
              <CatalogQueryForm gcnevent={gcnEvent as any} />
            </Grid>
            <Grid size={{ xs: 12, md: 8 }}>
              <CatalogQueryLists catalog_queries={catalogQueryList || []} />
            </Grid>
          </Grid>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default AddCatalogQueryPage;
