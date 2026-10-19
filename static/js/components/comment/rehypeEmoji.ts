import emoji from "emoji-dictionary";

const replaceEmoji = (node: any) => {
  if (node.type === "text") {
    node.value = node.value.replace(/:\w+:/gi, (name: string) => {
      // The name map is a plain object, so :constructor: etc. hit prototype
      // members; only strings are emoji.
      const unicode = emoji.getUnicode(name);
      return typeof unicode === "string" ? unicode : name;
    });
  } else if (node.tagName !== "code") {
    node.children?.forEach(replaceEmoji);
  }
};

// Rehype plugin for :name: shortcodes outside code, since react-markdown's
// `components` can only override elements, not text.
export const rehypeEmoji = () => replaceEmoji;
