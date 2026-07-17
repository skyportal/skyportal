export class RobustLatexToMongoConverter {
  constructor() {
    // Updated pattern to allow fields starting with numbers (e.g., "10days", "10magpsf")
    this.fieldPattern = /([a-zA-Z0-9_][a-zA-Z0-9_.]*)/g;
    this.numberPattern = /^-?\d+\.?\d*$/;
  }

  // Convert LaTeX expression to MongoDB aggregation expression
  convertToMongo(latexExpression, isInArrayFilter = false) {
    if (!latexExpression || typeof latexExpression !== "string") {
      return latexExpression;
    }

    try {
      let expression = this._cleanExpression(latexExpression);

      if (this._isSimpleField(expression)) {
        return `$${expression}`;
      }

      if (this._isSimpleNumber(expression)) {
        return parseFloat(expression);
      }

      return this._parseWithExpressionTree(expression, 0, isInArrayFilter);
    } catch (error) {
      console.warn(
        "Failed to convert LaTeX expression:",
        latexExpression,
        error,
      );
      return `$${latexExpression}`;
    }
  }

  // Convert \frac{num}{den} to (num)/(den), recursively
  _convertFractions(expression) {
    let result = expression;
    let hasMore = true;

    while (hasMore) {
      const fracPattern =
        /\\frac\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}/;
      const match = result.match(fracPattern);

      if (match) {
        const [fullMatch, numerator, denominator] = match;
        const processedNum = this._convertFractions(numerator.trim());
        const processedDen = this._convertFractions(denominator.trim());
        result = result.replace(
          fullMatch,
          `(${processedNum})/(${processedDen})`,
        );
      } else {
        hasMore = false;
      }
    }

    return result;
  }

  // Convert name_{subscript} to name_subscript (flat notation)
  _convertUnderscoreSubscripts(expression) {
    let result = expression;
    let hasMore = true;

    while (hasMore) {
      const underscorePattern =
        /([a-zA-Z_][a-zA-Z0-9_]*?)_\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}/;
      const match = result.match(underscorePattern);

      if (match) {
        const [fullMatch, baseName, subscript] = match;
        const processedSubscript = this._convertUnderscoreSubscripts(
          subscript.trim(),
        );
        const flatSubscript = processedSubscript.replace(/[{}]/g, "");
        result = result.replace(fullMatch, `${baseName}_${flatSubscript}`);
      } else {
        hasMore = false;
      }
    }

    return result;
  }

  _cleanExpression(expression) {
    let cleaned = this._convertFractions(expression);
    cleaned = this._convertUnderscoreSubscripts(cleaned);

    cleaned = cleaned
      .replace(/\\left\(/g, "(")
      .replace(/\\right\)/g, ")")
      .replace(/\\left\[/g, "(")
      .replace(/\\right\]/g, ")")
      .replace(/\\left\\\{/g, "(")
      .replace(/\\right\\\}/g, ")");

    let prevCleaned;
    do {
      prevCleaned = cleaned;
      cleaned = this._replaceLatexAbsoluteValues(cleaned);
    } while (cleaned !== prevCleaned);

    return cleaned
      .replace(/\s+/g, " ")
      .replace(/\\cdot/g, "*")
      .replace(/\\times/g, "*")
      .replace(/\\div/g, "/")
      .trim();
  }

  // Replace \left|...\right| with |...|, handling nesting
  _replaceLatexAbsoluteValues(expression) {
    let result = expression;
    let i = 0;

    while (i < result.length) {
      if (i + 5 < result.length && result.substring(i, i + 6) === "\\left|") {
        let level = 1;
        let j = i + 6;

        while (j < result.length && level > 0) {
          if (
            j + 5 < result.length &&
            result.substring(j, j + 6) === "\\left|"
          ) {
            level++;
            j += 6;
          } else if (
            j + 6 < result.length &&
            result.substring(j, j + 7) === "\\right|"
          ) {
            level--;
            if (level === 0) {
              const innerContent = result.substring(i + 6, j);
              const replacement = `|${innerContent}|`;
              result =
                result.substring(0, i) + replacement + result.substring(j + 7);
              i += replacement.length;
              break;
            } else {
              j += 7;
            }
          } else {
            j++;
          }
        }

        if (level > 0) {
          i++;
        }
      } else {
        i++;
      }
    }

    return result;
  }

  _isSimpleField(expression) {
    return /^[a-zA-Z_][a-zA-Z0-9_.]*$/.test(expression);
  }

  _isSimpleNumber(expression) {
    return this.numberPattern.test(expression);
  }

  _parseWithExpressionTree(expression, depth = 0, isInArrayFilter = false) {
    if (!expression || typeof expression !== "string") {
      return expression || "";
    }

    if (depth > 10) {
      return `$${expression}`;
    }

    const functionNames = ["abs", "sqrt", "sin", "cos", "tan", "log", "ln"];
    for (const funcName of functionNames) {
      if (expression.startsWith(`${funcName}(`)) {
        const innerContent = this._extractFunctionArgument(
          expression,
          funcName,
        );
        if (innerContent !== null) {
          return {
            [`$${funcName}`]: this._parseWithExpressionTree(
              innerContent,
              depth + 1,
              isInArrayFilter,
            ),
          };
        }
      }
    }

    if (
      expression.startsWith("(") &&
      expression.endsWith(")") &&
      this._isBalancedParentheses(expression.slice(1, -1))
    ) {
      return this._parseWithExpressionTree(
        expression.slice(1, -1),
        depth + 1,
        isInArrayFilter,
      );
    }

    const mainOp = this._findMainOperator(expression);
    if (mainOp) {
      const { left, operator, right } = mainOp;
      const leftVal = this._parseWithExpressionTree(
        left,
        depth + 1,
        isInArrayFilter,
      );
      const rightVal = this._parseWithExpressionTree(
        right,
        depth + 1,
        isInArrayFilter,
      );

      const opMap = {
        "+": "$add",
        "-": "$subtract",
        "*": "$multiply",
        "/": "$divide",
        "^": "$pow",
        "**": "$pow",
      };
      if (opMap[operator]) {
        return { [opMap[operator]]: [leftVal, rightVal] };
      }
    }

    // Handle absolute value (LaTeX has already been converted to standard notation)
    const absMatch = expression.match(/^\|(.+)\|$/);
    if (absMatch) {
      return {
        $abs: this._parseWithExpressionTree(
          absMatch[1],
          depth + 1,
          isInArrayFilter,
        ),
      };
    }

    const leftAbsMatch = expression.match(/^left\|(.+)$/);
    if (leftAbsMatch) {
      return {
        $abs: this._parseWithExpressionTree(
          leftAbsMatch[1],
          depth + 1,
          isInArrayFilter,
        ),
      };
    }

    const rightAbsMatch = expression.match(/^(.+)\|right$/);
    if (rightAbsMatch) {
      return {
        $abs: this._parseWithExpressionTree(
          rightAbsMatch[1],
          depth + 1,
          isInArrayFilter,
        ),
      };
    }

    return this._convertAtomicValue(expression, depth, isInArrayFilter);
  }

  _isBalancedParentheses(expression) {
    let count = 0;
    for (const char of expression) {
      if (char === "(") count++;
      if (char === ")") count--;
      if (count < 0) return false;
    }
    return count === 0;
  }

  _extractFunctionArgument(expression, funcName) {
    const prefix = `${funcName}(`;
    if (!expression.startsWith(prefix)) {
      return null;
    }

    let parenCount = 0;
    const startIndex = prefix.length;

    for (let i = startIndex - 1; i < expression.length; i++) {
      if (expression[i] === "(") {
        parenCount++;
      } else if (expression[i] === ")") {
        parenCount--;
        if (parenCount === 0) {
          const content = expression.substring(startIndex, i);
          return i === expression.length - 1 ? content : null;
        }
      }
    }

    return null;
  }

  _findMainOperator(expression) {
    const operators = [
      { ops: ["**", "^"], precedence: 3 },
      { ops: ["*", "/"], precedence: 2 },
      { ops: ["+", "-"], precedence: 1 },
    ];

    let parenLevel = 0;
    let absLevel = 0;
    let bestOp = null;
    let bestPrec = Infinity;
    let funcLevel = 0;

    for (let i = expression.length - 1; i >= 0; i--) {
      const char = expression[i];

      if (char === ")") {
        parenLevel++;
        const beforeParen = expression.substring(0, i);
        if (/\b(sqrt|sin|cos|tan|log|ln)$/.test(beforeParen)) {
          funcLevel++;
        }
      }
      if (char === "(") {
        parenLevel--;
        if (funcLevel > 0) {
          funcLevel--;
        }
      }

      if (char === "|") {
        const beforeBar = expression.substring(0, i);
        const afterBar = expression.substring(i + 1);

        if (beforeBar.endsWith("left") || afterBar.startsWith("right")) {
          continue;
        }

        absLevel = absLevel > 0 ? absLevel - 1 : absLevel + 1;
      }

      if (parenLevel === 0 && funcLevel === 0 && absLevel === 0) {
        for (const { ops, precedence } of operators) {
          for (const op of ops) {
            if (op.length > 1) {
              const startIdx = i - op.length + 1;
              if (
                startIdx >= 0 &&
                expression.substring(startIdx, i + 1) === op &&
                precedence <= bestPrec
              ) {
                const left = expression.substring(0, startIdx).trim();
                const right = expression.substring(i + 1).trim();
                if (left && right) {
                  bestOp = { left, operator: op, right };
                  bestPrec = precedence;
                }
              }
            } else if (op === char && precedence <= bestPrec) {
              if (
                i > 0 &&
                /[a-zA-Z]/.test(char) &&
                /[a-zA-Z]/.test(expression[i - 1])
              ) {
                continue;
              }

              if (
                char === "-" &&
                (i === 0 || /[+\-*/^(]/.test(expression[i - 1]))
              ) {
                continue;
              }

              const left = expression.substring(0, i).trim();
              const right = expression.substring(i + 1).trim();

              if (left && right) {
                bestOp = { left, operator: char, right };
                bestPrec = precedence;
              }
            }
          }
        }
      }
    }

    return bestOp;
  }

  _convertAtomicValue(value, depth = 0, isInArrayFilter = false) {
    const trimmed = value.trim();

    // Multi-argument aggregate functions: min(...), max(...), sum(...), avg(...)
    const aggregateFuncMatch = trimmed.match(/^(min|max|sum|avg)\((.+)\)$/);
    if (aggregateFuncMatch) {
      const [, funcName, argsString] = aggregateFuncMatch;
      const args = this._parseCommaSeparatedArgs(
        argsString,
        depth,
        isInArrayFilter,
      );
      const operatorMap = {
        min: "$min",
        max: "$max",
        sum: "$sum",
        avg: "$avg",
      };
      return { [operatorMap[funcName]]: args };
    }

    // abs(expression)
    const absFuncMatch = trimmed.match(/^abs\((.+)\)$/);
    if (absFuncMatch) {
      return {
        $abs: this._parseWithExpressionTree(
          absFuncMatch[1],
          depth + 1,
          isInArrayFilter,
        ),
      };
    }

    // field^exponent
    const powerMatch = trimmed.match(/^([a-zA-Z_][a-zA-Z0-9_.]*)\^(.+)$/);
    if (powerMatch) {
      const [, base, exponent] = powerMatch;
      return {
        $pow: [
          `$${base}`,
          this._parseWithExpressionTree(exponent, depth + 1, isInArrayFilter),
        ],
      };
    }

    if (
      depth < 5 &&
      (trimmed.includes("^") ||
        trimmed.includes("|") ||
        trimmed.startsWith("left|") ||
        trimmed.endsWith("|right") ||
        trimmed.startsWith("abs(") ||
        trimmed.includes("\\left|") ||
        trimmed.includes("\\right|")) &&
      !this._isSimpleField(trimmed) &&
      !this.numberPattern.test(trimmed)
    ) {
      return this._parseWithExpressionTree(trimmed, depth + 1, isInArrayFilter);
    }

    if (this.numberPattern.test(trimmed)) {
      return parseFloat(trimmed);
    }

    if (this._isSimpleField(trimmed) || trimmed.startsWith("$")) {
      return trimmed.startsWith("$") ? trimmed : `$${trimmed}`;
    }

    return `$${trimmed}`;
  }

  // Split argsString at top-level commas (respecting parens and braces)
  _splitAtTopLevelCommas(argsString) {
    const args = [];
    let current = "";
    let parenDepth = 0;
    let braceDepth = 0;

    for (const char of argsString) {
      if (char === "(") {
        parenDepth++;
        current += char;
      } else if (char === ")") {
        parenDepth--;
        current += char;
      } else if (char === "{") {
        braceDepth++;
        current += char;
      } else if (char === "}") {
        braceDepth--;
        current += char;
      } else if (char === "," && parenDepth === 0 && braceDepth === 0) {
        if (current.trim()) args.push(current.trim());
        current = "";
      } else {
        current += char;
      }
    }

    if (current.trim()) args.push(current.trim());
    return args;
  }

  _parseCommaSeparatedArgs(argsString, depth = 0, isInArrayFilter = false) {
    return this._splitAtTopLevelCommas(argsString).map((arg) =>
      this._parseWithExpressionTree(arg, depth + 1, isInArrayFilter),
    );
  }

  _splitCommaSeparatedFields(argsString) {
    // Same as _splitAtTopLevelCommas but only tracks parens (no braces needed here)
    return this._splitAtTopLevelCommas(argsString);
  }

  // Extract field dependencies from a LaTeX expression
  extractFieldDependencies(latexExpression) {
    if (!latexExpression || typeof latexExpression !== "string") {
      return [];
    }

    const cleanedExpression = this._cleanExpression(latexExpression);
    const fields = new Set();

    const aggregateFuncPattern = /\b(min|max|sum|avg)\s*\(([^)]+)\)/g;
    let aggregateMatch;
    while (
      (aggregateMatch = aggregateFuncPattern.exec(cleanedExpression)) !== null
    ) {
      const args = this._splitCommaSeparatedFields(aggregateMatch[2]);
      args.forEach((arg) => {
        const trimmedArg = arg.trim();
        if (
          trimmedArg &&
          !this.numberPattern.test(trimmedArg) &&
          !trimmedArg.includes("(") &&
          !trimmedArg.includes("+") &&
          !trimmedArg.includes("-") &&
          !trimmedArg.includes("*") &&
          !trimmedArg.includes("/") &&
          !trimmedArg.startsWith("this.") &&
          trimmedArg !== "this"
        ) {
          fields.add(trimmedArg);
        }
      });
    }

    const fieldPattern = /([a-zA-Z0-9_][a-zA-Z0-9_.]*)/g;
    for (const [, field] of cleanedExpression.matchAll(fieldPattern)) {
      if (
        !this.numberPattern.test(field) &&
        ![
          "sqrt",
          "sin",
          "cos",
          "tan",
          "log",
          "ln",
          "abs",
          "min",
          "max",
          "sum",
          "avg",
          "left",
          "right",
          "frac",
        ].includes(field) &&
        !field.startsWith("this.") &&
        field !== "this"
      ) {
        fields.add(field);
      }
    }

    return [...fields];
  }
}

export const latexToMongoConverter = new RobustLatexToMongoConverter();
