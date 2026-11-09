import { v4 as uuidv4 } from "uuid";

const deepCopy = (value: any) => JSON.parse(JSON.stringify(value));

export const mapBlock = (
  filters: any[],
  blockId: string,
  update: (block: any) => any,
): any[] => {
  const visit = (block: any): any =>
    block.id === blockId
      ? update(block)
      : {
          ...block,
          children: (block.children ?? []).map((child: any) =>
            child.category === "block" ? visit(child) : child,
          ),
        };
  return filters.map(visit);
};

export const replaceOrAppend = (
  children: any[],
  item: any,
  replaceId?: string | null,
) =>
  replaceId
    ? children.map((child) => (child.id === replaceId ? item : child))
    : [...children, item];

export const cloneCustomBlock = (customBlock: any) => {
  const nestedBlockIds: string[] = [];
  const cloneBlock = (blockToClone: any, isTopLevel: boolean): any => {
    const cloned = {
      ...blockToClone,
      id: uuidv4(),
      customBlockName: isTopLevel
        ? customBlock.name.replace(/^Custom\./, "")
        : blockToClone.customBlockName,
      children: (blockToClone.children ?? []).map((child: any) =>
        child.category === "block"
          ? cloneBlock(child, false)
          : {
              ...child,
              id: uuidv4(),
              ...(child.value && typeof child.value === "object"
                ? { value: deepCopy(child.value) }
                : {}),
              ...(child.listCondition
                ? { listCondition: deepCopy(child.listCondition) }
                : {}),
            },
      ),
    };
    if (!isTopLevel) nestedBlockIds.push(cloned.id);
    return cloned;
  };
  return { block: cloneBlock(customBlock.block, true), nestedBlockIds };
};

export const findItem = (items: any[], id: string): any => {
  for (const item of items ?? []) {
    if (item.id === id) return item;
    const found = findItem(item.children, id);
    if (found) return found;
  }
  return null;
};

const removeFrom = (block: any, id: string): any => ({
  ...block,
  children: (block.children ?? [])
    .filter((child: any) => child.id !== id)
    .map((child: any) =>
      child.category === "block" ? removeFrom(child, id) : child,
    ),
});

export const insertItem = (
  filters: any[],
  blockId: string,
  item: any,
  anchorId: string | null = null,
  after = false,
) =>
  mapBlock(filters, blockId, (block) => {
    const children = [...(block.children ?? [])];
    const anchor = anchorId
      ? children.findIndex((child) => child.id === anchorId)
      : -1;
    children.splice(
      anchor === -1 ? children.length : anchor + (after ? 1 : 0),
      0,
      item,
    );
    return { ...block, children };
  });

export const cloneWithNewIds = (item: any): any => {
  const copy = deepCopy(item);
  const renew = (node: any) => {
    node.id = uuidv4();
    (node.children ?? []).forEach(renew);
  };
  renew(copy);
  return copy;
};

export const dropItem = (
  filters: any[],
  itemId: string,
  blockId: string,
  anchorId: string | null,
  after: boolean,
  copy: boolean,
) => {
  const item = findItem(filters, itemId);
  if (!item) return filters;
  if (copy) {
    return insertItem(filters, blockId, cloneWithNewIds(item), anchorId, after);
  }
  if (anchorId === itemId || findItem([item], blockId)) return filters;
  return insertItem(
    filters.map((root) => removeFrom(root, itemId)),
    blockId,
    item,
    anchorId,
    after,
  );
};
