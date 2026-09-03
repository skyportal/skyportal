export const getSimpleType = (avroType) => {
  if (typeof avroType === "string") {
    switch (avroType) {
      case "double":
      case "float":
      case "int":
      case "long":
        return "number";
      case "string":
        return "string";
      case "boolean":
        return "boolean";
      default:
        return "string";
    }
  }
  if (Array.isArray(avroType)) {
    return getSimpleType(avroType.find((t) => t !== "null"));
  }
  if (typeof avroType === "object") {
    if (avroType.type === "array") return "array";
    if (avroType.type === "record") return "object";
    return getSimpleType(avroType.type);
  }
  return "string";
};

export const flattenFieldOptions = (avroSchema) => {
  const flattenedOptions = [];
  const defaultGroupName = "Other Fields";

  const capitalizeGroupName = (groupName) => {
    if (!groupName || typeof groupName !== "string") return groupName;
    return groupName.charAt(0).toUpperCase() + groupName.slice(1);
  };

  // Resolves a named Avro type reference to its full schema object by searching recursively through the schema's fields
  const resolveNamedType = (typeName, schema) => {
    if (typeof typeName !== "string") return null;

    const find = (fields) => {
      for (const field of fields) {
        const fieldType = Array.isArray(field.type)
          ? field.type.find((t) => t !== "null")
          : field.type;

        if (typeof fieldType === "object") {
          if (fieldType.name === typeName) return fieldType;

          if (
            fieldType.type === "array" &&
            typeof fieldType.items === "object" &&
            fieldType.items.name === typeName
          ) {
            return fieldType.items;
          }

          if (fieldType.type === "record" && fieldType.fields) {
            const found = find(fieldType.fields);
            if (found) return found;
          }
        }

        if (Array.isArray(field.type)) {
          for (const unionType of field.type) {
            if (typeof unionType === "object") {
              if (unionType.name === typeName) return unionType;
              if (unionType.type === "record" && unionType.fields) {
                const found = find(unionType.fields);
                if (found) return found;
              }
            }
          }
        }
      }
      return null;
    };

    return find(schema.fields || []);
  };

  const processField = (field, parentPath = "") => {
    const currentPath = parentPath ? `${parentPath}.${field.name}` : field.name;
    const group = parentPath
      ? capitalizeGroupName(parentPath.split(".")[0])
      : defaultGroupName;

    let actualType = field.type;
    if (Array.isArray(actualType)) {
      actualType = actualType.find((t) => t !== "null") || actualType[0];
    }
    if (typeof actualType === "string") {
      actualType = resolveNamedType(actualType, avroSchema) ?? actualType;
    }

    if (
      typeof actualType === "object" &&
      actualType.type === "record" &&
      actualType.fields
    ) {
      actualType.fields.forEach((nestedField) =>
        processField(nestedField, currentPath),
      );
    } else if (
      typeof actualType === "object" &&
      actualType.type === "array" &&
      actualType.items
    ) {
      let itemsType = actualType.items;
      if (typeof itemsType === "string") {
        const resolvedType = resolveNamedType(itemsType, avroSchema);
        if (resolvedType) {
          itemsType = resolvedType;
        } else {
          flattenedOptions.push({
            label: currentPath,
            type: "array",
            group,
            isExpandableArray: true,
            unresolvedTypeName: actualType.items,
          });
          return;
        }
      }

      const isCrossMatchStyle =
        typeof itemsType === "object" &&
        itemsType.type === "record" &&
        itemsType.fields &&
        itemsType.fields.some(
          (catalogField) =>
            Array.isArray(catalogField.type) &&
            catalogField.type.some(
              (unionType) =>
                typeof unionType === "object" && unionType.type === "record",
            ),
        );

      if (isCrossMatchStyle) {
        const groupName =
          field.name === "cross_matches"
            ? "Cross Matches"
            : capitalizeGroupName(field.name);
        itemsType.fields.forEach((catalogField) => {
          flattenedOptions.push({
            label: `${currentPath}.${catalogField.name}`,
            type: "array",
            group: groupName,
            parentArray: currentPath,
            arrayObject: catalogField.name,
            catalogName: catalogField.name,
          });
        });
      } else if (typeof itemsType === "object" && itemsType.type === "record") {
        flattenedOptions.push({
          label: currentPath,
          type: "array",
          group,
          arrayItems: itemsType,
          isExpandableArray: true,
        });
      } else {
        flattenedOptions.push({
          label: currentPath,
          type: "array",
          group,
          itemType: getSimpleType(itemsType),
        });
      }
    } else {
      flattenedOptions.push({
        label: currentPath,
        type: getSimpleType(actualType),
        group,
      });
    }
  };

  if (avroSchema && avroSchema.fields) {
    avroSchema.fields.forEach((field) => processField(field));
  }

  return flattenedOptions;
};

const getExpandableArrayFields = (avroSchema, arrayFieldName) => {
  if (!avroSchema || !avroSchema.fields) return [];

  const arrayField = avroSchema.fields.find((f) => f.name === arrayFieldName);
  if (!arrayField) return [];

  let fieldType = arrayField.type;

  // Handle union types
  if (Array.isArray(fieldType)) {
    fieldType = fieldType.find((t) => t !== "null") || fieldType[0];
  }

  if (fieldType.type !== "array" || !fieldType.items) return [];

  let itemsType = fieldType.items;

  // Helper to resolve named types
  const resolveNamedType = (typeName, schema) => {
    if (typeof typeName !== "string") return null;

    const findNamedType = (fields) => {
      for (const field of fields) {
        const fieldTypeName = Array.isArray(field.type)
          ? field.type.find((t) => t !== "null")
          : field.type;

        if (
          typeof fieldTypeName === "object" &&
          fieldTypeName.name === typeName
        ) {
          return fieldTypeName;
        }

        if (
          typeof fieldTypeName === "object" &&
          fieldTypeName.type === "record" &&
          fieldTypeName.fields
        ) {
          const found = findNamedType(fieldTypeName.fields);
          if (found) return found;
        }

        if (
          typeof fieldTypeName === "object" &&
          fieldTypeName.type === "array" &&
          typeof fieldTypeName.items === "object" &&
          fieldTypeName.items.fields
        ) {
          const found = findNamedType(fieldTypeName.items.fields);
          if (found) return found;
        }

        // Search within union types (e.g., ["null", {...}])
        if (Array.isArray(field.type)) {
          for (const unionType of field.type) {
            if (typeof unionType === "object" && unionType.name === typeName) {
              return unionType;
            }
            // Recursively search within union type records
            if (
              typeof unionType === "object" &&
              unionType.type === "record" &&
              unionType.fields
            ) {
              const found = findNamedType(unionType.fields);
              if (found) return found;
            }
          }
        }
      }
      return null;
    };

    return findNamedType(schema.fields || []);
  };

  if (typeof itemsType === "string") {
    const resolvedType = resolveNamedType(itemsType, avroSchema);
    if (resolvedType) {
      itemsType = resolvedType;
    }
  }

  if (
    typeof itemsType !== "object" ||
    itemsType.type !== "record" ||
    !itemsType.fields
  ) {
    return [];
  }

  const nestedFields = [];

  const processNestedField = (field, parentPath = "") => {
    const currentPath = parentPath ? `${parentPath}.${field.name}` : field.name;
    let actualType = field.type;

    if (Array.isArray(actualType)) {
      actualType = actualType.find((t) => t !== "null") || actualType[0];
    }
    if (typeof actualType === "string") {
      actualType = resolveNamedType(actualType, avroSchema) ?? actualType;
    }

    if (
      typeof actualType === "object" &&
      actualType.type === "record" &&
      actualType.fields
    ) {
      actualType.fields.forEach((nestedField) =>
        processNestedField(nestedField, currentPath),
      );
    } else if (typeof actualType === "object" && actualType.type === "array") {
      let arrayItemsType = actualType.items;
      if (typeof arrayItemsType === "string") {
        arrayItemsType =
          resolveNamedType(arrayItemsType, avroSchema) ?? arrayItemsType;
      }
      nestedFields.push({
        label: currentPath,
        type: "array",
        itemType: getSimpleType(arrayItemsType),
      });
    } else {
      nestedFields.push({
        label: currentPath,
        type: getSimpleType(actualType),
      });
    }
  };

  itemsType.fields.forEach((field) => processNestedField(field));

  return nestedFields.sort((a, b) => a.label.localeCompare(b.label));
};

export const mongoOperatorLabels = {
  $eq: "=",
  $ne: "≠",
  $gt: ">",
  $gte: "≥",
  $lt: "<",
  $lte: "≤",
  $in: "In",
  $anyElementTrue: "Any Element True",
  $allElementsTrue: "All Elements True",
  $filter: "Filter",
  $map: "Map",
  $exists: "Exists",
  $isNumber: "Is Number",
  $min: "Minimum",
  $max: "Maximum",
  $avg: "Average",
  $sum: "Sum",
  $size: "Count",
  $stdDevPop: "Stdandard Deviation",
  $median: "Median",
  $round: "Round",
  $lengthGt: "Length >",
  $lengthLt: "Length <",
  $regex: "Regex Match",
  $type: "Type Check",
  $switch: "Switch",
};

export const mongoOperatorTypes = {
  $eq: "comparison",
  $ne: "comparison",
  $gt: "comparison",
  $gte: "comparison",
  $lt: "comparison",
  $lte: "comparison",
  $in: "comparison",
  $anyElementTrue: "array",
  $allElementsTrue: "array",
  $filter: "array",
  $map: "array",
  $exists: "exists",
  $isNumber: "exists",
  $min: "aggregation",
  $max: "aggregation",
  $avg: "aggregation",
  $sum: "aggregation",
  $size: "aggregation",
  $stdDevPop: "aggregation",
  $median: "aggregation",
  $round: "aggregation",
  $lengthGt: "array_single",
  $lengthLt: "array_single",
  $regex: "string",
  $type: "string",
  $switch: "conditional",
};

// Helper functions for handling nested objects in arrays
export function flattenObject(obj, prefix = "", separator = ".") {
  const flattened = {};

  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      const newKey = prefix ? `${prefix}${separator}${key}` : key;
      const value = obj[key];

      if (
        value !== null &&
        typeof value === "object" &&
        !Array.isArray(value)
      ) {
        // Recursively flatten nested objects
        Object.assign(flattened, flattenObject(value, newKey, separator));
      } else {
        flattened[newKey] = value;
      }
    }
  }

  return flattened;
}

export function unflattenObject(flatObj, separator = ".") {
  const result = {};

  for (const key in flatObj) {
    if (Object.prototype.hasOwnProperty.call(flatObj, key)) {
      const keys = key.split(separator);
      let current = result;

      for (let i = 0; i < keys.length - 1; i++) {
        const k = keys[i];
        if (!(k in current)) {
          current[k] = {};
        }
        current = current[k];
      }

      current[keys[keys.length - 1]] = flatObj[key];
    }
  }

  return result;
}

// Helper to get all array and aggregation operators
export function getArrayOperators() {
  return Object.keys(mongoOperatorTypes).filter(
    (op) =>
      mongoOperatorTypes[op] === "array" ||
      mongoOperatorTypes[op] === "array_boolean" ||
      mongoOperatorTypes[op] === "array_single" ||
      mongoOperatorTypes[op] === "array_number" ||
      mongoOperatorTypes[op] === "aggregation",
  );
}

// Helper to get comparison operators
export function getComparisonOperators() {
  return Object.keys(mongoOperatorTypes).filter(
    (op) => mongoOperatorTypes[op] === "comparison",
  );
}

// Helper to extract array field subkeys for list condition dialog
export function getArrayFieldSubOptions(arrayFieldLabel, schema) {
  // Handle null/undefined input
  if (!arrayFieldLabel || typeof arrayFieldLabel !== "string") {
    return [];
  }

  // Handle different array field formats
  if (arrayFieldLabel.startsWith("cross_matches.")) {
    // Extract the catalog name (e.g., 'AllWISE' from 'cross_matches.AllWISE')
    const catalogName = arrayFieldLabel.replace("cross_matches.", "");

    // Find the cross_matches field in the Avro schema
    const crossMatchesField = schema?.fields?.find(
      (field) => field.name === "cross_matches",
    );
    if (!crossMatchesField) {
      return [];
    }

    let crossMatchType = crossMatchesField.type;
    if (Array.isArray(crossMatchType)) {
      crossMatchType =
        crossMatchType.find((t) => t !== "null") || crossMatchType[0];
    }

    if (
      crossMatchType.type === "array" &&
      crossMatchType.items &&
      crossMatchType.items.type === "record" &&
      crossMatchType.items.fields
    ) {
      // Find the specific catalog field
      const catalogField = crossMatchType.items.fields.find(
        (f) => f.name === catalogName,
      );
      if (!catalogField) return [];

      let catalogType = catalogField.type;
      if (Array.isArray(catalogType)) {
        catalogType = catalogType.find((t) => t !== "null") || catalogType[0];
      }

      if (
        typeof catalogType === "object" &&
        catalogType.type === "record" &&
        catalogType.fields
      ) {
        // Convert Avro fields to our field options format
        const catalogGroupName =
          catalogName === "NED_BetaV3"
            ? "NED BetaV3"
            : catalogName === "CLU_20190625"
              ? "CLU 20190625"
              : catalogName === "Gaia_EDR3"
                ? "Gaia EDR3"
                : catalogName;

        const convertAvroField = (field, prefix = "") => {
          const fieldPath = prefix ? `${prefix}.${field.name}` : field.name;
          let fieldType = field.type;
          if (Array.isArray(fieldType)) {
            fieldType = fieldType.find((t) => t !== "null") || fieldType[0];
          }

          if (
            typeof fieldType === "object" &&
            fieldType.type === "record" &&
            fieldType.fields
          ) {
            return fieldType.fields.flatMap((nestedField) =>
              convertAvroField(nestedField, fieldPath),
            );
          }
          return [
            {
              label: `${arrayFieldLabel}.${fieldPath}`,
              type: getSimpleType(fieldType),
              group: catalogGroupName,
            },
          ];
        };

        const allFields = catalogType.fields.flatMap((field) =>
          convertAvroField(field),
        );

        return allFields.sort((a, b) => a.label.localeCompare(b.label));
      }
    }

    return [];
  }

  if (!arrayFieldLabel.includes(".")) {
    return getExpandableArrayFields(schema, arrayFieldLabel);
  }

  return [];
}
