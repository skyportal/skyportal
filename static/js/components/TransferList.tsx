import * as React from "react";
import Grid from "@mui/material/Grid";
import List from "@mui/material/List";
import Card from "@mui/material/Card";
import CardHeader from "@mui/material/CardHeader";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import ListItemIcon from "@mui/material/ListItemIcon";
import Checkbox from "@mui/material/Checkbox";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";

import { intersection, not, union } from "../utils";

interface TransferListItem {
  id: number | string;
  label?: string;
  [key: string]: any;
}

interface TransferListProps {
  left: TransferListItem[];
  right: TransferListItem[];
  setLeft: (...args: any[]) => void;
  setRight: (...args: any[]) => void;
  leftLabel?: string;
  rightLabel?: string;
}

const TransferList = ({
  left,
  right,
  setLeft,
  setRight,
  leftLabel = "Choices",
  rightLabel = "Chosen",
}: TransferListProps) => {
  const [checked, setChecked] = React.useState<TransferListItem[]>([]);

  const leftChecked = intersection(checked, left);
  const rightChecked = intersection(checked, right);

  const handleToggle = (value: TransferListItem) => () => {
    const currentIndex = checked.findIndex((item) => item.id === value.id);
    const newChecked = [...checked];

    if (currentIndex === -1) {
      newChecked.push(value);
    } else {
      newChecked.splice(currentIndex, 1);
    }

    setChecked(newChecked);
  };

  const numberOfChecked = (items: TransferListItem[]) =>
    intersection(checked, items).length;

  const handleToggleAll = (items: TransferListItem[]) => () => {
    if (numberOfChecked(items) === items.length) {
      setChecked(not(checked, items));
    } else {
      setChecked(union(checked, items));
    }
  };

  const handleCheckedRight = () => {
    const newRight = right
      .concat(leftChecked)
      .sort((a, b) => (a?.label ?? "").localeCompare(b?.label ?? ""));
    const newLeft = not(left, leftChecked).sort((a: any, b: any) =>
      a?.label?.localeCompare(b?.label),
    );
    const newChecked = not(checked, leftChecked).sort((a: any, b: any) =>
      a?.label?.localeCompare(b?.label),
    );
    setRight(newRight);
    setLeft(newLeft);
    setChecked(newChecked);
  };

  const handleCheckedLeft = () => {
    const newLeft = left
      .concat(rightChecked)
      .sort((a, b) => (a?.label ?? "").localeCompare(b?.label ?? ""));
    const newRight = not(right, rightChecked).sort((a: any, b: any) =>
      a?.label?.localeCompare(b?.label),
    );
    const newChecked = not(checked, rightChecked).sort((a: any, b: any) =>
      a?.label?.localeCompare(b?.label),
    );
    setLeft(newLeft);
    setRight(newRight);
    setChecked(newChecked);
  };

  const customList = (title: string, items: TransferListItem[]) => (
    <Card>
      <CardHeader
        sx={{ px: 2, py: 1 }}
        avatar={
          <Checkbox
            onClick={handleToggleAll(items)}
            checked={
              numberOfChecked(items) === items.length && items.length !== 0
            }
            indeterminate={
              numberOfChecked(items) !== items.length &&
              numberOfChecked(items) !== 0
            }
            disabled={items.length === 0}
            inputProps={{
              "aria-label": "all items selected",
            }}
          />
        }
        title={title}
        subheader={`${numberOfChecked(items)}/${items.length} selected`}
      />
      <Divider />
      <List
        sx={{
          width: "100%",
          height: "100%",
          maxHeight: "60vh",
          bgcolor: "background.paper",
          overflow: "auto",
        }}
        dense
        component="div"
        role="list"
      >
        {items.map((item) => {
          const labelId = `transfer-list-all-item-${item.id}-label`;

          return (
            <ListItemButton
              key={item.id}
              role="listitem"
              onClick={handleToggle(item)}
            >
              <ListItemIcon>
                <Checkbox
                  checked={checked.findIndex((i) => i.id === item.id) !== -1}
                  tabIndex={-1}
                  disableRipple
                  inputProps={{
                    "aria-labelledby": labelId,
                  }}
                />
              </ListItemIcon>
              <ListItemText id={String(item.id)} primary={item.label} />
            </ListItemButton>
          );
        })}
      </List>
    </Card>
  );

  return (
    <Grid
      container
      size={12}
      spacing={1}
      justifyContent="center"
      alignItems="baseline"
    >
      <Grid size={5}>{customList(leftLabel || "Choices", left)}</Grid>
      <Grid size={2}>
        <Grid container direction="column" alignItems="center">
          <Button
            sx={{ my: 0.5 }}
            variant="outlined"
            size="small"
            onClick={handleCheckedRight}
            disabled={leftChecked.length === 0}
            aria-label="move selected right"
          >
            &gt;
          </Button>
          <Button
            sx={{ my: 0.5 }}
            variant="outlined"
            size="small"
            onClick={handleCheckedLeft}
            disabled={rightChecked.length === 0}
            aria-label="move selected left"
          >
            &lt;
          </Button>
        </Grid>
      </Grid>
      <Grid size={5}>{customList(rightLabel || "Chosen", right)}</Grid>
    </Grid>
  );
};

export default TransferList;
