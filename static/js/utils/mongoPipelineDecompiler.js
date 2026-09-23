/**
 * Turns a simple Mongo pipeline back into a builder block tree.
 *
 * Compilation is one-way and lossy: a tree carries block names, variable
 * references and grouping that the pipeline does not, and 3977 lines of
 * `mongoPipelineBuilder` reduce many trees to the same pipeline. So this does
 * not invert that compiler. It recognises the one shape an assistant writes --
 * a single `$match` of field comparisons joined by `$and`/`$or` -- and proves
 * the result by recompiling it: a tree is returned only when it compiles back
 * to the pipeline it came from, byte for byte. Anything else returns null and
 * the caller keeps the pipeline read-only, which is what it does today.
 */
import { convertToMongoAggregation } from "./mongoPipelineBuilder.js";

// The operators makeFieldCondition emits as {field: {$op: value}}.
const OPERATORS = new Set([
  "$eq",
  "$ne",
  "$gt",
  "$gte",
  "$lt",
  "$lte",
  "$in",
  "$exists",
]);

const isPlainObject = (value) =>
  value !== null && typeof value === "object" && !Array.isArray(value);

class Unsupported extends Error {}

const makeId = (state) => `assistant-${state.next++}`;

const condition = (state, field, operator, value) => ({
  id: makeId(state),
  category: "condition",
  field,
  operator,
  value,
});

const block = (state, logic, children) => ({
  id: makeId(state),
  category: "block",
  logic,
  children,
});

/** One `{field: ...}` entry of a match object. */
const fromField = (state, field, spec) => {
  // A boolean $eq compiles to the bare {field: value} shorthand.
  if (!isPlainObject(spec)) {
    return condition(state, field, "$eq", spec);
  }
  const operators = Object.keys(spec);
  if (operators.length !== 1 || !OPERATORS.has(operators[0])) {
    throw new Unsupported(field);
  }
  return condition(state, field, operators[0], spec[operators[0]]);
};

const fromMatch = (state, match) => {
  if (!isPlainObject(match)) throw new Unsupported("match");

  const children = [];
  for (const [key, value] of Object.entries(match)) {
    if (key === "$and" || key === "$or") {
      if (!Array.isArray(value) || value.length === 0) {
        throw new Unsupported(key);
      }
      const logic = key === "$or" ? "Or" : "And";
      const branches = value.map((branch) => fromMatch(state, branch));
      // A branch that is itself a single condition stays a condition; nesting
      // it in a one-child block would compile to an extra $and.
      children.push(
        block(
          state,
          logic,
          branches.map((b) =>
            b.category === "block" &&
            b.children.length === 1 &&
            b.logic === "And"
              ? b.children[0]
              : b,
          ),
        ),
      );
    } else if (key.startsWith("$")) {
      throw new Unsupported(key);
    } else {
      children.push(fromField(state, key, value));
    }
  }
  if (children.length === 0) throw new Unsupported("empty");
  return children.length === 1 && children[0].category === "block"
    ? children[0]
    : block(state, "And", children);
};

/**
 * The match as the compiler would write it, so the two can be compared.
 *
 * Only two rewrites, each meaning-preserving in Mongo: several keys in one
 * object are an implicit conjunction, and a bare value is an equality test.
 * The compiler spells both out, so an input that did not is no difference.
 */
const canonicalMatch = (match) => {
  if (!isPlainObject(match)) return match;

  const keys = Object.keys(match);
  if (keys.length > 1) {
    return { $and: keys.map((key) => canonicalMatch({ [key]: match[key] })) };
  }
  const [key] = keys;
  const value = match[key];

  if (key === "$and" || key === "$or") {
    if (!Array.isArray(value)) return match;
    const branches = value.map(canonicalMatch);
    // A one-branch conjunction is the branch: a block with one child compiles
    // to that child, with no wrapper.
    return branches.length === 1 && key === "$and"
      ? branches[0]
      : { [key]: branches };
  }
  if (key.startsWith("$")) return match;
  return { [key]: isPlainObject(value) ? value : { $eq: value } };
};

/**
 * The block tree for `pipeline`, or null when it cannot be represented or the
 * representation does not compile back to the same thing.
 */
export const decompilePipeline = (pipeline) => {
  if (!Array.isArray(pipeline) || pipeline.length !== 1) return null;
  const [stage] = pipeline;
  if (!isPlainObject(stage) || Object.keys(stage).join() !== "$match") {
    return null;
  }

  let tree;
  try {
    const root = fromMatch({ next: 0 }, stage.$match);
    tree = [
      root.category === "block" ? root : block({ next: 0 }, "And", [root]),
    ];
  } catch (error) {
    if (error instanceof Unsupported) return null;
    throw error;
  }

  try {
    const recompiled = convertToMongoAggregation(tree);
    const canonical = [{ $match: canonicalMatch(stage.$match) }];
    return JSON.stringify(recompiled) === JSON.stringify(canonical)
      ? tree
      : null;
  } catch {
    return null;
  }
};

export default { decompilePipeline };
