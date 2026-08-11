/** Characters XML 1.0 forbids outright, plus the two non-characters and
 *  unpaired surrogates.
 *
 *  An RSS library will not do this for you: `feed` passes these straight
 *  through and the document it produces does not parse. Whether a byte is
 *  legal in XML is a question about the data rather than about serialisation,
 *  so it stays the caller's job. It matters because one bad byte anywhere
 *  makes the whole document ill-formed, and a reader drops the entire feed
 *  rather than the one item, without reporting anything.
 *
 *  Tab, newline and carriage return are legal and are kept. */
const ILLEGAL =
  // eslint-disable-next-line no-control-regex
  /[\u0000-\u0008\u000B\u000C\u000E-\u001F\uFFFE\uFFFF]|[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/g;

export function safe(text: string): string {
  return text.replace(ILLEGAL, "");
}
