// A simple trie (aka prefix tree) implementation (https://en.wikipedia.org/wiki/Trie) that supports
// searching for users by supplying a prefix to their username, first name or last name.
// Case-insensitive.
// Initialized empty: `const trie = UsernameTrie()`
// Returns an object that supports the following methods:
//  `insertUser({ username: string, firstName: string, lastName: string })` - inserts the user's names into the trie
//  `findAllStartingWith(prefix, limit = Infinity)` - returns an object mapping username to `{ firstName, lastName }` for all user
//    objects in the trie with at least one of username, first name or last name matching the given prefix,
//    up to the given limit if provided, otherwise all matches are returned.

const UsernameTrie = () => {
  const trieRoot = {};

  const getAllMatchesFromHere = (trieNode, limit) => {
    const matches = {};
    let numMatches = 0;

    const traverseAndSaveMatches = (currNode = trieNode) => {
      if (currNode.matchTerminatesHere) {
        Object.keys(currNode.matchingUsersMap).forEach((username) => {
          if (!matches[username] && numMatches < limit) {
            matches[username] = currNode.matchingUsersMap[username];
            numMatches += 1;
          }
        });
      }
      if (numMatches >= limit) {
        return;
      }
      Object.keys(currNode)
        .filter(
          (key) => key !== "matchTerminatesHere" && key !== "matchingUsersMap",
        )
        .forEach((char) => {
          traverseAndSaveMatches(currNode[char]);
        });
    };

    traverseAndSaveMatches();

    return matches;
  };

  return {
    insertUser: ({ username, firstName, lastName }) => {
      [username, firstName, lastName]
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
          if (thisLevel.matchingUsersMap == null) {
            thisLevel.matchingUsersMap = {};
          }
          thisLevel.matchingUsersMap[username] = { firstName, lastName };
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

export default UsernameTrie;
