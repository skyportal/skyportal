import { useEffect, useState } from "react";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import Select from "@mui/material/Select";
import Slider from "@mui/material/Slider";
import InputLabel from "@mui/material/InputLabel";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Paper from "@mui/material/Paper";
import Chip from "@mui/material/Chip";
import { makeStyles } from "tss-react/mui";
import { withStyles } from "tss-react/mui";
import { showNotification } from "baselayer/components/Notifications";
import Button from "../Button";
import {
  useAddClassificationMutation,
  useUpdateClassificationMutation,
} from "../../ducks/source";
import { useGetProfileQuery } from "../../ducks/profile";
import * as ClassificationsActions from "../../ducks/classifications";
import { useAppDispatch, useAppSelector } from "../../types/hooks";

interface MultipleClassificationsFormProps {
  objId: string;
  taxonomyList: any[];
  groupId?: number | null | undefined;
  currentClassifications: any[];
}

const useStyles = makeStyles()(() => ({
  container: {
    padding: "1rem",
  },
  taxonomySelect: {
    minWidth: "10rem",
    margin: "0.25rem 0",
  },
  sliderContainer: {
    display: "flex",
    flexFlow: "row wrap",
    "& > div": {
      padding: "1rem 2rem",
      margin: "0.5rem",
      flexGrow: "1",
      flexBasis: "15rem",
    },
  },
  submitButton: {
    margin: "1rem 0",
  },
}));

// For each node in the hierarchy tree, add its full path from root
// to the nodePaths list
const addNodePaths = (
  nodePaths: any[],
  hierarchy: any,
  prefix_path: any[] = [],
) => {
  const thisNodePath = [...prefix_path];

  if (
    hierarchy.class !== undefined &&
    hierarchy.class !== "Time-domain Source"
  ) {
    thisNodePath.push(hierarchy.class);
    nodePaths.push(thisNodePath);
  }

  hierarchy.subclasses?.forEach((item: any) => {
    if (typeof item === "object") {
      addNodePaths(nodePaths, item, thisNodePath);
    }
  });
};

// For each class in the hierarchy, return its name
// as well as the path from the root of hierarchy to that class
export const allowedClasses = (hierarchy: any) => {
  if (!hierarchy) {
    return null;
  }

  const classPaths: any[] = [];
  addNodePaths(classPaths, hierarchy);

  const classes = classPaths.map((path) => ({
    class: path.pop(),
    context: path.reverse(),
  }));

  return classes;
};

const MultipleClassificationsForm = ({
  objId,
  taxonomyList,
  groupId = null,
  currentClassifications,
}: MultipleClassificationsFormProps) => {
  const { classes } = useStyles();
  const dispatch = useAppDispatch();
  const [addClassification] = useAddClassificationMutation();
  const [updateClassification] = useUpdateClassificationMutation();
  const { data: currentUser } = useGetProfileQuery();
  const stateTaxonomy = useAppSelector(
    (state) => state["classifications"].taxonomy,
  );
  const [selectedTaxonomy, setSelectedTaxonomy] = useState<any>(stateTaxonomy);
  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);

  const latestTaxonomyList = taxonomyList?.filter((t: any) => t.isLatest);

  useEffect(() => {
    setSelectedTaxonomy(stateTaxonomy);
  }, [stateTaxonomy]);

  const scaleProbabilities = useAppSelector(
    (state) => state["classifications"].scaleProbabilities,
  );

  const [scaleProbabilitiesChecked, setScaleProbabilitiesChecked] =
    useState(scaleProbabilities);

  const handleScaleProbabilitiesSwitchChange = (event: any) => {
    setScaleProbabilitiesChecked(event.target.checked);
    dispatch(
      ClassificationsActions.setScaleProbabilities(event.target.checked),
    );
  };

  const updateExisting = useAppSelector(
    (state) => state["classifications"]["updateExisting"],
  );

  const handleUpdateExistingSwitchChange = (event: any) => {
    dispatch(ClassificationsActions.setUpdateExisting(event.target.checked));
  };

  const [formState, setFormState] = useState<any>({});

  useEffect(() => {
    const initialFormState: any = {};
    (taxonomyList?.filter((t: any) => t.isLatest) || []).forEach(
      (taxonomy: any) => {
        initialFormState[taxonomy?.id] = {};
      },
    );

    // Start each slider at the most recently modified classification for that
    // taxonomy/class, keeping its id so that further edits can update it in
    // place. Zero-probability classifications are kept too: they are explicit
    // "not this class" labels, not the absence of one.
    [...(currentClassifications || [])]
      .sort((a: any, b: any) => (a.modified < b.modified ? -1 : 1))
      .forEach((classification: any) => {
        if (!(classification.taxonomy_id in initialFormState)) {
          return;
        }
        initialFormState[classification.taxonomy_id][
          classification.classification
        ] = {
          depth: -1,
          probability: classification.probability || 0,
          savedProbability: classification.probability || 0,
          id: classification.id,
          authorName: classification.author_name,
        };
      });

    setFormState(initialFormState);
  }, [currentClassifications, taxonomyList]);

  // Whether the current user may edit a classification posted by `authorName`;
  // the backend enforces the same rule (Classification.update).
  const canUpdate = (entry: any) =>
    Boolean(
      updateExisting &&
      entry?.id &&
      (currentUser?.permissions?.includes("System admin") ||
        currentUser?.permissions?.includes("Manage groups") ||
        currentUser?.username === entry.authorName),
    );

  const getNode = (classification: any, path: any[]) => {
    // Get node from hierarchy, given classification name
    // and path to the classification
    let node: any;
    let hierarchy = selectedTaxonomy?.hierarchy.subclasses;
    const pathCopy = [...path];
    while (pathCopy.length > 0) {
      const ancestor = pathCopy.pop();
      node = hierarchy?.find((x: any) => x.class === ancestor);
      hierarchy = node?.subclasses;
    }

    // Covers the case where the node is a first-level node
    if (node?.class === classification) {
      return node;
    }

    node = hierarchy?.find((x: any) => x.class === classification);
    return node;
  };

  const listChildren = (node: any, newFormState: any) => {
    // List the probabilities of the children
    const children = node?.subclasses;
    const list: any[] = [];
    children?.forEach((subclass: any) => {
      list.push(
        newFormState[selectedTaxonomy.id][subclass.class]?.probability || 0,
      );
    });
    return list;
  };

  const updateChildren = (
    classification: any,
    newValue: number,
    newFormState: any,
    depth: number,
  ) => {
    classification?.subclasses?.forEach((subclass: any) => {
      const currentProbability =
        newFormState[selectedTaxonomy.id][subclass.class]?.probability || 0;
      // New probability is the min of the parent and child probabilities
      // No child probabilities may be greater than the parent probability
      const newProbability = Math.min(newValue, currentProbability) || 0;

      newFormState[selectedTaxonomy.id][subclass.class] = {
        ...newFormState[selectedTaxonomy.id][subclass.class],
        depth,
        probability: newProbability,
      };
      updateChildren(subclass, newProbability, newFormState, depth + 1);
    });
  };

  const handleChange = (newValue: number, classification: any, path: any[]) => {
    const newFormState = { ...formState };
    newFormState[selectedTaxonomy.id][classification] = {
      ...newFormState[selectedTaxonomy.id][classification],
      depth: path.length,
      probability: newValue,
    };

    // Probability normalization
    if (scaleProbabilitiesChecked) {
      // Update higher-level classification probabilities to be
      // the max of the subclasses' probabilities.
      path?.forEach((ancestor: any, i: number) => {
        const subpath = path.slice(i + 1);
        const probabilityOfSubclasses = Math.max(
          ...listChildren(getNode(ancestor, subpath), newFormState),
          0,
        );
        const probabilityOfAncestor =
          formState[selectedTaxonomy.id][ancestor]?.probability || 0;
        newFormState[selectedTaxonomy.id][ancestor] = {
          ...newFormState[selectedTaxonomy.id][ancestor],
          depth: subpath.length,
          probability: Math.max(probabilityOfSubclasses, probabilityOfAncestor),
        };
      });
      // Update children to be ≤ parent probability
      const node = getNode(classification, path);
      updateChildren(node, newValue, newFormState, path.length + 1);
    }
    setFormState(newFormState);
  };

  const renderSliders = (classifications: any, depth: number, path: any[]) =>
    classifications?.map((classification: any) => {
      const StyledSlider: any = withStyles(
        ({ classes: styles }: { classes?: any }) =>
          depth > 0 ? (
            <div className={styles.sliderDiv}>
              <Typography className={styles.sliderLabel} gutterBottom>
                {classification.class}
              </Typography>
              <Slider
                className={styles.slider}
                value={
                  formState[selectedTaxonomy.id][classification.class]
                    ?.probability || 0
                }
                onChangeCommitted={(_: any, value: any) =>
                  handleChange(value, classification.class, path)
                }
                id={classification.class}
                aria-labelledby={classification.class}
                valueLabelDisplay="auto"
                step={0.25}
                marks
                min={0}
                max={1.0}
              />
              {classification.class in (formState[selectedTaxonomy.id] || []) &&
                formState[selectedTaxonomy.id][classification.class]
                  ?.probability !== 0 &&
                renderSliders(
                  classification.subclasses,
                  depth + 1,
                  [classification.class].concat(path),
                )}
            </div>
          ) : (
            <Paper variant="outlined" className={styles.sliderDiv}>
              <Typography className={styles.sliderLabel} gutterBottom>
                {classification.class}
              </Typography>
              <Slider
                className={styles.slider}
                value={
                  (formState[selectedTaxonomy.id] || [])[classification.class]
                    ?.probability || 0
                }
                onChangeCommitted={(_: any, value: any) =>
                  handleChange(value, classification.class, path)
                }
                id={classification.class}
                aria-labelledby={classification.class}
                valueLabelDisplay="auto"
                step={0.25}
                marks
                min={0}
                max={1.0}
              />
              {classification.class in (formState[selectedTaxonomy.id] || []) &&
                formState[selectedTaxonomy.id][classification.class]
                  ?.probability !== 0 &&
                renderSliders(
                  classification.subclasses,
                  depth + 1,
                  [classification.class].concat(path),
                )}
            </Paper>
          ),
        {
          sliderDiv: {
            textAlign: "end",
          },
          slider: {
            width: `calc(100% * (1 - .15 * ${depth}))`,
          },
          sliderLabel: {
            width: `calc(100% * (1 - .15 * ${depth}))`,
            marginLeft: `calc(100% * .15 * ${depth})`,
            textAlign: "left",
          },
        },
      );
      return <StyledSlider key={`${classification.class}`} />;
    });

  const handleSelectTaxonomy = (event: any) => {
    setSelectedTaxonomy(event.target.value);
    dispatch(ClassificationsActions.setTaxonomy(event.target.value));
  };

  // Helper function to loop through array while waiting for
  // each item to finish an async function
  // Adapted from: https://codeburst.io/javascript-async-await-with-foreach-b6ba62bbf404
  const asyncForEach = async (array: any[], callback: any) => {
    for (let index = 0; index < array.length; index += 1) {
      // eslint-disable-next-line no-await-in-loop
      await callback(array[index], index, array);
    }
  };

  const getClassificationsToSubmit = (classifications: any) => {
    if (!classifications) {
      return null;
    }

    const toSubmit = (Object.entries(classifications) as [string, any][])
      // Only submit classifications that have been edited (depth > -1). A zero
      // probability is only meaningful as an update to an existing
      // classification: posting new ones would flood the source with the zeroed
      // subclasses that scaling writes into the form state.
      .filter(
        ([, entry]) =>
          entry.depth > -1 && (entry.probability > 0 || canUpdate(entry)),
      );
    // Post lower depths first (more specific classifications will be added
    // later, to be the most recent when fetched)
    toSubmit.sort((a, b) => a[1].depth - b[1].depth);
    return toSubmit;
  };

  const handleSubmit = async () => {
    setSubmissionRequestInProcess(true);
    const results: boolean[] = [];

    const classifications = formState[selectedTaxonomy?.id];

    // Submit the edited classifications for the current taxonomy
    const toSubmit = getClassificationsToSubmit(classifications);
    await asyncForEach(
      toSubmit ?? [],
      async ([classification, entry]: [string, any]) => {
        const data: any = {
          taxonomy_id: selectedTaxonomy.id,
          obj_id: objId,
          classification,
          probability: entry.probability,
        };
        try {
          if (canUpdate(entry)) {
            // No group_ids: an update must not narrow the groups the existing
            // classification is already shared with.
            await updateClassification({
              classificationID: entry.id,
              formData: data,
            }).unwrap();
          } else {
            if (groupId) {
              data.group_ids = [groupId];
            }
            await addClassification(data).unwrap();
          }
          results.push(true);
        } catch {
          results.push(false);
        }
      },
    );

    // Reset the depths for the submitted classifications so that they
    // are not resubmitted upon further edits
    const newFormState = { ...formState };
    toSubmit?.forEach(([classification, entry]: [string, any]) => {
      newFormState[selectedTaxonomy.id][classification] = {
        ...entry,
        depth: -1,
        savedProbability: entry.probability,
      };
    });
    setFormState(newFormState);

    setSubmissionRequestInProcess(false);
    if (results.every((result) => result)) {
      dispatch(showNotification("Classifications saved."));
    }
  };

  return (
    <div className={classes.container}>
      <Typography variant="h6">Post Classifications</Typography>
      <div>
        <Typography variant="subtitle2">
          Classifications to be submitted:
        </Typography>
        {getClassificationsToSubmit(formState[selectedTaxonomy?.id])?.map(
          ([classification, entry]: [string, any]) => (
            <Chip
              key={`${selectedTaxonomy.id}-${classification}`}
              variant={canUpdate(entry) ? "outlined" : "filled"}
              label={
                canUpdate(entry)
                  ? `${classification} (${selectedTaxonomy.name}): ${entry.savedProbability} → ${entry.probability}`
                  : `${classification} (${selectedTaxonomy.name}): ${entry.probability}`
              }
            />
          ),
        )}
      </div>
      <FormControl className={classes.taxonomySelect}>
        <InputLabel id={`taxonomy-select-label-${objId}`}>
          Select Taxonomy
        </InputLabel>
        <Select
          labelId={`taxonomy-select-label-${objId}`}
          label="Select Taxonomy"
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          id={`taxonomy-select-${objId}`}
          value={selectedTaxonomy || ""}
          onChange={handleSelectTaxonomy}
        >
          {latestTaxonomyList?.map((taxonomy: any) => (
            <MenuItem key={taxonomy.name} value={taxonomy}>
              {taxonomy.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <div>
        <FormControlLabel
          control={
            <Switch
              checked={scaleProbabilities || false}
              onChange={handleScaleProbabilitiesSwitchChange}
              slotProps={{ input: { "aria-label": "controlled" } }}
            />
          }
          label="Scale parent/child probabilities"
        />
        <FormControlLabel
          control={
            <Switch
              checked={updateExisting || false}
              onChange={handleUpdateExistingSwitchChange}
              slotProps={{ input: { "aria-label": "controlled" } }}
              name="updateExistingClassifications"
            />
          }
          label="Update existing classifications"
        />
      </div>
      {selectedTaxonomy?.hierarchy?.subclasses?.map((category: any) => (
        <Accordion
          className={(classes as any).classifications}
          key={`${category.class}`}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="classifications-content"
          >
            <Typography
              variant="subtitle1"
              className={(classes as any).accordionHeading}
            >
              {category.class}
            </Typography>
          </AccordionSummary>
          <AccordionDetails className={classes.sliderContainer}>
            {renderSliders(category.subclasses, 0, [category.class])}
          </AccordionDetails>
        </Accordion>
      ))}
      <div className={classes.submitButton}>
        <Button
          primary
          type="submit"
          name="submitClassificationsButton"
          disabled={submissionRequestInProcess}
          onClick={handleSubmit}
        >
          Submit classifications
        </Button>
      </div>
    </div>
  );
};

export default MultipleClassificationsForm;
