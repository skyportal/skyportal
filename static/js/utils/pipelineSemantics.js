export class Unsupported extends Error {}

const isPlainObject = (value) =>
  value !== null && typeof value === "object" && !Array.isArray(value);

const isOperator = (key) => typeof key === "string" && key.startsWith("$");

const join = (a, b) => (a ? `${a}.${b}` : b);

const orig = (path) => ({ kind: "orig", path });
const computed = (expr) => ({ kind: "expr", expr });
const obj = (fields = new Map(), base = null, origPath = null) => ({
  kind: "obj",
  fields,
  base,
  origPath,
});

const lookup = (node, segment) => {
  if (node.kind === "orig") return orig(join(node.path, segment));
  if (node.kind === "obj") {
    if (node.fields.has(segment)) return node.fields.get(segment);
    if (node.base) return lookup(node.base, segment);
    return null;
  }
  throw new Unsupported("it reads a field inside a computed value");
};

const keptPaths = (node, prefix = "") =>
  [...node.fields.entries()].flatMap(([key, child]) =>
    child.kind === "obj"
      ? keptPaths(child, join(prefix, key))
      : [join(prefix, key)],
  );

const pathInto = (expr, rest) => {
  if (rest.length === 0) return expr;
  if (typeof expr === "string" && expr.startsWith("$")) {
    return `${expr}.${rest.join(".")}`;
  }
  return { $__get: [expr, rest.join(".")] };
};

const resolvePath = (env, path) => {
  let node = env;
  const segments = path.split(".");
  for (const [i, segment] of segments.entries()) {
    if (node.kind === "orig")
      return `$${join(node.path, segments.slice(i).join("."))}`;
    if (node.kind === "expr") return pathInto(node.expr, segments.slice(i));
    node = lookup(node, segment);
    if (!node) return { $__missing: path };
  }
  if (node.kind === "orig") return `$${node.path}`;
  if (node.kind === "expr") return node.expr;
  if (node.origPath && !node.base) {
    return { $$partial: { path: node.origPath, keep: keptPaths(node) } };
  }
  throw new Unsupported(`it uses the whole ${path} object`);
};

const nodeAt = (env, path) => {
  let node = env;
  for (const segment of path.split(".")) {
    if (node.kind !== "obj" && node.kind !== "orig") return null;
    node = lookup(node, segment);
    if (!node) return null;
  }
  return node;
};

const setPath = (root, path, value) => {
  const segments = path.split(".");
  let node = root;
  segments.slice(0, -1).forEach((segment) => {
    let child = node.fields.get(segment);
    if (!child) {
      const inherited = node.base ? lookup(node.base, segment) : null;
      child =
        inherited?.kind === "orig"
          ? obj(new Map(), inherited, inherited.path)
          : inherited?.kind === "obj"
            ? obj(new Map(inherited.fields), inherited.base, inherited.origPath)
            : obj();
      node.fields.set(segment, child);
    } else if (child.kind === "orig") {
      child = obj(new Map(), child, child.path);
      node.fields.set(segment, child);
    } else if (child.kind === "obj") {
      child = obj(new Map(child.fields), child.base, child.origPath);
      node.fields.set(segment, child);
    } else {
      throw new Unsupported(`it sets ${path} inside a computed value`);
    }
    node = child;
  });
  node.fields.set(segments[segments.length - 1], value);
};

const removePath = (root, path) => {
  const segments = path.split(".");
  let node = root;
  for (const segment of segments.slice(0, -1)) {
    const child = node.fields.get(segment);
    if (!child || child.kind !== "obj") {
      throw new Unsupported(`it removes the nested field ${path}`);
    }
    node = child;
  }
  const last = segments[segments.length - 1];
  if (node.base) throw new Unsupported(`it removes the field ${path}`);
  node.fields.delete(last);
};

const cloneTree = (node) =>
  node.kind === "obj"
    ? obj(
        new Map([...node.fields].map(([k, v]) => [k, cloneTree(v)])),
        node.base,
        node.origPath,
      )
    : node;

const SYSTEM_VARIABLES = new Set(["ROOT", "CURRENT", "NOW", "CLUSTER_TIME"]);
const PASSTHROUGH_VARIABLES = new Set(["REMOVE"]);

const resolveExpr = (expr, ctx, scope) => {
  if (typeof expr === "string") {
    if (expr.startsWith("$$")) {
      const [name, ...rest] = expr.slice(2).split(".");
      if (PASSTHROUGH_VARIABLES.has(name) && rest.length === 0) return expr;
      if (SYSTEM_VARIABLES.has(name)) {
        throw new Unsupported(`it uses $$${name}`);
      }
      if (!(name in scope))
        throw new Unsupported(`it uses the undefined variable $$${name}`);
      const bound = scope[name];
      if (bound.inline !== undefined) return pathInto(bound.inline, rest);
      return [`$$${bound.name}`, ...rest].join(".");
    }
    if (expr.startsWith("$")) return resolvePath(ctx.env, expr.slice(1));
    return expr;
  }
  if (Array.isArray(expr)) return expr.map((e) => resolveExpr(e, ctx, scope));
  if (!isPlainObject(expr)) return expr;

  const keys = Object.keys(expr);
  if (keys.length === 1 && isOperator(keys[0])) {
    const [op] = keys;
    const arg = expr[op];
    if (op === "$literal") return expr;
    if (op === "$map" || op === "$filter") {
      const name = `__v${ctx.depth + 1}`;
      const as = arg.as ?? "this";
      const input = resolveExpr(arg.input, ctx, scope);
      const inner = { ...ctx, depth: ctx.depth + 1 };
      const innerScope = { ...scope, [as]: { name } };
      const body = op === "$map" ? "in" : "cond";
      const result = { input, as: name };
      result[body] = resolveExpr(arg[body], inner, innerScope);
      if (arg.limit !== undefined) {
        result.limit = resolveExpr(arg.limit, ctx, scope);
      }
      return { [op]: result };
    }
    if (op === "$reduce") {
      const depth = ctx.depth + 1;
      const inner = { ...ctx, depth };
      return {
        $reduce: {
          input: resolveExpr(arg.input, ctx, scope),
          initialValue: resolveExpr(arg.initialValue, ctx, scope),
          in: resolveExpr(arg.in, inner, {
            ...scope,
            this: { name: `__t${depth}` },
            value: { name: `__a${depth}` },
          }),
        },
      };
    }
    if (op === "$let") {
      const bindings = Object.fromEntries(
        Object.entries(arg.vars || {}).map(([name, value]) => [
          name,
          { inline: resolveExpr(value, ctx, scope) },
        ]),
      );
      return resolveExpr(arg.in, ctx, { ...scope, ...bindings });
    }
    return { [op]: resolveExpr(arg, ctx, scope) };
  }
  if (keys.some(isOperator))
    throw new Unsupported("it has an invalid expression");
  return Object.fromEntries(
    keys.map((key) => [key, resolveExpr(expr[key], ctx, scope)]),
  );
};

const QUERY_LOGIC = new Set(["$and", "$or", "$nor"]);

const resolveQuery = (query, ctx) => {
  if (!isPlainObject(query)) throw new Unsupported("it has an invalid $match");
  const clauses = Object.entries(query).flatMap(([key, value]) => {
    if (QUERY_LOGIC.has(key)) {
      if (!Array.isArray(value) || value.length === 0) {
        throw new Unsupported(`it has an empty ${key}`);
      }
      return [{ [key]: value.map((q) => resolveQuery(q, ctx)) }];
    }
    if (key === "$expr") return [{ $expr: resolveExpr(value, ctx, {}) }];
    if (key === "$comment") return [];
    if (isOperator(key)) throw new Unsupported(`it uses ${key}`);
    const target = resolvePath(ctx.env, key);
    if (typeof target === "string") return [{ [target.slice(1)]: value }];
    return [{ $$on: [target, value] }];
  });
  if (clauses.length === 0) return {};
  return clauses.length === 1 ? clauses[0] : { $and: clauses };
};

const isInclusion = (value) =>
  value === true || (typeof value === "number" && value !== 0);
const isExclusion = (value) => value === false || value === 0;

const ensureParents = (target, path, env) => {
  const segments = path.split(".");
  let node = target;
  segments.slice(0, -1).forEach((segment, i) => {
    if (!node.fields.has(segment)) {
      const source = nodeAt(env, segments.slice(0, i + 1).join("."));
      node.fields.set(
        segment,
        obj(new Map(), null, source?.kind === "orig" ? source.path : null),
      );
    }
    node = node.fields.get(segment);
  });
};

const projectInto = (target, spec, prefix, ctx) => {
  Object.entries(spec).forEach(([key, value]) => {
    const path = join(prefix, key);
    if (path === "_id") return;
    if (isInclusion(value)) {
      const node = nodeAt(ctx.env, path);
      if (node) {
        ensureParents(target, path, ctx.env);
        setPath(target, path, node);
      }
    } else if (isExclusion(value)) {
      throw new Unsupported("a $project both keeps and removes fields");
    } else if (
      isPlainObject(value) &&
      Object.keys(value).length > 0 &&
      !Object.keys(value).some(isOperator)
    ) {
      projectInto(target, value, path, ctx);
    } else {
      setPath(
        target,
        path,
        define(resolveExpr(value, ctx, {}), key.split(".").pop(), ctx),
      );
    }
  });
};

const define = (expr, name, ctx) => {
  if (
    typeof expr === "string" &&
    expr.startsWith("$") &&
    !expr.startsWith("$$")
  ) {
    return orig(expr.slice(1));
  }
  if (isPlainObject(expr) && expr.$$def !== undefined) return computed(expr);
  ctx.defs.push({ name, expr });
  return computed({ $$def: ctx.defs.length - 1 });
};

const projectStage = (spec, ctx) => {
  const entries = Object.entries(spec);
  const nonId = entries.filter(([key]) => key !== "_id");
  if (nonId.length > 0 && nonId.every(([, value]) => isExclusion(value))) {
    const next = cloneTree(ctx.env);
    nonId.forEach(([key]) => removePath(next, key));
    if (isExclusion(spec._id)) throw new Unsupported("it removes _id");
    return next;
  }
  const next = obj();
  if (spec._id === undefined || isInclusion(spec._id)) {
    setPath(next, "_id", nodeAt(ctx.env, "_id"));
  } else if (isExclusion(spec._id)) {
    throw new Unsupported("it removes _id");
  } else {
    throw new Unsupported("it changes _id");
  }
  projectInto(next, spec, "", ctx);
  return next;
};

const addFieldsStage = (spec, ctx) => {
  const next = cloneTree(ctx.env);
  const values = Object.entries(spec).map(([key, value]) => [
    key,
    define(resolveExpr(value, ctx, {}), key.split(".").pop(), ctx),
  ]);
  values.forEach(([key, node]) => setPath(next, key, node));
  return next;
};

export const readPipeline = (pipeline) => {
  if (!Array.isArray(pipeline) || pipeline.length === 0) {
    throw new Unsupported("it is not a list of stages");
  }
  const ctx = { env: obj(new Map(), orig("")), defs: [], depth: 0 };
  const where = [];
  pipeline.forEach((stage) => {
    if (!isPlainObject(stage) || Object.keys(stage).length !== 1) {
      throw new Unsupported("it has an invalid stage");
    }
    const [name] = Object.keys(stage);
    const spec = stage[name];
    if (name === "$match") {
      const resolved = resolveQuery(spec, ctx);
      if (Object.keys(resolved).length > 0) where.push(resolved);
    } else if (name === "$project") {
      ctx.env = projectStage(spec, ctx);
    } else if (name === "$addFields" || name === "$set") {
      ctx.env = addFieldsStage(spec, ctx);
    } else if (name === "$unset") {
      const next = cloneTree(ctx.env);
      [].concat(spec).forEach((path) => removePath(next, path));
      ctx.env = next;
    } else {
      throw new Unsupported(`it uses the ${name} stage`);
    }
  });

  const objectId = nodeAt(ctx.env, "objectId");
  const id = nodeAt(ctx.env, "_id");
  if (objectId?.kind !== "orig" || objectId.path !== "objectId") {
    throw new Unsupported("it drops objectId");
  }
  if (id?.kind !== "orig" || id.path !== "_id") {
    throw new Unsupported("it drops _id");
  }

  const annotations = {};
  const collect = (node, path) => {
    if (node.kind === "obj") {
      if (node.base)
        throw new Unsupported("it merges new annotations into existing ones");
      node.fields.forEach((child, key) => collect(child, join(path, key)));
    } else if (node.kind === "orig") {
      annotations[path] = `$${node.path}`;
    } else {
      annotations[path] = node.expr;
    }
  };
  const annotationsNode = nodeAt(ctx.env, "annotations");
  if (annotationsNode && !(annotationsNode.kind === "orig")) {
    collect(annotationsNode, "");
  }
  return { where, defs: ctx.defs, annotations };
};

const BOOLEAN_OPS = new Set([
  "$and",
  "$or",
  "$not",
  "$eq",
  "$ne",
  "$gt",
  "$gte",
  "$lt",
  "$lte",
  "$in",
  "$anyElementTrue",
  "$allElementsTrue",
  "$isNumber",
  "$isArray",
  "$regexMatch",
]);

const REDUCER_OPS = new Set(["$min", "$max", "$sum", "$avg"]);

const NUMERIC_OPS = new Set([
  "$add",
  "$subtract",
  "$multiply",
  "$divide",
  "$abs",
  "$pow",
  "$sqrt",
  "$ln",
  "$log",
  "$log10",
  "$exp",
  "$floor",
  "$ceil",
  "$trunc",
  "$round",
  "$mod",
  "$sin",
  "$cos",
  "$tan",
  "$asin",
  "$acos",
  "$atan",
  "$atan2",
  "$degreesToRadians",
  "$radiansToDegrees",
]);

const opOf = (expr) =>
  isPlainObject(expr) && Object.keys(expr).length === 1
    ? Object.keys(expr)[0]
    : null;

export const isBooleanExpr = (expr) =>
  typeof expr === "boolean" || BOOLEAN_OPS.has(opOf(expr));

export const isNumericExpr = (expr) => NUMERIC_OPS.has(opOf(expr));

const UNARY = new Set([
  "$abs",
  "$sqrt",
  "$ln",
  "$log10",
  "$exp",
  "$floor",
  "$ceil",
  "$trunc",
  "$not",
  "$size",
  "$isNumber",
  "$isArray",
  "$anyElementTrue",
  "$allElementsTrue",
  "$toString",
  "$toDouble",
  "$toInt",
  "$toBool",
  "$degreesToRadians",
  "$radiansToDegrees",
  "$sin",
  "$cos",
  "$tan",
  "$asin",
  "$acos",
  "$atan",
  "$max",
  "$min",
  "$sum",
  "$avg",
  "$stdDevPop",
]);

const COMMUTATIVE = new Set([
  "$add",
  "$multiply",
  "$and",
  "$or",
  "$max",
  "$min",
]);

const ARRAY_CONSUMERS = new Set([
  "$anyElementTrue",
  "$allElementsTrue",
  "$size",
]);

const SHAPE_ONLY = new Set([
  "$size",
  "$type",
  "$isArray",
  "$anyElementTrue",
  "$allElementsTrue",
]);

const key = (value) => JSON.stringify(value);
const sortByKey = (values) =>
  values
    .map((value) => [key(value), value])
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([, value]) => value);

const stripEmptyFallback = (expr) => {
  const op = opOf(expr);
  if (
    op === "$ifNull" &&
    Array.isArray(expr.$ifNull) &&
    expr.$ifNull.length === 2 &&
    Array.isArray(expr.$ifNull[1]) &&
    expr.$ifNull[1].length === 0
  ) {
    return stripEmptyFallback(expr.$ifNull[0]);
  }
  if (op === "$map" || op === "$filter") {
    return { [op]: { ...expr[op], input: stripEmptyFallback(expr[op].input) } };
  }
  return expr;
};

const variablesUsed = (expr, name, found = new Set()) => {
  if (typeof expr === "string" && expr.startsWith(`$$${name}`)) {
    const rest = expr.slice(name.length + 2);
    if (rest === "") found.add("");
    else if (rest.startsWith(".")) found.add(rest.slice(1));
  } else if (Array.isArray(expr)) {
    expr.forEach((e) => variablesUsed(e, name, found));
  } else if (isPlainObject(expr)) {
    Object.values(expr).forEach((e) => variablesUsed(e, name, found));
  }
  return found;
};

const coveredBy = (path, keep) =>
  keep.some((k) => path === k || path.startsWith(`${k}.`));

const unwrapPartial = (expr, allowed) => {
  if (isPlainObject(expr) && expr.$$partial) {
    if (!allowed(expr.$$partial.keep)) {
      throw new Unsupported(
        "it reads array fields that an earlier $project removed",
      );
    }
    return `$${expr.$$partial.path}`;
  }
  if (opOf(expr) === "$ifNull" && Array.isArray(expr.$ifNull)) {
    return {
      $ifNull: [
        unwrapPartial(expr.$ifNull[0], allowed),
        ...expr.$ifNull.slice(1),
      ],
    };
  }
  return expr;
};

const NORMALIZED_DEFS = new WeakMap();

export const normalizeExpr = (expr, defs) => {
  if (Array.isArray(expr)) return expr.map((e) => normalizeExpr(e, defs));
  if (!isPlainObject(expr)) return expr;
  if (expr.$$def !== undefined) {
    if (!NORMALIZED_DEFS.has(defs)) NORMALIZED_DEFS.set(defs, new Map());
    const cache = NORMALIZED_DEFS.get(defs);
    if (!cache.has(expr.$$def)) {
      cache.set(expr.$$def, normalizeExpr(defs[expr.$$def].expr, defs));
    }
    return cache.get(expr.$$def);
  }
  if (expr.$$partial)
    throw new Unsupported("it reads a value that an earlier $project cut down");

  const keys = Object.keys(expr);
  if (keys.length !== 1 || !isOperator(keys[0])) {
    return Object.fromEntries(
      keys.map((k) => [k, normalizeExpr(expr[k], defs)]),
    );
  }
  const [op] = keys;
  let arg = expr[op];

  if (op === "$literal") return expr;
  if (op === "$expr") return normalizeExpr(arg, defs);

  if (op === "$map" || op === "$filter") {
    const body = op === "$map" ? "in" : "cond";
    const input = unwrapPartial(arg.input, (keep) => {
      const used = variablesUsed(arg[body], arg.as);
      return ![...used].some((p) => p === "" || !coveredBy(p, keep));
    });
    const result = {
      input: normalizeExpr(input, defs),
      as: arg.as,
      [body]: normalizeExpr(arg[body], defs),
    };
    if (arg.limit !== undefined) result.limit = normalizeExpr(arg.limit, defs);
    return { [op]: result };
  }

  if (op === "$cond") {
    const [ifExpr, thenExpr, elseExpr] = Array.isArray(arg)
      ? arg
      : [arg.if, arg.then, arg.else];
    return normalizeExpr(
      {
        $switch: {
          branches: [{ case: ifExpr, then: thenExpr }],
          default: elseExpr,
        },
      },
      defs,
    );
  }
  if (op === "$first") return normalizeExpr({ $arrayElemAt: [arg, 0] }, defs);
  if (op === "$last") return normalizeExpr({ $arrayElemAt: [arg, -1] }, defs);

  if (op === "$switch") {
    const branches = arg.branches.map((b) => ({
      case: normalizeExpr(b.case, defs),
      then: normalizeExpr(b.then, defs),
    }));
    const fallback =
      arg.default === undefined ? undefined : normalizeExpr(arg.default, defs);
    if (branches.length === 1 && isBooleanExpr(branches[0].case)) {
      const [{ case: test, then }] = branches;
      if (then === true && fallback === false) return test;
      if (then === false && fallback === true) return negate(test);
    }
    const result = { branches };
    if (fallback !== undefined) result.default = fallback;
    return { $switch: result };
  }

  if (UNARY.has(op) && Array.isArray(arg) && arg.length === 1) [arg] = arg;
  if (REDUCER_OPS.has(op) && Array.isArray(arg) && arg.length === 1)
    [arg] = arg;
  if (op === "$round" && !Array.isArray(arg)) arg = [arg, 0];
  if (op === "$round" && Array.isArray(arg) && arg.length === 1)
    arg = [arg[0], 0];

  if (SHAPE_ONLY.has(op)) arg = unwrapPartial(arg, () => true);
  let normalized = normalizeExpr(arg, defs);
  if (ARRAY_CONSUMERS.has(op) || REDUCER_OPS.has(op)) {
    normalized = stripEmptyFallback(normalized);
  }

  if (op === "$not") {
    return negate(normalized);
  }
  if (
    (op === "$eq" || op === "$ne") &&
    Array.isArray(normalized) &&
    normalized.length === 2
  ) {
    const [left, right] = normalized;
    const [test, flag] =
      typeof left === "boolean" ? [right, left] : [left, right];
    if (typeof flag === "boolean" && isBooleanExpr(test)) {
      return flag === (op === "$eq") ? test : negate(test);
    }
  }
  if (COMMUTATIVE.has(op) && Array.isArray(normalized)) {
    const flat = normalized.flatMap((e) =>
      opOf(e) === op && Array.isArray(e[op]) ? e[op] : [e],
    );
    if ((op === "$and" || op === "$or") && flat.length === 1) return flat[0];
    return { [op]: sortByKey(flat) };
  }
  return { [op]: normalized };
};

const OPPOSITE = {
  $eq: "$ne",
  $ne: "$eq",
  $gt: "$lte",
  $lte: "$gt",
  $gte: "$lt",
  $lt: "$gte",
};

const negate = (expr) => {
  const op = opOf(expr);
  if (op === "$not" && isBooleanExpr(expr.$not)) return expr.$not;
  if (OPPOSITE[op] && Array.isArray(expr[op]) && expr[op].length === 2) {
    return { [OPPOSITE[op]]: expr[op] };
  }
  return { $not: expr };
};

const atomFromExpr = (expr) => {
  const op = opOf(expr);
  if (op === "$and") return { and: expr.$and.map(atomFromExpr) };
  if (op === "$or") return { or: expr.$or.map(atomFromExpr) };
  if (op === "$not") return { not: atomFromExpr(expr.$not) };
  return { e: expr };
};

const QUERY_COMPARISONS = new Set([
  "$eq",
  "$ne",
  "$gt",
  "$gte",
  "$lt",
  "$lte",
  "$in",
  "$nin",
  "$exists",
  "$size",
  "$type",
  "$elemMatch",
  "$all",
  "$regex",
  "$options",
  "$mod",
]);

let booleanFields = new Set();

const isSingleLiteral = (value) =>
  Array.isArray(value) &&
  value.length === 1 &&
  (value[0] === null ||
    ["boolean", "number", "string"].includes(typeof value[0]));

const conditionAtoms = (target, condition, defs, onComputed) => {
  const ops =
    isPlainObject(condition) &&
    Object.keys(condition).length > 0 &&
    Object.keys(condition).every(isOperator)
      ? Object.entries(condition)
      : [["$eq", condition]];
  return ops
    .map(([op, value]) => {
      if (op === "$not") {
        return {
          not: { and: conditionAtoms(target, value, defs, onComputed) },
        };
      }
      if (!QUERY_COMPARISONS.has(op)) throw new Unsupported(`it uses ${op}`);
      if (op === "$options") return null;
      let v = value;
      if (op === "$exists") v = Boolean(value);
      if (
        (op === "$in" || op === "$nin") &&
        booleanFields.has(target) &&
        Array.isArray(value)
      ) {
        v = [...new Set(value.filter((x) => typeof x === "boolean"))];
      }
      if (op === "$in" && isSingleLiteral(v)) {
        return onComputed
          ? onComputed("$eq", v[0])
          : { f: target, op: "$eq", v: v[0] };
      }
      if (op === "$in" || op === "$nin") v = sortByKey(value);
      if (op === "$regex") {
        v = { pattern: String(value), options: condition.$options ?? "" };
      }
      return onComputed ? onComputed(op, v) : { f: target, op, v };
    })
    .filter(Boolean);
};

const computedAtoms = (expr, condition, defs) => {
  const target = normalizeExpr(expr, defs);
  return conditionAtoms(null, condition, defs, (op, v) => {
    if (isBooleanExpr(target)) {
      if ((op === "$eq" && v === true) || (op === "$ne" && v === false)) {
        return atomFromExpr(target);
      }
      if ((op === "$eq" && v === false) || (op === "$ne" && v === true)) {
        return { not: atomFromExpr(target) };
      }
    }
    if (isNumericExpr(target) && typeof v === "number") {
      if (op === "$gt" || op === "$gte" || op === "$eq" || op === "$ne") {
        return { e: { [op]: [target, v] } };
      }
      if (op === "$lt" || op === "$lte") {
        return {
          and: [{ e: { [op]: [target, v] } }, { e: { $isNumber: target } }],
        };
      }
    }
    return { fe: target, op, v };
  });
};

const normalizeQuery = (query, defs) => {
  const atoms = Object.entries(query).flatMap(([field, condition]) => {
    if (field === "$and") return condition.map((q) => normalizeQuery(q, defs));
    if (field === "$or")
      return [{ or: condition.map((q) => normalizeQuery(q, defs)) }];
    if (field === "$nor") {
      return [{ not: { or: condition.map((q) => normalizeQuery(q, defs)) } }];
    }
    if (field === "$expr")
      return [atomFromExpr(normalizeExpr(condition, defs))];
    if (field === "$$on")
      return computedAtoms(condition[0], condition[1], defs);
    return conditionAtoms(field, condition, defs);
  });
  return { and: atoms };
};

const canonical = (formula) => {
  if (formula.and) {
    const parts = formula.and
      .map(canonical)
      .flatMap((p) => (p.and ? p.and : [p]));
    const unique = [...new Map(parts.map((p) => [key(p), p])).values()];
    return unique.length === 1 ? unique[0] : { and: sortByKey(unique) };
  }
  if (formula.or) {
    const parts = formula.or.map(canonical).flatMap((p) => (p.or ? p.or : [p]));
    const unique = [...new Map(parts.map((p) => [key(p), p])).values()];
    return unique.length === 1 ? unique[0] : { or: sortByKey(unique) };
  }
  if (formula.not) {
    const inner = canonical(formula.not);
    if (inner.not) return inner.not;
    if (inner.e && OPPOSITE[opOf(inner.e)]) return { e: negate(inner.e) };
    return { not: inner };
  }
  return formula;
};

export const describePipeline = (pipeline, options = {}) => {
  booleanFields = new Set(options.booleanFields ?? []);
  const { where, defs, annotations } = readPipeline(pipeline);
  const condition = canonical({
    and: where.map((q) => normalizeQuery(q, defs)),
  });
  const output = Object.fromEntries(
    Object.keys(annotations)
      .sort()
      .map((path) => [path, normalizeExpr(annotations[path], defs)]),
  );
  return { where: condition, annotations: output };
};

export const sameBehavior = (a, b) => {
  try {
    return key(describePipeline(a)) === key(describePipeline(b));
  } catch (error) {
    if (error instanceof Unsupported) return false;
    throw error;
  }
};
