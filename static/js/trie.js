const Trie = () => {
  const trieRoot = {};

  const getAllPathsFromHere = (trieNode) => {
    const matches = [];
    Object.keys(trieNode).forEach((key) => {
      if (key !== "matchTerminatesHere") {
        getAllPathsFromHere(trieNode[key]).forEach((subMatch) => {
          matches.push(key + subMatch);
        });
      }
    });
    if (trieNode.matchTerminatesHere) {
      matches.push("");
    }
    return matches;
  };

  return {
    insert: (word) => {
      let thisLevel = trieRoot;
      for (let i = 0; i < word.length; i += 1) {
        const char = word[i];
        if (!thisLevel[char]) {
          thisLevel[char] = { matchTerminatesHere: false };
        }
        thisLevel = thisLevel[char];
      }
      thisLevel.matchTerminatesHere = true;
    },

    findAllStartingWith: (prefix) => {
      const matches = [];
      let thisLevel = trieRoot;
      for (let i = 0; i < prefix.length; i += 1) {
        const char = prefix[i];
        if (!thisLevel[char]) {
          return matches;
        }
        thisLevel = thisLevel[char];
      }
      getAllPathsFromHere(thisLevel).forEach((match) => {
        matches.push(prefix + match);
      });
      return matches;
    },
  };
};

export default Trie;
