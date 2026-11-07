import { v4 as uuidv4 } from "uuid";

export const toBlocks = (node: any): any => {
  if (Array.isArray(node)) return node.map(toBlocks);
  if (node?.children) {
    const logic = (node.logic ?? node.operator ?? "and").toLowerCase();
    return {
      id: node.id ?? uuidv4(),
      category: "block",
      logic: logic === "or" ? "Or" : "And",
      children: node.children.map(toBlocks),
      createdAt: Date.now(),
    };
  }
  return {
    id: node.id ?? uuidv4(),
    category: "condition",
    field: node.field,
    operator: node.operator,
    value: node.value,
    createdAt: Date.now(),
  };
};

export const asRootBlocks = (tree: any) => {
  const blocks = toBlocks(tree);
  return Array.isArray(blocks) ? blocks : [blocks];
};
