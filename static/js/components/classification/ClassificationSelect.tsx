import Box from "@mui/material/Box";
import { useAppSelector } from "../../types/hooks";
import { allowedClasses } from "./ClassificationForm";
import ClassificationShortcutButtons from "./ClassificationShortcutButtons";
import SelectWithChips from "../SelectWithChips";

interface ClassificationSelectProps {
  selectedClassifications: string[];
  setSelectedClassifications: (...args: any[]) => void;
  showShortcuts?: boolean;
  inDialog?: boolean;
}

const ClassificationSelect = ({
  selectedClassifications,
  setSelectedClassifications,
  showShortcuts = false,
  inDialog = false,
}: ClassificationSelectProps) => {
  const { taxonomyList } = useAppSelector((state) => state.taxonomies);
  const latestTaxonomyList = taxonomyList?.filter((t: any) => t.isLatest);
  let classifications: string[] = [];
  latestTaxonomyList?.forEach((taxonomy: any) => {
    const currentClasses = allowedClasses(taxonomy.hierarchy)?.map(
      (option: any) => option.class,
    );
    classifications = classifications.concat(currentClasses);
  });
  classifications = Array.from(new Set(classifications)).sort();

  return (
    <>
      <SelectWithChips
        label="Classifications"
        id="classifications-select"
        initValue={selectedClassifications}
        onChange={(e: any) => setSelectedClassifications(e.target.value)}
        options={classifications}
      />
      {showShortcuts && (
        <Box sx={{ mt: "0.4rem" }}>
          <ClassificationShortcutButtons
            selectedClassifications={selectedClassifications}
            setSelectedClassifications={setSelectedClassifications}
            inDialog={inDialog}
          />
        </Box>
      )}
    </>
  );
};

export default ClassificationSelect;
