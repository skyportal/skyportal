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
