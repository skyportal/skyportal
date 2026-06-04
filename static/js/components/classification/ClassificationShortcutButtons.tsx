import { useAppSelector } from "../../types/hooks";
import Button from "../Button";

interface ClassificationShortcutButtonsProps {
  selectedClassifications: string[];
  setSelectedClassifications: (...args: any[]) => void;
  inDialog?: boolean;
}

const ClassificationShortcutButtons = ({
  selectedClassifications,
  setSelectedClassifications,
  inDialog = false,
}: ClassificationShortcutButtonsProps) => {
  const { classificationShortcuts } = useAppSelector(
    (state) => state.profile.preferences,
  ) as any;
  if (!classificationShortcuts) return null;

  const handleClassificationShortcutClick = (
    shortcutClassifications: string[],
  ) => {
    setSelectedClassifications([
      ...new Set([...selectedClassifications, ...shortcutClassifications]),
    ]);
  };

  return Object.entries(classificationShortcuts)?.map(
    ([shortcutName, shortcutClassifications]) => (
      <Button
        secondary
        key={shortcutName}
        data-testid={shortcutName + (inDialog ? `_inDialog` : "")}
        onClick={() =>
          handleClassificationShortcutClick(shortcutClassifications as string[])
        }
      >
        Select {shortcutName}
      </Button>
    ),
  );
};

export default ClassificationShortcutButtons;
