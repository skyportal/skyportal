// A simple trie (aka prefix tree) implementation (https://en.wikipedia.org/wiki/Trie)
// Initialized empty: `const trie = Trie()`
// Returns an object that supports the following methods:
//  `insert(word)` - inserts the word into the trie
//  `findAllStartingWith(prefix)` - returns an array of all words in the trie that start with the given prefix
//  `someStartWith(prefix)` - returns true if there is at least one word in the trie that starts with the given prefix

const Trie = () => {
  const trieRoot = {};

  const getAllPathsFromHere = (trieNode) => {
    const matches = [];

    const traverseAndSaveMatches = (currNode = trieNode, currStr = "") => {
      if (currNode.matchTerminatesHere) {
        matches.push(currStr);
      }
      Object.keys(currNode)
        .filter((key) => key !== "matchTerminatesHere")
        .forEach((char) => {
          traverseAndSaveMatches(currNode[char], currStr + char);
        });
    };

    traverseAndSaveMatches();

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

    someStartWith: (prefix) => {
      let thisLevel = trieRoot;
      for (let i = 0; i < prefix.length; i += 1) {
        const char = prefix[i];
        if (!thisLevel[char]) {
          return false;
        }
        thisLevel = thisLevel[char];
      }
      return true;
    },
  };
};

export default Trie;
