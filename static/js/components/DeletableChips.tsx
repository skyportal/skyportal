import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";

interface DeletableChipsProps {
  items: string[];
  onDelete: (item: string) => void;
  title: string;
}

const DeletableChips = ({ items, onDelete, title }: DeletableChipsProps) => (
  <div>
    <Typography>{title}</Typography>
    {items?.map((item) => (
      <Chip key={item} label={item} onDelete={() => onDelete(item)} />
    ))}
  </div>
);

export default DeletableChips;
