import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { showNotification } from "baselayer/components/Notifications";
import { useForm } from "react-hook-form";
import AddIcon from "@mui/icons-material/Add";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import ClassificationSelect from "../classification/ClassificationSelect";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as Actions from "../../ducks/source";
import { allowedClasses } from "../classification/ClassificationForm";
import Button from "../Button";

interface AddClassificationsScanningPageProps {
  obj_id: string;
}

const AddClassificationsScanningPage = ({
  obj_id,
}: AddClassificationsScanningPageProps) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedClassifications, setSelectedClassifications] = useState<
    string[]
  >([]);
  const dispatch = useAppDispatch();

  const { taxonomyList } = useAppSelector(
    (state) => state["taxonomies"],
  ) as any;
  const latestTaxonomyList = taxonomyList?.filter((t: any) => t.isLatest);
  const classificationsAndTaxonomyIds: Record<string, number> = {};
  latestTaxonomyList?.forEach((taxonomy: any) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy);
    currentClasses?.forEach((option: any) => {
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
      const result: any = await dispatch(Actions.addClassification(data));
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
          onClick={openDialog}
          data-testid={`addClassificationsButton_${obj_id}`}
        >
          <AddIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Dialog open={dialogOpen} onClose={closeDialog}>
        <DialogTitle>Add Classifications</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: "0.4rem", mb: "0.8rem" }}>
            <ClassificationSelect
              selectedClassifications={selectedClassifications}
              setSelectedClassifications={setSelectedClassifications}
              showShortcuts
              inDialog
            />
          </Box>
          <Button
            primary
            data-testid="addClassificationsButtonInDialog"
            onClick={handleSubmit(onSubmit)}
          >
            Add Classifications
          </Button>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default AddClassificationsScanningPage;
