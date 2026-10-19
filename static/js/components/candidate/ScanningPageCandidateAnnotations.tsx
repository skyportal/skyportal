import { useState } from "react";

import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Collapse from "@mui/material/Collapse";
import ExpandLess from "@mui/icons-material/ExpandLess";
import ExpandMore from "@mui/icons-material/ExpandMore";
import Divider from "@mui/material/Divider";
import Paper from "@mui/material/Paper";
import TextField from "@mui/material/TextField";

import ConfirmSourceInGCN from "../source/ConfirmSourceInGCN";
import { useAppDispatch, useAppSelector } from "../../types/hooks";
import * as candidatesActions from "../../ducks/candidate/candidates";
import type { Annotation, Group } from "../../types";
import { getAnnotationValueString } from "./annotationValue";

export { getAnnotationValueString };

const GCN_CROSSMATCH_ORIGIN = "GCN-crossmatch";

const nestedSx = { pl: 4, py: 0 };
const rowTextSlotProps = { secondary: { sx: { maxWidth: 200 } } };

const isFilterGroupOrigin = (origin: string, groups: Group[]) =>
  groups.some(({ name, nickname }) =>
    [name, nickname || name].some((label) =>
      origin.toLowerCase().includes(label.toLowerCase()),
    ),
  );

const crossmatchedEvents = (data: Annotation["data"]) =>
  Object.entries(data).flatMap(([triggerId, payload]) => {
    const dateobs = (payload as { dateobs?: string } | null)?.dateobs;
    return dateobs ? [{ triggerId, dateobs }] : [];
  });

interface ScanningPageCandidateAnnotationsProps {
  annotations: Annotation[];
  filterGroups?: Group[];
}

const ScanningPageCandidateAnnotations = ({
  annotations,
  filterGroups = [],
}: ScanningPageCandidateAnnotationsProps) => {
  const dispatch = useAppDispatch();
  const selectedSort = useAppSelector(
    (state) => state.candidates.selectedAnnotationSortOptions,
  );
  const [openedOrigins, setOpenedOrigins] = useState<Record<string, boolean>>(
    () => Object.fromEntries(annotations.map(({ origin }) => [origin, true])),
  );
  const [search, setSearch] = useState("");

  const rank = ({ origin }: Annotation) =>
    isFilterGroupOrigin(origin, filterGroups) ? 0 : 1;
  // RTK Query data is frozen: copy before sorting.
  const sortedAnnotations = [...annotations]
    .sort((a, b) => rank(a) - rank(b) || a.origin.localeCompare(b.origin))
    .map((annotation) => ({
      ...annotation,
      data: Object.fromEntries(
        Object.entries(annotation.data).sort(([a], [b]) => a.localeCompare(b)),
      ),
    }));

  const query = search.trim().toLowerCase();
  const matches = (text: string) => text.toLowerCase().includes(query);
  const filteredAnnotations = query
    ? sortedAnnotations.flatMap((annotation) => {
        if (matches(annotation.origin)) return [annotation];
        const entries = Object.entries(annotation.data).filter(
          ([key, value]) =>
            matches(key) || matches(getAnnotationValueString(value)),
        );
        return entries.length
          ? [{ ...annotation, data: Object.fromEntries(entries) }]
          : [];
      })
    : sortedAnnotations;

  const isSelected = (origin: string, key: string) =>
    selectedSort?.origin === origin && selectedSort?.key === key;

  const toggleSort = (origin: string, key: string) =>
    dispatch(
      candidatesActions.setCandidatesAnnotationSortOptions(
        isSelected(origin, key) ? null : { origin, key, order: null },
      ),
    );

  return (
    <Paper variant="outlined">
      <TextField
        sx={{ p: 0.5 }}
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
        dense
        disablePadding
        sx={{ maxHeight: "24rem", overflowY: "auto" }}
      >
        {filteredAnnotations.map(({ origin, obj_id, data }) => {
          const isOpen = Boolean(query) || openedOrigins[origin];
          return (
            <div key={origin}>
              <Divider />
              <ListItemButton
                sx={{
                  position: "sticky",
                  top: 0,
                  zIndex: 1,
                  bgcolor: "background.paper",
                }}
                onClick={() =>
                  setOpenedOrigins((opened) => ({
                    ...opened,
                    [origin]: !opened[origin],
                  }))
                }
              >
                <ListItemText
                  primary={origin}
                  slotProps={{ primary: { variant: "button" } }}
                />
                {isOpen ? <ExpandLess /> : <ExpandMore />}
              </ListItemButton>
              <Collapse in={isOpen} timeout="auto" unmountOnExit>
                <List
                  component="div"
                  dense
                  disablePadding
                  sx={{ maxWidth: 250 }}
                >
                  {origin === GCN_CROSSMATCH_ORIGIN &&
                    obj_id &&
                    crossmatchedEvents(data).map(({ triggerId, dateobs }) => (
                      <ListItem key={`vet_${triggerId}`} sx={nestedSx}>
                        <ListItemText
                          slotProps={rowTextSlotProps}
                          secondary={`vet ${triggerId}`}
                        />
                        <ConfirmSourceInGCN
                          compact
                          dateobs={dateobs}
                          source_id={obj_id}
                          sources_id_list={[obj_id]}
                        />
                      </ListItem>
                    ))}
                  {Object.entries(data).map(([key, value]) => (
                    <ListItemButton
                      key={key}
                      sx={nestedSx}
                      selected={isSelected(origin, key)}
                      onClick={() => toggleSort(origin, key)}
                    >
                      <ListItemText
                        slotProps={rowTextSlotProps}
                        secondary={`${key}: ${getAnnotationValueString(value)}`}
                      />
                    </ListItemButton>
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
