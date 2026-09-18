/* The one place the shared-file layout is defined.
 *
 * The native half (bridge_check.py) PARSES this file for its constants rather
 * than restating them, so the two sides cannot drift. That discipline is here
 * because it was learned the hard way: the worker's launch environment was
 * written down twice and the copies disagreed, and it now has a test enforcing
 * a single source.
 *
 * Layout, all little-endian:
 *   0  magic        "NSBR"          4 bytes
 *   4  state        u32             see the NSB_* states below
 *   8  round        u32             the round the native side is on
 *  12  payload_len  u32             valid bytes of payload
 *  16  reserved     48 bytes
 *  64  payload      NSB_CAPACITY bytes
 */
#define NSB_MAGIC        "NSBR"
#define NSB_HDR_BYTES    64u
#define NSB_MAGIC_OFF    0u
#define NSB_STATE_OFF    4u
#define NSB_ROUND_OFF    8u
#define NSB_LEN_OFF      12u
#define NSB_PAYLOAD_OFF  64u

/* Big enough for one 2560x1440 RGBA frame: 14745600 bytes. Sized to the frame
 * being moved rather than to something convenient, because the whole question is
 * how a frame of that size crosses the boundary. */
#define NSB_CAPACITY     (16u * 1024u * 1024u)

/* Handshake states. The native side creates the file and drives the rounds. */
#define NSB_FRESH        0u
#define NSB_NATIVE_WROTE 1u   /* native has filled the payload, windows should read it */
#define NSB_WIN_WROTE    2u   /* windows has filled the payload, native should read it */
#define NSB_DONE         3u   /* native is finished; windows should exit */
#define NSB_WIN_READY    0x57u /* windows has the mapping and is polling */

/* Each side fills the payload with its own byte, so a successful round proves
 * coherence in both directions without either side needing to know the other's
 * algorithm. */
#define NSB_NATIVE_BYTE  0xA5u
#define NSB_WIN_BYTE     0x5Au
