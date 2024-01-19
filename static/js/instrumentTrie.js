// A simple trie (aka prefix tree) implementation (https://en.wikipedia.org/wiki/Trie) that supports
// searching for instruments by supplying a prefix to their instrument or telescope.
// Case-insensitive.
// Initialized empty: `const trie = InstrumentTrie()`
// Returns an object that supports the following methods:
//  `insertInstrument({ instrument: string, telescope: string })` - inserts the instruments names into the trie
//  `findAllStartingWith(prefix, limit = Infinity)` - returns an object mapping instrument to `{ instrument, telescope }` for all instruments
//    objects in the trie with at least one of instrument or telescope matching the given prefix,
//    up to the given limit if provided, otherwise all matches are returned.

const InstrumentTrie = () => {
  const trieRoot = {};

  const getAllMatchesFromHere = (trieNode, limit) => {
    const matches = {};
    let numMatches = 0;

    const traverseAndSaveMatches = (currNode = trieNode) => {
      if (currNode.matchTerminatesHere) {
        Object.keys(currNode.matchingInstrumentsMap).forEach((instrument) => {
          if (!matches[instrument] && numMatches < limit) {
            matches[instrument] = currNode.matchingInstrumentsMap[instrument];
            numMatches += 1;
          }
        });
      }
      if (numMatches >= limit) {
        return;
      }
      Object.keys(currNode)
        .filter(
          (key) =>
            key !== "matchTerminatesHere" && key !== "matchingInstrumentsMap",
        )
        .forEach((char) => {
          traverseAndSaveMatches(currNode[char]);
        });
    };

    traverseAndSaveMatches();

    return matches;
  };

  return {
    insertInstrument: ({ instrument, telescope }) => {
      [instrument, telescope]
        .filter((word) => word !== "")
        .map((word) => word.toLowerCase())
        .forEach((word) => {
          let thisLevel = trieRoot;
          for (let i = 0; i < word.length; i += 1) {
            const char = word[i];
            if (!thisLevel[char]) {
              thisLevel[char] = { matchTerminatesHere: false };
            }
            thisLevel = thisLevel[char];
          }
          thisLevel.matchTerminatesHere = true;
          if (thisLevel.matchingInstrumentsMap == null) {
            thisLevel.matchingInstrumentsMap = {};
          }
          thisLevel.matchingInstrumentsMap[instrument] = { telescope };
        });
    },

    findAllStartingWith: (prefix, limit = Infinity) => {
      let thisLevel = trieRoot;
      for (let i = 0; i < prefix.length; i += 1) {
        const char = prefix[i].toLowerCase();
        if (!thisLevel[char]) {
          return {};
        }
        thisLevel = thisLevel[char];
      }
      return getAllMatchesFromHere(thisLevel, limit);
    },
  };
};

export default InstrumentTrie;
