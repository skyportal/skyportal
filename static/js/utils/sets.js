function not(a, b) {
  // we can't do indexOf on objects, so we need to compare the id
  return a.filter(
    (value) => b.findIndex((item) => item.id === value.id) === -1,
  );
}

function intersection(a, b) {
  return a.filter(
    (value) => b.findIndex((item) => item.id === value.id) !== -1,
  );
}

function union(a, b) {
  return [...a, ...not(b, a)];
}

export { not, intersection, union };
