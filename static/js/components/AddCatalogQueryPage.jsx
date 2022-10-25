import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import { useDispatch } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";

import Button from "./Button";
import CatalogQueryForm from "./CatalogQueryForm";
import CatalogQueryLists from "./CatalogQueryLists";

import { GET } from "../API";

const AddCatalogQueryPage = ({ gcnevent }) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const dispatch = useDispatch();

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  const [catalogQueryList, setCatalogQueryList] = useState(null);
  useEffect(() => {
    const fetchCatalogQueryList = async () => {
      const response = await dispatch(
        GET(
          `/api/gcn_event/${gcnevent.id}/catalog_query`,
          "skyportal/FETCH_GCNEVENT_CATALOG_QUERIES"
        )
      );
      setCatalogQueryList(response.data);
    };
    fetchCatalogQueryList();
  }, [dispatch, setCatalogQueryList, gcnevent]);

  return (
    <>
      <Button
        secondary
        size="small"
        onClick={openDialog}
        data-testid={`addCatalogQueryButton_${gcnevent.id}`}
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
            <CatalogQueryForm gcnevent={gcnevent} />
            {catalogQueryList?.length > 0 && (
              <CatalogQueryLists catalog_queries={catalogQueryList} />
            )}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

AddCatalogQueryPage.propTypes = {
  gcnevent: PropTypes.shape({
    dateobs: PropTypes.string,
    localizations: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        localization_name: PropTypes.string,
      })
    ),
    id: PropTypes.number,
  }).isRequired,
};

export default AddCatalogQueryPage;
