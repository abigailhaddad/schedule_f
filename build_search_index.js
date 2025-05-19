const MiniSearch = require('minisearch');
const fs = require('fs');
const raw = require('./frontend/data.json');

const miniSearch = new MiniSearch({
  fields: ['title', 'key_quote', 'comment'],
  storeFields: ['id'],
  idField: 'id'
});

miniSearch.addAll(raw);

// Get the serialized representation of the MiniSearch instance
// The output of toJSON() is already an object (not a string)
const serializedIndex = miniSearch.toJSON();
console.log('MiniSearch serialized index created');

// Create a map of ID to document for quick lookup
const resultMap = Object.fromEntries(raw.map(r => [r.id, r]));
console.log('Result map created with', Object.keys(resultMap).length, 'entries');

// Serialize to JSON strings
const indexJsonString = JSON.stringify(serializedIndex);
const mapJsonString = JSON.stringify(resultMap);

console.log('Writing search_index.json');
fs.writeFileSync('./frontend/search_index.json', indexJsonString);

console.log('Writing result_map.json');
fs.writeFileSync('./frontend/result_map.json', mapJsonString);

console.log('Files written successfully');
