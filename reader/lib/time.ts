/** Display timezone. An IANA name, not a fixed offset: Sydney is UTC+10 in
 *  winter and UTC+11 over daylight saving, and the abbreviation changes with
 *  it. Both the server and the client format with an explicit locale and zone
 *  so they produce the same string and hydration matches. */
export const ZONE = "Australia/Sydney";
const LOCALE = "en-AU";

/** The day the post belongs to *in the display zone*, which is what the
 *  separator has to key on — 23:30 UTC is the next day in Sydney. */
export function dayOf(iso: string): string {
  return new Date(iso).toLocaleDateString(LOCALE, {
    timeZone: ZONE,
    day: "numeric",
    month: "long",
  });
}

/** Time with its zone abbreviation, so AEST and AEDT are distinguishable. */
export function timeOf(iso: string): string {
  return new Date(iso).toLocaleTimeString(LOCALE, {
    timeZone: ZONE,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZoneName: "short",
  });
}

/** One line: date and time when the day changes, time alone when it does not. */
export function stamp(iso: string, dayChanged: boolean): string {
  return dayChanged ? `${dayOf(iso)} · ${timeOf(iso)}` : timeOf(iso);
}
