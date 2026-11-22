import { compileFilterPipeline } from "./compileFilterPipeline.js";
import { convertArithmeticExpression } from "./mongoPipelineBuilder.js";
import {
  Unsupported,
  describePipeline,
  isBooleanExpr,
  isNumericExpr,
  normalizeExpr,
  readPipeline,
} from "./pipelineSemantics.js";

const isPlainObject = (value) =>
  value !== null && typeof value === "object" && !Array.isArray(value);

const opOf = (expr) =>
  isPlainObject(expr) && Object.keys(expr).length === 1
    ? Object.keys(expr)[0]
    : null;

const isDef = (expr) => isPlainObject(expr) && expr.$$def !== undefined;

const isFieldRef = (expr) =>
  typeof expr === "string" && expr.startsWith("$") && !expr.startsWith("$$");

const isLiteral = (expr) =>
  expr === null ||
  typeof expr === "number" ||
  typeof expr === "boolean" ||
  (typeof expr === "string" && !expr.startsWith("$")) ||
  (Array.isArray(expr) && expr.every(isLiteral));

const isOperatorObject = (value) =>
  isPlainObject(value) &&
  Object.keys(value).length > 0 &&
  Object.keys(value).every((k) => k.startsWith("$"));

const operatorsOf = (condition) =>
  isOperatorObject(condition)
    ? Object.entries(condition)
    : [["$eq", condition]];

const unwrapSingle = (arg) =>
  Array.isArray(arg) && arg.length === 1 ? arg[0] : arg;

const unwrapEmptyFallback = (expr) =>
  opOf(expr) === "$ifNull" &&
  Array.isArray(expr.$ifNull) &&
  Array.isArray(expr.$ifNull[1]) &&
  expr.$ifNull[1].length === 0
    ? expr.$ifNull[0]
    : expr;

const COMPARISONS = new Set(["$eq", "$ne", "$gt", "$gte", "$lt", "$lte"]);
const BOOLEAN_NODES = new Set([
  ...COMPARISONS,
  "$in",
  "$and",
  "$or",
  "$not",
  "$isNumber",
]);
const FLIPPED = {
  $eq: "$eq",
  $ne: "$ne",
  $gt: "$lt",
  $gte: "$lte",
  $lt: "$gt",
  $lte: "$gte",
};
const QUERY_OPERATORS = new Set([
  "$eq",
  "$ne",
  "$gt",
  "$gte",
  "$lt",
  "$lte",
  "$in",
  "$exists",
]);
const LIST_REDUCERS = new Set(["$min", "$max", "$avg", "$sum", "$stdDevPop"]);

const INFIX = {
  $add: " + ",
  $subtract: " - ",
  $multiply: " * ",
  $divide: " / ",
  $pow: "^",
};
const FUNCTIONS = {
  $abs: "abs",
  $sqrt: "sqrt",
  $ln: "ln",
  $log10: "log10",
  $exp: "exp",
  $floor: "floor",
  $ceil: "ceil",
  $sin: "sin",
  $cos: "cos",
  $tan: "tan",
  $asin: "asin",
  $acos: "acos",
  $atan: "atan",
  $degreesToRadians: "radians",
  $radiansToDegrees: "degrees",
  $toString: "toString",
  $first: "first",
  $last: "last",
};
const VARIADIC = {
  $max: "max",
  $min: "min",
  $atan2: "atan2",
  $round: "round",
  $ifNull: "ifNull",
  $arrayElemAt: "at",
};
const REDUCERS = { $min: "min", $max: "max", $sum: "sum", $avg: "avg" };

const IDENTIFIER = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
const FIELD_PATH = /^[a-zA-Z0-9_][a-zA-Z0-9_.]*$/;

const formatNumber = (n) => {
  if (!Number.isFinite(n)) throw new Unsupported("non-finite number");
  let text = String(n);
  if (/e/i.test(text)) {
    text = n.toLocaleString("en-US", {
      useGrouping: false,
      maximumFractionDigits: 20,
    });
  }
  if (parseFloat(text) !== n) throw new Unsupported(`number ${n}`);
  return text;
};

const sanitize = (name) => {
  const cleaned = String(name || "")
    .replace(/[^a-zA-Z0-9_]/g, "_")
    .replace(/^([0-9])/, "_$1");
  return IDENTIFIER.test(cleaned) ? cleaned : "value";
};

const fieldRoots = (expr, found = new Set()) => {
  if (isFieldRef(expr)) {
    found.add(expr.slice(1).split(".")[0]);
  } else if (Array.isArray(expr)) {
    expr.forEach((e) => fieldRoots(e, found));
  } else if (isPlainObject(expr)) {
    Object.values(expr).forEach((e) => fieldRoots(e, found));
  }
  return found;
};

const PROBES = new Map();

const KINDS = {
  variable: "customVariables",
  listVariable: "customListVariables",
  switchCase: "customSwitchCases",
};
const CREATED = {
  variable: "variables",
  listVariable: "listVariables",
  switchCase: "switchCases",
};

const replaceDropped = (expr) => {
  if (Array.isArray(expr)) return expr.map(replaceDropped);
  if (!isPlainObject(expr)) return expr;
  if (opOf(expr) === "$__missing") return `$${expr.$__missing}`;
  return Object.fromEntries(
    Object.entries(expr).map(([k, v]) => [k, replaceDropped(v)]),
  );
};

class Decompiler {
  constructor(ir, context) {
    this.ir = {
      where: replaceDropped(ir.where),
      defs: ir.defs.map((d) => ({ ...d, expr: replaceDropped(d.expr) })),
      annotations: replaceDropped(ir.annotations),
    };
    this.context = context;
    this.created = { variables: [], listVariables: [], switchCases: [] };
    this.byDef = new Map();
    this.nextId = 0;
    this.catalogNames = new Set(
      Object.values(KINDS).flatMap((k) => context[k].map((v) => v.name)),
    );
    this.taken = new Set([
      ...this.catalogNames,
      ...context.fieldOptions.flatMap((f) => [f.value, f.label]),
    ]);
  }

  id() {
    this.nextId += 1;
    return `pipeline-${this.nextId}`;
  }

  ref(name, kind = "schema") {
    let type;
    if (kind === "schema") {
      type = this.context.fieldOptions.find(
        (f) => f.value === name || f.label === name,
      )?.type;
    } else if (kind === "variable") {
      type = "number";
    } else if (kind === "listVariable") {
      const operator = this.find("listVariable", name)?.listCondition?.operator;
      type =
        operator === "$anyElementTrue" || operator === "$allElementsTrue"
          ? "array_variable_boolean"
          : "array_variable";
    }
    return {
      name,
      _meta: {
        isSchemaField: kind === "schema",
        isVariable: kind === "variable",
        isListVariable: kind === "listVariable",
        isSwitchCase: kind === "switchCase",
        ...(type ? { type } : {}),
      },
    };
  }

  find(kind, name) {
    return [...this.context[KINDS[kind]], ...this.created[CREATED[kind]]].find(
      (v) => v.name === name,
    );
  }

  condition(field, operator, value) {
    return { id: this.id(), category: "condition", field, operator, value };
  }

  block(logic, children, negated = false) {
    const node = { id: this.id(), category: "block", logic, children };
    if (negated) node.isTrue = false;
    return node;
  }

  single(nodes) {
    return nodes.length === 1 ? nodes[0] : this.block("And", nodes);
  }

  uniqueName(hint) {
    const base = sanitize(hint);
    let name = base;
    for (let i = 2; this.taken.has(name); i += 1) name = `${base}_${i}`;
    this.taken.add(name);
    return name;
  }

  variables() {
    return {
      customVariables: [
        ...this.context.customVariables,
        ...this.created.variables,
      ],
      customListVariables: [
        ...this.context.customListVariables,
        ...this.created.listVariables,
      ],
      customSwitchCases: [
        ...this.context.customSwitchCases,
        ...this.created.switchCases,
      ],
    };
  }

  normalized(expr) {
    return normalizeExpr(expr, this.ir.defs);
  }

  probeCache() {
    if (!this.probes) {
      const key = JSON.stringify(
        Object.values(KINDS).map((k) => this.context[k]),
      );
      if (!PROBES.has(key)) {
        if (PROBES.size > 20) PROBES.clear();
        PROBES.set(key, new Map());
      }
      this.probes = PROBES.get(key);
    }
    return this.probes;
  }

  probe(name) {
    try {
      const pipeline = compileFilterPipeline({
        filters: [],
        projectionFields: [
          { fieldName: name, outputName: "probe", type: "include" },
        ],
        schema: this.context.schema,
        fieldOptions: this.context.fieldOptions,
        customVariables: this.context.customVariables,
        customListVariables: this.context.customListVariables,
        customSwitchCases: this.context.customSwitchCases,
      });
      return JSON.stringify(describePipeline(pipeline).annotations.probe);
    } catch {
      return null;
    }
  }

  mayMatch(kind, variable, normalized, roots) {
    if (kind === "listVariable") {
      return opOf(normalized) === variable.listCondition?.operator;
    }
    if (kind === "switchCase") {
      return opOf(normalized) === "$switch" || isBooleanExpr(normalized);
    }
    const expression = String(variable.variable || "")
      .split("=")
      .slice(1)
      .join("=");
    const names = expression.match(/[a-zA-Z_][a-zA-Z0-9_]*/g) || [];
    return (
      roots.size === 0 ||
      names.some((n) => roots.has(n) || this.catalogNames.has(n))
    );
  }

  catalogMatch(kind, expr) {
    const normalized = this.normalized(expr);
    const target = JSON.stringify(normalized);
    const roots = fieldRoots(normalized);
    const probes = this.probeCache();
    const hit = this.context[KINDS[kind]].find((v) => {
      if (!this.mayMatch(kind, v, normalized, roots)) return false;
      const key = `${kind}:${JSON.stringify(v)}`;
      if (!probes.has(key)) probes.set(key, this.probe(v.name));
      return probes.get(key) === target;
    });
    return hit ? { name: hit.name, kind } : null;
  }

  addArithmetic(hint, expr) {
    const reused = this.catalogMatch("variable", expr);
    if (reused) return reused;
    const variable = `${this.printArithmetic(expr, null, true)}`;
    const name = this.uniqueName(hint);
    this.created.variables.push({
      name,
      variable: `${name} = ${variable}`,
      type: "number",
      streams: this.context.streams,
    });
    return { name, kind: "variable" };
  }

  addList(hint, expr, listCondition) {
    const reused = this.catalogMatch("listVariable", expr);
    if (reused) return reused;
    const name = this.uniqueName(hint);
    this.created.listVariables.push({
      name,
      listCondition: { type: "array", ...listCondition },
      streams: this.context.streams,
    });
    return { name, kind: "listVariable" };
  }

  addSwitch(hint, expr, cases, fallback) {
    const reused = this.catalogMatch("switchCase", expr);
    if (reused) return reused;
    const name = this.uniqueName(hint);
    const value = { cases };
    if (fallback !== undefined) value.default = fallback;
    this.created.switchCases.push({
      name,
      switchCondition: { operator: "$switch", value, targetField: name },
      type: "switch_variable",
      streams: this.context.streams,
    });
    return { name, kind: "switchCase" };
  }

  liftValue(expr, hint) {
    if (!isDef(expr)) return this.liftDefinition(expr, hint);
    if (!this.byDef.has(expr.$$def)) {
      const def = this.ir.defs[expr.$$def];
      this.byDef.set(expr.$$def, this.liftDefinition(def.expr, def.name));
    }
    return this.byDef.get(expr.$$def);
  }

  liftDefinition(expr, hint) {
    if (isDef(expr)) return this.liftValue(expr, hint);
    const op = opOf(expr);
    if (op === "$expr") return this.liftDefinition(expr.$expr, hint);
    const list = this.liftList(expr, hint);
    if (list) return list;
    if (op === "$switch" || op === "$cond") return this.liftSwitch(expr, hint);
    if (isBooleanExpr(expr)) {
      if (!BOOLEAN_NODES.has(op)) {
        throw new Unsupported(`it uses ${op}, which blocks cannot express`);
      }
      return this.addSwitch(
        hint,
        expr,
        [{ block: this.liftBooleanBlock(expr, null, hint), then: true }],
        false,
      );
    }
    if (
      isNumericExpr(expr) ||
      isFieldRef(expr) ||
      VARIADIC[op] ||
      FUNCTIONS[op]
    ) {
      return this.addArithmetic(hint, expr);
    }
    throw new Unsupported(
      `it uses ${op || typeof expr}, which blocks cannot express`,
    );
  }

  arrayInput(input, hint) {
    const source = unwrapEmptyFallback(input);
    if (isFieldRef(source)) return source.slice(1);
    if (isPlainObject(source) && source.$$partial) {
      return source.$$partial.path;
    }
    const inner = this.liftValue(source, `${hint}_items`);
    if (inner.kind !== "listVariable") {
      throw new Unsupported("list over a computed value");
    }
    return inner.name;
  }

  liftList(expr, hint) {
    const op = opOf(expr);
    if (op === "$anyElementTrue" || op === "$allElementsTrue") {
      const arg = unwrapEmptyFallback(unwrapSingle(expr[op]));
      if (opOf(arg) === "$map") {
        const { input, as, in: body } = arg.$map;
        const field = this.arrayInput(input, hint);
        const value = this.liftBooleanBlock(body, { field, as }, hint);
        return this.addList(hint, expr, { field, operator: op, value });
      }
      return this.addList(hint, expr, {
        field: this.arrayInput(arg, hint),
        operator: op,
      });
    }
    if (op === "$filter") {
      const { input, as, cond, limit } = expr.$filter;
      if (limit !== undefined) throw new Unsupported("$filter with a limit");
      const field = this.arrayInput(input, hint);
      const value = this.liftBooleanBlock(cond, { field, as }, hint);
      return this.addList(hint, expr, { field, operator: "$filter", value });
    }
    if (op === "$size") {
      const field = this.arrayInput(unwrapSingle(expr.$size), hint);
      return this.addList(hint, expr, { field, operator: "$size" });
    }
    if (op === "$map") {
      const { input, as, in: body } = expr.$map;
      const field = this.arrayInput(input, hint);
      return this.addList(hint, expr, {
        field,
        operator: "$map",
        value: { mapExpression: this.renameElement(body, as) },
      });
    }
    if (op === "$median") {
      const { input, method } = expr.$median;
      if (method !== "approximate" || !isFieldRef(input)) return null;
      return this.addList(hint, expr, this.reducerSource(input, "$median"));
    }
    if (LIST_REDUCERS.has(op) && isFieldRef(expr[op])) {
      return this.addList(hint, expr, this.reducerSource(expr[op], op));
    }
    return null;
  }

  reducerSource(ref, operator) {
    const path = ref.slice(1);
    const cut = path.lastIndexOf(".");
    return cut < 0
      ? { field: path, operator }
      : { field: path.slice(0, cut), subField: path.slice(cut + 1), operator };
  }

  renameElement(expr, as) {
    if (typeof expr === "string" && expr.startsWith(`$$${as}`)) {
      const rest = expr.slice(as.length + 2);
      if (rest === "" || rest.startsWith(".")) return `$$this${rest}`;
    }
    if (Array.isArray(expr)) return expr.map((e) => this.renameElement(e, as));
    if (!isPlainObject(expr)) return expr;
    if (isDef(expr) || expr.$$partial) {
      throw new Unsupported("computed value inside a list mapping");
    }
    if (opOf(expr) === "$map" || opOf(expr) === "$filter") {
      throw new Unsupported("nested list operation");
    }
    return Object.fromEntries(
      Object.entries(expr).map(([k, v]) => [k, this.renameElement(v, as)]),
    );
  }

  liftSwitch(expr, hint) {
    let branches;
    let fallback;
    if (opOf(expr) === "$cond") {
      const arg = expr.$cond;
      const [ifExpr, thenExpr, elseExpr] = Array.isArray(arg)
        ? arg
        : [arg.if, arg.then, arg.else];
      branches = [{ case: ifExpr, then: thenExpr }];
      fallback = elseExpr;
    } else {
      ({ branches, default: fallback } = expr.$switch);
    }
    const cases = branches.map((b, i) => ({
      block: this.liftBooleanBlock(b.case, null, `${hint}_case${i + 1}`),
      then: this.switchValue(b.then, `${hint}_value${i + 1}`),
    }));
    return this.addSwitch(
      hint,
      expr,
      cases,
      fallback === undefined
        ? undefined
        : this.switchValue(fallback, `${hint}_default`),
    );
  }

  switchValue(expr, hint) {
    if (typeof expr === "number" || typeof expr === "boolean") return expr;
    if (typeof expr === "string" && !expr.startsWith("$")) {
      if (!Number.isNaN(Number(expr)) || this.taken.has(expr)) {
        throw new Unsupported(`switch value ${expr}`);
      }
      return expr;
    }
    if (isFieldRef(expr)) return this.ref(expr.slice(1));
    const variable = this.liftValue(expr, hint);
    return this.ref(variable.name, variable.kind);
  }

  printArithmetic(expr, array, top = false) {
    const wrap = (text) => (top ? text : `(${text})`);
    if (typeof expr === "number") return formatNumber(expr);
    if (typeof expr === "string") {
      if (array && expr.startsWith(`$$${array.as}.`)) {
        return `${array.field}.${expr.slice(array.as.length + 3)}`;
      }
      if (isFieldRef(expr) && FIELD_PATH.test(expr.slice(1))) {
        return expr.slice(1);
      }
      throw new Unsupported(`reference ${expr} in arithmetic`);
    }
    if (isDef(expr)) {
      const variable = this.liftValue(expr);
      if (variable.kind !== "variable" || !array) return variable.name;
      return this.printArithmetic(this.ir.defs[expr.$$def].expr, array);
    }
    const materialized = this.materializedPath(expr, "value");
    if (materialized) return materialized;
    const op = opOf(expr);
    const arg = op ? expr[op] : undefined;
    if (INFIX[op] && Array.isArray(arg) && arg.length >= 2) {
      if (op !== "$add" && op !== "$multiply" && arg.length !== 2) {
        throw new Unsupported(`${op} with ${arg.length} operands`);
      }
      return wrap(
        arg.map((a) => this.printArithmetic(a, array)).join(INFIX[op]),
      );
    }
    const call = (name, args) =>
      `${name}(${args.map((a) => this.printArithmetic(a, array, true)).join(", ")})`;
    if (FUNCTIONS[op]) return call(FUNCTIONS[op], [unwrapSingle(arg)]);
    if (VARIADIC[op] && Array.isArray(arg) && arg.length >= 2) {
      return call(VARIADIC[op], arg);
    }
    if (REDUCERS[op] && !Array.isArray(arg)) return call(REDUCERS[op], [arg]);
    if (!array && op) {
      const list = this.liftList(expr, "value");
      if (list) return list.name;
      if (op === "$switch" || op === "$cond") {
        return this.liftSwitch(expr, "value").name;
      }
    }
    throw new Unsupported(
      `it computes with ${op || "a value"}, which blocks cannot express`,
    );
  }

  namedForm(expr) {
    if (Array.isArray(expr)) return expr.map((e) => this.namedForm(e));
    if (!isPlainObject(expr)) return expr;
    if (isDef(expr)) {
      const variable = this.liftValue(expr);
      return variable.kind === "variable"
        ? this.namedForm(this.ir.defs[expr.$$def].expr)
        : `$${variable.name}`;
    }
    return Object.fromEntries(
      Object.entries(expr).map(([k, v]) => [k, this.namedForm(v)]),
    );
  }

  definitionOf(expr) {
    return isDef(expr)
      ? this.definitionOf(this.ir.defs[expr.$$def].expr)
      : expr;
  }

  materializedPath(expr, hint) {
    if (opOf(expr) !== "$__get") return null;
    const [base, path] = expr.$__get;
    const variable = this.liftValue(base, hint);
    if (variable.kind === "variable") {
      throw new Unsupported("path into a computed number");
    }
    return `${variable.name}.${path}`;
  }

  addArithmeticInArray(expr, array, hint) {
    if (!isNumericExpr(expr) && !isDef(expr)) {
      throw new Unsupported("non-numeric value inside a list condition");
    }
    const target = JSON.stringify(normalizeExpr(this.namedForm(expr), []));
    const reused = this.context.customVariables.find((v) => {
      const converted = convertArithmeticExpression(
        v.variable,
        this.context.customVariables,
      );
      if (!converted) return false;
      const inArray = JSON.parse(
        JSON.stringify(converted)
          .split(`"$${array.field}.`)
          .join(`"$$${array.as}.`),
      );
      return JSON.stringify(normalizeExpr(inArray, [])) === target;
    });
    if (reused) return this.ref(reused.name, "variable");
    const name = this.uniqueName(hint);
    this.created.variables.push({
      name,
      variable: `${name} = ${this.printArithmetic(expr, array, true)}`,
      type: "number",
      streams: this.context.streams,
    });
    return this.ref(name, "variable");
  }

  operand(expr, array, hint) {
    const result = this.operandRef(expr, array, hint);
    if (array && result.ref?._meta?.isSchemaField) {
      return { ref: result.ref.name, schema: true };
    }
    return result;
  }

  operandRef(expr, array, hint) {
    if (isLiteral(expr)) return { literal: expr };
    const materialized = this.materializedPath(expr, hint);
    if (materialized) return { ref: this.ref(materialized) };
    if (
      typeof expr === "string" &&
      array &&
      expr.startsWith(`$$${array.as}.`)
    ) {
      return {
        ref: this.ref(`${array.field}.${expr.slice(array.as.length + 3)}`),
      };
    }
    if (isFieldRef(expr)) return { ref: this.ref(expr.slice(1)) };
    if (array) {
      const lifted = isDef(expr) ? this.liftValue(expr, hint) : null;
      if (lifted && lifted.kind !== "variable") {
        return { ref: this.ref(lifted.name, lifted.kind) };
      }
      return { ref: this.addArithmeticInArray(expr, array, hint) };
    }
    const variable = this.liftValue(expr, hint);
    return { ref: this.ref(variable.name, variable.kind) };
  }

  liftBooleanBlock(expr, array, hint) {
    const op = opOf(expr);
    if (op === "$and" || op === "$or") {
      return this.block(
        op === "$and" ? "And" : "Or",
        expr[op].map((e, i) =>
          this.liftBooleanNode(e, array, `${hint}_${i + 1}`),
        ),
      );
    }
    return this.block("And", [this.liftBooleanNode(expr, array, hint)]);
  }

  liftBooleanNode(expr, array, hint) {
    const op = opOf(expr);
    if (op === "$and" || op === "$or") {
      return this.liftBooleanBlock(expr, array, hint);
    }
    if (op === "$not") {
      const block = this.liftBooleanBlock(unwrapSingle(expr.$not), array, hint);
      if (block.isTrue !== false) return { ...block, isTrue: false };
      const { isTrue, ...positive } = block;
      return positive;
    }
    if (COMPARISONS.has(op) || op === "$in") {
      let [left, right] = expr[op];
      let operator = op;
      if (op !== "$in" && isLiteral(left) && !isLiteral(right)) {
        [left, right] = [right, left];
        operator = FLIPPED[op];
      }
      if (operator === "$ne" && opOf(left) === "$type" && right === "missing") {
        const target = this.operand(left.$type, array, hint);
        if (target.schema || target.ref?._meta?.isSchemaField) {
          return this.condition(target.ref, "$exists", true);
        }
      }
      if (
        opOf(left) === "$size" &&
        (operator === "$gt" || operator === "$lt") &&
        typeof right === "number"
      ) {
        const target = this.operand(unwrapSingle(left.$size), array, hint);
        if (target.schema || target.ref?._meta?.isSchemaField) {
          return this.condition(
            target.ref,
            operator === "$gt" ? "$lengthGt" : "$lengthLt",
            right,
          );
        }
      }
      const subject = this.operand(left, array, `${hint}_value`);
      if (!subject.ref) throw new Unsupported("comparison of two literals");
      if (isLiteral(right)) return this.condition(subject.ref, operator, right);
      if (op === "$in") throw new Unsupported("$in against a computed list");
      const bound = this.operand(right, array, `${hint}_bound`);
      return this.condition(subject.ref, operator, bound.ref);
    }
    if (op === "$isNumber") {
      const subject = this.operand(unwrapSingle(expr.$isNumber), array, hint);
      return this.condition(subject.ref, "$isNumber", "true");
    }
    const variable = this.liftValue(expr, hint);
    if (variable.kind === "variable") {
      throw new Unsupported("numeric value used as a condition");
    }
    return this.condition(this.ref(variable.name, variable.kind), "$eq", true);
  }

  liftQuery(query) {
    return Object.entries(query).flatMap(([key, value]) => {
      if (key === "$and") return value.flatMap((q) => this.liftQuery(q));
      if (key === "$or" || key === "$nor") {
        const branches = value.map((q) => this.single(this.liftQuery(q)));
        return [this.block("Or", branches, key === "$nor")];
      }
      if (key === "$expr") return this.liftTopExpression(value);
      if (key === "$$on") return this.liftComputedQuery(value[0], value[1]);
      return this.liftFieldQuery(this.ref(key), value);
    });
  }

  liftFieldQuery(field, condition) {
    return operatorsOf(condition).flatMap(([op, value]) => {
      if (op === "$not") {
        return [this.block("And", this.liftFieldQuery(field, value), true)];
      }
      if (op === "$nin") {
        return [this.block("And", [this.condition(field, "$in", value)], true)];
      }
      if (!QUERY_OPERATORS.has(op)) {
        throw new Unsupported(`query operator ${op}`);
      }
      if (op === "$in" && value.length === 1 && typeof value[0] === "boolean") {
        return [this.condition(field, "$eq", value[0])];
      }
      return [this.condition(field, op, value)];
    });
  }

  liftLengthQuery(target, condition) {
    const [base, path] = target.$__get;
    const variable = this.liftValue(base, "value");
    const index = Number(path);
    const ops = isOperatorObject(condition) ? Object.entries(condition) : [];
    if (
      variable.kind !== "listVariable" ||
      !Number.isInteger(index) ||
      ops.length !== 1 ||
      ops[0][0] !== "$exists"
    ) {
      throw new Unsupported("condition on part of a list variable");
    }
    const field = this.ref(variable.name, "listVariable");
    return ops[0][1]
      ? [this.condition(field, "$lengthGt", index)]
      : [this.condition(field, "$lengthLt", index + 1)];
  }

  liftComputedQuery(target, condition) {
    if (opOf(target) === "$__get") {
      return this.liftLengthQuery(target, condition);
    }
    const variable = this.liftValue(target, "value");
    const field = this.ref(variable.name, variable.kind);
    return operatorsOf(condition).flatMap(([op, value]) => {
      if (op === "$not") {
        return [this.block("And", this.liftComputedQuery(target, value), true)];
      }
      if (!QUERY_OPERATORS.has(op)) {
        throw new Unsupported(`query operator ${op}`);
      }
      if (variable.kind !== "variable") {
        return [this.condition(field, op, value)];
      }
      if (typeof value !== "number" || op === "$in" || op === "$exists") {
        throw new Unsupported("query on a computed number");
      }
      if (op === "$lt" || op === "$lte") {
        return [
          this.condition(field, op, value),
          this.condition(field, "$isNumber", "true"),
        ];
      }
      return [this.condition(field, op, value)];
    });
  }

  liftTopExpression(expr) {
    const op = opOf(expr);
    if (op === "$and") {
      return expr.$and.flatMap((e) => this.liftTopExpression(e));
    }
    if (op === "$or") {
      const branches = expr.$or.map((e) =>
        this.single(this.liftTopExpression(e)),
      );
      return [this.block("Or", branches)];
    }
    if (op === "$not") {
      const inner = this.liftTopExpression(unwrapSingle(expr.$not));
      return [this.block("And", inner, true)];
    }
    if (op === "$isNumber" && isFieldRef(unwrapSingle(expr.$isNumber))) {
      const field = this.ref(unwrapSingle(expr.$isNumber).slice(1));
      return [this.condition(field, "$isNumber", "true")];
    }
    if (COMPARISONS.has(op) || op === "$in") {
      let [left, right] = expr[op];
      let operator = op;
      if (op !== "$in" && isLiteral(left) && !isLiteral(right)) {
        [left, right] = [right, left];
        operator = FLIPPED[op];
      }
      const size = opOf(left) === "$size" ? unwrapSingle(left.$size) : null;
      if (
        isFieldRef(size) &&
        (operator === "$gt" || operator === "$lt") &&
        typeof right === "number"
      ) {
        const length = operator === "$gt" ? "$lengthGt" : "$lengthLt";
        return [this.condition(this.ref(size.slice(1)), length, right)];
      }
      if (isLiteral(right)) {
        const hint = isFieldRef(left) ? left.slice(1) : "value";
        const variable = this.addArithmetic(hint, left);
        return [
          this.condition(this.ref(variable.name, "variable"), operator, right),
        ];
      }
      if (isFieldRef(left) && !isFieldRef(right) && op !== "$in") {
        const bound = this.liftValue(right, `${left.slice(1)}_bound`);
        if (bound.kind === "variable") {
          return [
            this.condition(
              this.ref(left.slice(1)),
              operator,
              this.ref(bound.name, "variable"),
            ),
          ];
        }
      }
    }
    const variable = this.liftValue(expr, "condition");
    if (variable.kind === "variable") {
      throw new Unsupported("numeric value used as a condition");
    }
    return [
      this.condition(this.ref(variable.name, variable.kind), "$eq", true),
    ];
  }

  liftAnnotation(path, expr) {
    if (path.includes(".")) throw new Unsupported("nested annotation");
    let type = "include";
    let source = expr;
    let roundDecimals = 4;
    const definition = this.definitionOf(expr);
    if (opOf(definition) === "$round") {
      const [value, places = 0] = Array.isArray(definition.$round)
        ? definition.$round
        : [definition.$round];
      if (!Number.isInteger(places)) throw new Unsupported("rounding places");
      type = "round";
      source = value;
      roundDecimals = places;
    }
    const fieldName = isFieldRef(source)
      ? source.slice(1)
      : this.liftValue(source, path).name;
    return {
      id: `annotation-${path}`,
      type,
      fieldName,
      outputName: path,
      isDefault: false,
      roundDecimals,
    };
  }

  run() {
    const children = this.ir.where.flatMap((query) => this.liftQuery(query));
    return {
      filters: [this.block("And", children)],
      projectionFields: Object.entries(this.ir.annotations).map(
        ([path, expr]) => this.liftAnnotation(path, expr),
      ),
    };
  }
}

const withDefaults = (context) => ({
  schema: context.schema ?? {},
  fieldOptions: context.fieldOptions ?? [],
  customVariables: context.customVariables ?? [],
  customListVariables: context.customListVariables ?? [],
  customSwitchCases: context.customSwitchCases ?? [],
  streams: context.streams ?? [],
});

export const liftPipeline = (pipeline, context = {}) => {
  const ctx = withDefaults(context);
  const decompiler = new Decompiler(readPipeline(pipeline), ctx);
  const { filters, projectionFields } = decompiler.run();
  return {
    filters,
    projectionFields,
    newVariables: decompiler.created,
    pipeline: compileFilterPipeline({
      filters,
      projectionFields,
      schema: ctx.schema,
      fieldOptions: ctx.fieldOptions,
      ...decompiler.variables(),
    }),
  };
};

export const decompileFilterPipeline = (pipeline, context = {}) => {
  try {
    const lifted = liftPipeline(pipeline, context);
    const expected = JSON.stringify(describePipeline(pipeline));
    const actual = JSON.stringify(describePipeline(lifted.pipeline));
    if (expected !== actual) {
      return {
        error: "the closest blocks would not pass exactly the same alerts",
      };
    }
    return {
      ...lifted,
      identical: JSON.stringify(lifted.pipeline) === JSON.stringify(pipeline),
    };
  } catch (error) {
    return {
      error:
        error instanceof Unsupported ? error.message : "the conversion failed",
    };
  }
};

export const decompilePipeline = (pipeline, context = {}) => {
  const result = decompileFilterPipeline(pipeline, context);
  return result.filters &&
    result.projectionFields.length === 0 &&
    Object.values(result.newVariables).every((v) => v.length === 0)
    ? result.filters
    : null;
};

export default { decompileFilterPipeline, decompilePipeline, liftPipeline };
