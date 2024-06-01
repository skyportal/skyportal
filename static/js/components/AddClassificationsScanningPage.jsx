import React, { useState } from "react";
import PropTypes from "prop-types";
import { useDispatch, useSelector } from "react-redux";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { showNotification } from "baselayer/components/Notifications";
import { useForm } from "react-hook-form";
import AddIcon from "@mui/icons-material/Add";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import ClassificationSelect from "./classification/ClassificationSelect";
import * as Actions from "../ducks/source";
import { allowedClasses } from "./classification/ClassificationForm";
import Button from "./Button";

const AddClassificationsScanningPage = ({ obj_id }) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedClassifications, setSelectedClassifications] = useState([]);
  const dispatch = useDispatch();

  const { taxonomyList } = useSelector((state) => state.taxonomies);
  const latestTaxonomyList = taxonomyList?.filter((t) => t.isLatest);
  const classificationsAndTaxonomyIds = {};
  latestTaxonomyList?.forEach((taxonomy) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy);
    currentClasses?.forEach((option) => {
      classificationsAndTaxonomyIds[option.class] = taxonomy.id;
    });
  });

  const { handleSubmit } = useForm();

  const openDialog = () => {
    setDialogOpen(true);
  };

  const closeDialog = () => {
    setDialogOpen(false);
  };

  const onSubmit = () => {
    selectedClassifications.forEach(async (classification) => {
      const data = {
        taxonomy_id: classificationsAndTaxonomyIds[classification],
        obj_id,
        classification,
        probability: 1,
      };
      const result = await dispatch(Actions.addClassification(data));
      if (result.status === "success") {
        dispatch(showNotification(`Classification ${classification} saved`));
      }
    });
    setSelectedClassifications([]);
    closeDialog();
  };
  return (
    <>
      <Tooltip title="Add Classifications">
        <IconButton
          size="small"
          onClick={openDialog}
          data-testid={`addClassificationsButton_${obj_id}`}
        >
          <AddIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Dialog
        open={dialogOpen}
        onClose={closeDialog}
        style={{ position: "fixed" }}
      >
        <DialogTitle>Add Classifications</DialogTitle>
        <DialogContent>
          <form onSubmit={handleSubmit(onSubmit)}>
            <ClassificationSelect
              selectedClassifications={selectedClassifications}
              setSelectedClassifications={setSelectedClassifications}
              showShortcuts
              inDialog
            />
            <Button
              primary
              type="submit"
              data-testid="addClassificationsButtonInDialog"
            >
              Add Classifications
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
};

AddClassificationsScanningPage.propTypes = {
  obj_id: PropTypes.string.isRequired,
};

export default AddClassificationsScanningPage;
