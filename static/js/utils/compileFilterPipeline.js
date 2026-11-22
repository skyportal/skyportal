import {
  convertArithmeticExpression,
  convertToMongoAggregation,
} from "./mongoPipelineBuilder.js";
import { isRawMongoPipeline } from "../components/filter/boom/pipelineFormat";

export const compileFilterPipeline = ({
  filters,
  projectionFields,
  schema,
  fieldOptions,
  customVariables,
  customListVariables,
  customSwitchCases,
}) => {
  // Imported filters are already a raw Mongo pipeline (not a block tree);
  // the block-tree converter below can't read them, so pass them through.
  if (isRawMongoPipeline(filters)) {
    return filters;
  }

  // Determine if we're in annotation mode (projections exist)
  const hasAnnotations = projectionFields && projectionFields.length > 0;

  // Collect field names from annotation fields that need to be available
  const annotationFieldsSet = new Set();

  if (projectionFields) {
    projectionFields.forEach((f) => {
      if (!f.fieldName || f.fieldName === "objectId") return;

      // Check if this is an arithmetic variable
      const arithVar = customVariables.find((v) => v.name === f.fieldName);

      if (arithVar) {
        // Arithmetic variable - it must be included itself so its schema-field
        // dependencies get marked "used" and survive the $project stage(s)
        // (see mongoPipelineBuilder.js's additionalFieldsToProject handling).
        annotationFieldsSet.add(f.fieldName);

        // Also scan its expression for variable references that need to be
        // materialized
        if (arithVar.variable) {
          const expression = arithVar.variable.includes("=")
            ? arithVar.variable.split("=")[1].trim()
            : arithVar.variable;

          // Scan for MongoDB-style variable references like $varname
          const fieldRefPattern = /\$([a-zA-Z_][a-zA-Z0-9_]*)/g;
          const matches = [...expression.matchAll(fieldRefPattern)];

          matches.forEach((match) => {
            const varName = match[1];

            // If it's a variable (not a schema field or MongoDB operator), add it
            const isVariable =
              customVariables.some((v) => v.name === varName) ||
              customListVariables.some((v) => v.name === varName) ||
              customSwitchCases.some((v) => v.name === varName);

            if (isVariable) {
              annotationFieldsSet.add(varName);
            }
          });
        }
      } else {
        // Not an arithmetic variable - include it directly
        annotationFieldsSet.add(f.fieldName);
      }
    });
  }

  const annotationFields = Array.from(annotationFieldsSet);

  // Always use filters as the base query, regardless of mode
  // This ensures annotations show both filters + projections
  const baseQuery = convertToMongoAggregation(
    filters,
    schema,
    fieldOptions,
    customVariables,
    customListVariables,
    customSwitchCases,
    annotationFields, // Pass annotation fields so switch cases can be projected
    hasAnnotations, // Pass annotation mode flag
  );

  // If there are projection fields (annotations), adapt the final project stage
  if (hasAnnotations) {
    // Get the last stage (which is sempre a $project stage now)
    let lastStageIndex = baseQuery.length - 1;
    let lastStage = baseQuery[lastStageIndex];

    if (lastStage && lastStage.$project) {
      // Start with existing projection (includes _id and used fields)
      const enhancedProjection = { ...lastStage.$project };

      // Add objectId explicitly if not already there
      if (!enhancedProjection.objectId) {
        enhancedProjection.objectId = "$objectId";
      }

      // Build annotations object
      const annotations_object = {};

      projectionFields.forEach((field) => {
        if (!field.fieldName || field.fieldName === "objectId") return;
        const outputName = field.outputName || field.fieldName;
        const decimals = Number.isInteger(field.roundDecimals)
          ? field.roundDecimals
          : 4;

        // Check if this field is an arithmetic variable
        const arithVar = customVariables.find(
          (v) => v.name === field.fieldName,
        );

        // Handle different projection types
        switch (field.type) {
          case "include":
            if (arithVar) {
              // Inline the arithmetic expression instead of referencing it
              const expr = convertArithmeticExpression(
                arithVar.variable,
                customVariables,
              );
              if (expr) {
                annotations_object[outputName] = expr;
              } else {
                // Fallback to reference if conversion fails
                annotations_object[outputName] = `$${field.fieldName}`;
              }
            } else {
              annotations_object[outputName] = `$${field.fieldName}`;
            }
            break;
          case "exclude":
            annotations_object[outputName] = 0;
            break;
          case "round":
            if (arithVar) {
              // Inline the arithmetic expression and wrap in $round
              const expr = convertArithmeticExpression(
                arithVar.variable,
                customVariables,
              );
              if (expr) {
                annotations_object[outputName] = {
                  $round: [expr, decimals],
                };
              } else {
                // Fallback to reference if conversion fails
                annotations_object[outputName] = {
                  $round: [`$${field.fieldName}`, decimals],
                };
              }
            } else {
              annotations_object[outputName] = {
                $round: [`$${field.fieldName}`, decimals],
              };
            }
            break;
          default:
            if (arithVar) {
              // Inline the arithmetic expression instead of referencing it
              const expr = convertArithmeticExpression(
                arithVar.variable,
                customVariables,
              );
              if (expr) {
                annotations_object[outputName] = expr;
              } else {
                // Fallback to reference if conversion fails
                annotations_object[outputName] = `$${field.fieldName}`;
              }
            } else {
              annotations_object[outputName] = `$${field.fieldName}`;
            }
        }
      });

      // Add annotations_object to projection if there are any
      if (Object.keys(annotations_object).length > 0) {
        enhancedProjection.annotations = annotations_object;

        // IMPORTANT: Scan the annotation expressions for $variableName references
        // These need to be materialized before the $project stage
        const extractVariableRefsFromExpr = (expr, refs) => {
          if (typeof expr === "string" && expr.startsWith("$")) {
            // Field reference like "$jd_min_prv"
            const fieldName = expr.substring(1); // Remove $
            // Check if this is a custom variable, list variable, or switch case
            const isCustomVar = customVariables.some(
              (v) => v.name === fieldName,
            );
            const isListVar = customListVariables.some(
              (v) => v.name === fieldName,
            );
            const isSwitchCase = customSwitchCases.some(
              (v) => v.name === fieldName,
            );

            if (isCustomVar || isListVar || isSwitchCase) {
              refs.add(fieldName);
            }
          } else if (Array.isArray(expr)) {
            expr.forEach((item) => extractVariableRefsFromExpr(item, refs));
          } else if (typeof expr === "object" && expr !== null) {
            Object.values(expr).forEach((value) =>
              extractVariableRefsFromExpr(value, refs),
            );
          }
        };

        const additionalVarRefs = new Set();
        Object.values(annotations_object).forEach((annotationExpr) => {
          extractVariableRefsFromExpr(annotationExpr, additionalVarRefs);
        });

        // Add these variable references to annotationFields so they get materialized
        additionalVarRefs.forEach((varName) => {
          if (!annotationFields.includes(varName)) {
            annotationFields.push(varName);
          }
        });

        // If we found new variables, rebuild the pipeline with them included
        if (additionalVarRefs.size > 0) {
          const rebuiltQuery = convertToMongoAggregation(
            filters,
            schema,
            fieldOptions,
            customVariables,
            customListVariables,
            customSwitchCases,
            annotationFields,
            hasAnnotations,
          );

          // Replace baseQuery entirely with rebuilt query, except keep our enhanced projection
          baseQuery.length = 0;
          baseQuery.push(...rebuiltQuery.slice(0, -1)); // All stages except final project
          // Update lastStageIndex after rebuild
          lastStageIndex = baseQuery.length;
        }
      }

      // Replace/add the last stage with the enhanced projection
      baseQuery[lastStageIndex] = { $project: enhancedProjection };
    }
  }

  return baseQuery;
};
