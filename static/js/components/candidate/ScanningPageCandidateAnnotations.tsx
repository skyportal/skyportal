import { useState } from "react";

import { makeStyles } from "tss-react/mui";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Collapse from "@mui/material/Collapse";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import Divider from "@mui/material/Divider";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";

import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as candidatesActions from "../../ducks/candidate/candidates";
import type { Annotation, Group } from "../../types";

const useStyles = makeStyles()((theme) => ({
  root: {
    width: "100%",
    background: theme.palette.background.paper,
    padding: 0,
    margin: 0,
    maxHeight: "24rem",
    overflowY: "scroll",
    // Prevent disabled annotations from being selected, but display normally for readability
    "& .Mui-disabled": {
      opacity: 1,
    },
  },
  nested: {
    paddingLeft: theme.spacing(4),
    paddingTop: 0,
    paddingBottom: 0,
  },
  // Keep the origin header visible while scrolling through its annotations.
  stickyOrigin: {
    position: "sticky",
    top: 0,
    zIndex: 1,
    background: theme.palette.background.paper,
  },
  search: {
    padding: theme.spacing(0.5),
  },
}));

export const getAnnotationValueString = (value: any): string => {
  let valueString;
  const valueType = typeof value;
  switch (valueType) {
    case "number":
      valueString = value.toFixed(4);
      break;
    case "object":
      valueString = JSON.stringify(value, null, 2);
      break;
    default:
      valueString = value.toString();
  }
  return valueString;
};

interface ScanningPageCandidateAnnotationsProps {
  annotations: Annotation[];
  filterGroups?: Group[];
  listWidth?: number;
  listItemWidth?: number;
}

const ScanningPageCandidateAnnotations = ({
  annotations,
  filterGroups = [],
  listWidth = 250,
  listItemWidth = 200,
}: ScanningPageCandidateAnnotationsProps) => {
  const { classes } = useStyles();

  const dispatch = useAppDispatch();

  // `annotations` is frozen RTK Query data, so copy before sorting in place.
  annotations = [...(annotations ?? [])].sort((a, b) =>
    a.origin.localeCompare(b.origin),
  );
  if (filterGroups?.length > 0) {
    // put the filter groups at the top
    annotations.sort((a, b) => {
      const aIsFilterGroup = filterGroups.some((group) => {
        const name = group.name ? group.name.toLowerCase() : "";
        const nickname = group.nickname ? group.nickname.toLowerCase() : name;
        const origin = a.origin.toLowerCase();
        return origin.includes(nickname) || origin.includes(name);
      });
      const bIsFilterGroup = filterGroups.some((group) => {
        const name = group.name ? group.name.toLowerCase() : "";
        const nickname = group.nickname ? group.nickname.toLowerCase() : name;
        const origin = b.origin.toLowerCase();
        return origin.includes(nickname) || origin.includes(name);
      });
      if (aIsFilterGroup && !bIsFilterGroup) {
        return -1;
      }
      if (!aIsFilterGroup && bIsFilterGroup) {
        return 1;
      }
      return 0;
    });
  }
  // The annotation objects are frozen RTK Query data, so build new objects
  // with sorted `data` rather than mutating them in place.
  annotations = annotations?.map((annotation) => ({
    ...annotation,
    data: Object.fromEntries(
      Object.entries(annotation.data).sort((a, b) => a[0].localeCompare(b[0])),
    ),
  }));

  const initState: Record<string, boolean> = {};
  annotations?.forEach((annotation) => {
    initState[annotation.origin] = true;
  });
  const [openedOrigins, setOpenedOrigins] = useState(initState);
  const [search, setSearch] = useState("");

  // Filter by origin name or any key/value text. An origin whose name matches
  // keeps all its entries; otherwise only its matching entries are kept.
  const query = search.trim().toLowerCase();
  const filteredAnnotations: Annotation[] = query
    ? annotations.reduce<Annotation[]>((acc, annotation) => {
        if (annotation.origin.toLowerCase().includes(query)) {
          acc.push(annotation);
          return acc;
        }
        const entries = Object.entries(annotation.data).filter(
          ([key, value]) =>
            key.toLowerCase().includes(query) ||
            getAnnotationValueString(value).toLowerCase().includes(query),
        );
        if (entries.length > 0) {
          acc.push({ ...annotation, data: Object.fromEntries(entries) });
        }
        return acc;
      }, [])
    : annotations;

  const selectedAnnotationSortOptions = useAppSelector(
    (state) => (state as any).candidates.selectedAnnotationSortOptions,
  );

  const handleClick = (origin: string) => {
    setOpenedOrigins({ ...openedOrigins, [origin]: !openedOrigins[origin] });
  };

  const handleItemSelect = (origin: string, key: string) => {
    const currentlySelected =
      selectedAnnotationSortOptions &&
      selectedAnnotationSortOptions.origin === origin &&
      selectedAnnotationSortOptions.key === key;

    const annotationItem: any = currentlySelected
      ? null
      : { origin, key, order: null };
    dispatch(
      candidatesActions.setCandidatesAnnotationSortOptions(annotationItem),
    );
  };

  return (
    <Paper variant="outlined">
      <TextField
        className={classes.search}
        size="small"
        fullWidth
        variant="standard"
        placeholder="Filter annotations..."
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        slotProps={{
          htmlInput: {
            "aria-label": "Filter annotations",
            "data-testid": "annotationSearchInput",
          },
        }}
      />
      <List
        component="nav"
        aria-labelledby="nested-list-subheader"
        className={classes.root}
        dense
      >
        {filteredAnnotations.map((annotation) => {
          // While searching, force matching origins open so results show.
          const isOpen = query ? true : openedOrigins[annotation.origin];
          return (
            <div key={`annotation_${annotation.origin}`}>
              <Divider />
              <ListItem
                {...({ button: true } as any)}
                className={classes.stickyOrigin}
                onClick={() => handleClick(annotation.origin)}
              >
                <ListItemText
                  primary={`${annotation.origin}`}
                  slotProps={{ primary: { variant: "button" } }}
                />
                {isOpen ? <ExpandLess /> : <ExpandMore />}
              </ListItem>
              <Collapse in={isOpen} timeout="auto" unmountOnExit>
                <List
                  component="div"
                  sx={{ maxWidth: listWidth }}
                  dense
                  disablePadding
                >
                  {Object.entries(annotation.data).map(([key, value]) => (
                    <ListItem
                      key={`key_${annotation.origin}_${key}`}
                      {...({ button: true } as any)}
                      className={classes.nested}
                      selected={
                        selectedAnnotationSortOptions &&
                        selectedAnnotationSortOptions.origin ===
                          annotation.origin &&
                        selectedAnnotationSortOptions.key === key
                      }
                      onClick={() => handleItemSelect(annotation.origin, key)}
                    >
                      <ListItemText
                        slotProps={{
                          secondary: { sx: { maxWidth: listItemWidth } },
                        }}
                        secondary={`${key}: ${getAnnotationValueString(value)}`}
                      />
                    </ListItem>
                  ))}
                </List>
              </Collapse>
              <Divider />
            </div>
          );
        })}
      </List>
    </Paper>
  );
};

export default ScanningPageCandidateAnnotations;
