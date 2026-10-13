import test from 'node:test';
import assert from 'node:assert/strict';
import {csvCell} from '../src/csv.js';
test('CSV neutralizes formulas, leading whitespace and control characters without losing text',()=>{
  assert.equal(csvCell('=HYPERLINK("https://example.test")'),'"\'=HYPERLINK(""https://example.test"")"');
  assert.equal(csvCell(' \t+1+2'),'"\' \t+1+2"');
  assert.equal(csvCell('\n@SUM(1,2)'),'"\'\n@SUM(1,2)"');
  assert.equal(csvCell('＝1+1'),'"\'＝1+1"');
  assert.equal(csvCell('BIA, "project"'),'"BIA, ""project"""');
  assert.equal(csvCell(null),'""');
});
