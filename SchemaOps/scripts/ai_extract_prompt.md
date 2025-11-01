You are extracting product attribute schema changes from marketplace specification documents.

Return JSON with fields: attributeName, required, dataType, maxLength, allowedValues, conditionalRequired, effectiveFrom.

Guidelines:
- Parse tables and bullet lists
- Normalize booleans and lengths
- If uncertain, set null and add note in comments

Examples:
- Input snippet: "title: required, max length 150"
- Output JSON: {"attributeName":"title","required":true,"dataType":"string","maxLength":150}






