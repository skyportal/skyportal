import React, { useState, useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import PropTypes from "prop-types";
import MenuItem from "@material-ui/core/MenuItem";
import Typography from "@material-ui/core/Typography";
import Select from "@material-ui/core/Select";
import Slider from "@material-ui/core/Slider";
import InputLabel from "@material-ui/core/InputLabel";
import FormControl from "@material-ui/core/FormControl";
import Accordion from "@material-ui/core/Accordion";
import AccordionSummary from "@material-ui/core/AccordionSummary";
import AccordionDetails from "@material-ui/core/AccordionDetails";
import ExpandMoreIcon from "@material-ui/icons/ExpandMore";
import Button from "@material-ui/core/Button";
import Paper from "@material-ui/core/Paper";
import Chip from "@material-ui/core/Chip";
import { makeStyles, withStyles } from "@material-ui/core/styles";

import { showNotification } from "baselayer/components/Notifications";
import { getSortedClasses } from "./ShowClassification";
import * as Actions from "../ducks/source";
import * as ClassificationsActions from "../ducks/classifications";

const useStyles = makeStyles(() => ({
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
const addNodePaths = (nodePaths, hierarchy, prefix_path = []) => {
  const thisNodePath = [...prefix_path];

  if (
    hierarchy.class !== undefined &&
    hierarchy.class !== "Time-domain Source"
  ) {
    thisNodePath.push(hierarchy.class);
    nodePaths.push(thisNodePath);
  }

  hierarchy.subclasses?.forEach((item) => {
    if (typeof item === "object") {
      addNodePaths(nodePaths, item, thisNodePath);
    }
  });
};

// For each class in the hierarchy, return its name
// as well as the path from the root of hierarchy to that class
export const allowedClasses = (hierarchy) => {
  if (!hierarchy) {
    return null;
  }

  const classPaths = [];
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
  groupId,
  currentClassifications,
}) => {
  const classes = useStyles();
  const dispatch = useDispatch();
  const stateTaxonomy = useSelector((state) => state.classifications.taxonomy);
  const [selectedTaxonomy, setSelectedTaxonomy] = useState(stateTaxonomy);
  const [submissionRequestInProcess, setSubmissionRequestInProcess] =
    useState(false);

  const latestTaxonomyList = taxonomyList?.filter((t) => t.isLatest);

  useEffect(() => {
    setSelectedTaxonomy(stateTaxonomy);
  }, [stateTaxonomy]);

  const initialFormState = {};
  latestTaxonomyList.forEach((taxonomy) => {
    initialFormState[taxonomy.id] = {};
  });
  const sortedClassifications = getSortedClasses(currentClassifications);

  // For each existing taxonomy/classification, update initial sliders
  sortedClassifications.forEach((classifications) => {
    classifications.forEach((classification) => {
      // Take just the latest values for each field
      if (
        !initialFormState[classification.taxonomy_id][
          classification.classification
        ]
      ) {
        initialFormState[classification.taxonomy_id][
          classification.classification
        ] = { depth: -1, probability: classification.probability };
      }
    });
  });
  const [formState, setFormState] = useState(initialFormState);

  const getNode = (classification, path) => {
    // Get node from hierarchy, given classification name
    // and path to the classification
    let node;
    let hierarchy = selectedTaxonomy?.hierarchy.subclasses;
    const pathCopy = [...path];
    while (pathCopy.length > 0) {
      const ancestor = pathCopy.pop();
      node = hierarchy?.find((x) => x.class === ancestor);
      hierarchy = node?.subclasses;
    }

    // Covers the case where the node is a first-level node
    if (node?.class === classification) {
      return node;
    }

    node = hierarchy?.find((x) => x.class === classification);
    return node;
  };

  const sumChildren = (node, newFormState) => {
    // Sum the probabilities of the children
    const children = node?.subclasses;
    let sum = 0;
    children?.forEach((subclass) => {
      sum +=
        newFormState[selectedTaxonomy.id][subclass.class]?.probability || 0;
    });

    return sum;
  };

  const updateChildren = (classification, newValue, newFormState, depth) => {
    const totalProbabilityOfSubclasses = sumChildren(
      classification,
      newFormState
    );
    classification?.subclasses?.forEach((subclass) => {
      const currentProbability =
        newFormState[selectedTaxonomy.id][subclass.class]?.probability || 0;
      // New probability is the new parent probability scaled by the
      // proportion of the total children probability this child has currently
      // Note: "|| 0" used to handle cases where totalProbabilityOfSubclasses === 0
      const newProbability =
        parseFloat(
          (
            (newValue * currentProbability) /
            totalProbabilityOfSubclasses
          ).toFixed(3)
        ) || 0;
      newFormState[selectedTaxonomy.id][subclass.class] = {
        depth,
        probability: newProbability,
      };
      updateChildren(subclass, newProbability, newFormState, depth + 1);
    });
  };

  const handleChange = (newValue, classification, path) => {
    const newFormState = { ...formState };
    newFormState[selectedTaxonomy.id][classification] = {
      depth: path.length,
      probability: newValue,
    };

    // Update higher-level classification probabilities to be
    // the sum of the subclasses' probabilities.
    path.forEach((ancestor, i) => {
      const subpath = path.slice(i + 1);
      const probabilityOfSubclasses = Math.min(
        sumChildren(getNode(ancestor, subpath), newFormState),
        1
      );
      newFormState[selectedTaxonomy.id][ancestor] = {
        depth: subpath.length,
        probability: probabilityOfSubclasses,
      };

      // Update siblings of the ancestor to respect cap of parent
      if (subpath.length > 0) {
        const parent = getNode(subpath[0], subpath);
        const remainingProbability =
          newFormState[selectedTaxonomy.id][parent.class]?.probability -
          newFormState[selectedTaxonomy.id][ancestor].probability;

        const siblings = parent.subclasses?.filter(
          (sibling) => sibling.class !== ancestor
        );
        let currentTotalOfSiblings = 0;
        siblings?.forEach((sibling) => {
          currentTotalOfSiblings +=
            newFormState[selectedTaxonomy.id][sibling.class]?.probability || 0;
        });
        siblings.forEach((sibling) => {
          const currentProbability =
            newFormState[selectedTaxonomy.id][sibling.class]?.probability || 0;
          // Scale the siblings' probabilities based on the proportion they had
          // previously of the parent's probability.
          // Note: "|| 0" used to handle cases where currentTotalOfSiblings === 0
          const newProbability =
            parseFloat(
              (
                remainingProbability *
                (currentProbability / currentTotalOfSiblings)
              ).toFixed(3)
            ) || 0;
          newFormState[selectedTaxonomy.id][sibling.class] = {
            depth: subpath.length,
            probability: newProbability,
          };
        });
      }
    });

    // Update siblings of actual node to respect cap of parent
    if (path.length > 0) {
      const parent = getNode(path[0], path.slice(1));
      const remainingProbability =
        newFormState[selectedTaxonomy.id][parent.class]?.probability - newValue;

      const siblings = parent.subclasses?.filter(
        (sibling) => sibling.class !== classification
      );
      let currentTotalOfSiblings = 0;
      siblings?.forEach((sibling) => {
        currentTotalOfSiblings +=
          newFormState[selectedTaxonomy.id][sibling.class]?.probability || 0;
      });
      siblings.forEach((sibling) => {
        const currentProbability =
          newFormState[selectedTaxonomy.id][sibling.class]?.probability || 0;
        // Scale the siblings' probabilities based on the proportion they had
        // previously of the parent's probability.
        // Note: "|| 0" used to handle cases where currentTotalOfSiblings === 0
        const newProbability =
          parseFloat(
            (
              remainingProbability *
              (currentProbability / currentTotalOfSiblings)
            ).toFixed(3)
          ) || 0;
        newFormState[selectedTaxonomy.id][sibling.class] = {
          depth: path.length,
          // Scale the siblings' probabilities based on the proportion they had
          // previously of the parent's probability.
          probability: newProbability,
        };
        updateChildren(sibling, newProbability, newFormState, path.length + 1);
      });
    }

    // Update subclasses' probabilities
    const node = getNode(classification, path);
    updateChildren(node, newValue, newFormState, path.length + 1);
    setFormState(newFormState);
  };

  const renderSliders = (classifications, depth, path) =>
    classifications?.map((classification) => {
      const StyledSlider = withStyles({
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
      })(({ classes: styles }) =>
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
              onChangeCommitted={(_, value) =>
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
            {renderSliders(
              classification.subclasses,
              depth + 1,
              [classification.class].concat(path)
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
                formState[selectedTaxonomy.id][classification.class]
                  ?.probability || 0
              }
              onChangeCommitted={(_, value) =>
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
            {renderSliders(
              classification.subclasses,
              depth + 1,
              [classification.class].concat(path)
            )}
          </Paper>
        )
      );
      return <StyledSlider key={`${classification.class}`} />;
    });

  const handleSelectTaxonomy = (event) => {
    setSelectedTaxonomy(event.target.value);
    dispatch(ClassificationsActions.setTaxonomy(event.target.value));
  };

  // Helper function to loop through array while waiting for
  // each item to finish an async function
  // Adapted from: https://codeburst.io/javascript-async-await-with-foreach-b6ba62bbf404
  const asyncForEach = async (array, callback) => {
    for (let index = 0; index < array.length; index += 1) {
      // eslint-disable-next-line no-await-in-loop
      await callback(array[index], index, array);
    }
  };

  const getClassificationsToPost = (classifications) => {
    if (!classifications) {
      return null;
    }

    const toPost = Object.entries(classifications)
      // Only submit non-zero classifications that have been
      // edited (depth > -1)
      .filter(([, { depth, probability }]) => probability > 0 && depth > -1);
    // Post lower depths first (more specific classifications will be added
    // later, to be the most recent when fetched)
    toPost.sort((a, b) => a[1].depth - b[1].depth);
    return toPost;
  };

  const handleSubmit = async () => {
    setSubmissionRequestInProcess(true);
    const results = [];

    const classifications = formState[selectedTaxonomy?.id];

    // Submit non-zero classifications for the current taxonomy
    const toPost = getClassificationsToPost(classifications);
    asyncForEach(toPost, async ([classification, { probability }]) => {
      const data = {
        taxonomy_id: selectedTaxonomy.id,
        obj_id: objId,
        classification,
        probability,
      };
      if (groupId) {
        data.group_ids = [groupId];
      }
      const result = await dispatch(Actions.addClassification(data));
      results.push(result);
    });

    // Reset the depths for the posted classifications so that they
    // are not reposted upon further edits
    const newFormState = { ...formState };
    toPost.forEach(([classification, { probability }]) => {
      newFormState[selectedTaxonomy.id][classification] = {
        depth: -1,
        probability,
      };
    });
    setFormState(newFormState);

    setSubmissionRequestInProcess(false);
    if (results.every((result) => result.status === "success")) {
      dispatch(showNotification("Classifications saved."));
    }
  };

  return (
    <div className={classes.container}>
      <Typography variant="h6">Post Classifications</Typography>
      <div>
        <Typography variant="subtitle2">
          Classifications to be posted:
        </Typography>
        {getClassificationsToPost(formState[selectedTaxonomy?.id])?.map(
          ([classification, { probability }]) => (
            <Chip
              key={`${selectedTaxonomy.id}-${classification}`}
              label={`${classification} (${selectedTaxonomy.name}): ${probability}`}
            />
          )
        )}
      </div>
      <FormControl className={classes.taxonomySelect}>
        <InputLabel id={`taxonomy-select-label-${objId}`}>
          Select Taxonomy
        </InputLabel>
        <Select
          labelId={`taxonomy-select-label-${objId}`}
          inputProps={{ MenuProps: { disableScrollLock: true } }}
          id={`taxonomy-select-${objId}`}
          value={selectedTaxonomy || ""}
          onChange={handleSelectTaxonomy}
        >
          {latestTaxonomyList?.map((taxonomy) => (
            <MenuItem key={taxonomy.name} value={taxonomy}>
              {taxonomy.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {selectedTaxonomy?.hierarchy?.subclasses?.map((category) => (
        <Accordion
          className={classes.classifications}
          key={`${category.class}`}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="classifications-content"
            id="classifications-header"
          >
            <Typography
              variant="subtitle1"
              className={classes.accordionHeading}
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
          variant="contained"
          color="primary"
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

MultipleClassificationsForm.propTypes = {
  objId: PropTypes.string.isRequired,
  taxonomyList: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string,
      created_at: PropTypes.string,
      isLatest: PropTypes.bool,
      version: PropTypes.string,
    })
  ).isRequired,
  groupId: PropTypes.number,
  currentClassifications: PropTypes.arrayOf(PropTypes.shape({})).isRequired,
};

MultipleClassificationsForm.defaultProps = {
  groupId: null,
};

export default MultipleClassificationsForm;
