import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import { showNotification } from "baselayer/components/Notifications";
import AddIcon from "@mui/icons-material/Add";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import Box from "@mui/material/Box";
import ClassificationSelect from "../classification/ClassificationSelect";
import { useAppDispatch } from "../../types/hooks";
import { useAddClassificationMutation } from "../../ducks/source";
import { useGetTaxonomiesQuery } from "../../ducks/taxonomies";
import { allowedClasses } from "../classification/ClassificationForm";
import Button from "../Button";
import { useHasPermission } from "../../ducks/profile";

interface AddClassificationsScanningPageProps {
  obj_id: string;
}

const AddClassificationsScanningPage = ({
  obj_id,
}: AddClassificationsScanningPageProps) => {
  const canClassify = useHasPermission("Classify");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedClassifications, setSelectedClassifications] = useState<
    string[]
  >([]);
  const dispatch = useAppDispatch();
  const [addClassification] = useAddClassificationMutation();
  const { data: taxonomyList } = useGetTaxonomiesQuery();

  if (!canClassify) return null;

  const onSubmit = () => {
    const taxonomyIds = Object.fromEntries(
      (taxonomyList ?? [])
        .filter((taxonomy: any) => taxonomy.isLatest)
        .flatMap((taxonomy) =>
          allowedClasses(taxonomy.hierarchy).map((option) => [
            option.class,
            taxonomy.id,
          ]),
        ),
    );
    selectedClassifications.forEach(async (classification) => {
      const { error } = await addClassification({
        taxonomy_id: taxonomyIds[classification],
        obj_id,
        classification,
        probability: 1,
      });
      if (!error) {
        dispatch(showNotification(`Classification ${classification} saved`));
      }
    });
    setSelectedClassifications([]);
    setDialogOpen(false);
  };

  return (
    <>
      <Tooltip title="Add Classifications">
        <IconButton
          onClick={() => setDialogOpen(true)}
          data-testid={`addClassificationsButton_${obj_id}`}
        >
          <AddIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
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
            onClick={onSubmit}
          >
            Add Classifications
          </Button>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default AddClassificationsScanningPage;
