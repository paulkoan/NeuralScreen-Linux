/* The Windows half of the shared-file bridge test.
 *
 * Why this program exists. The DLSS worker is a prebuilt Windows binary whose
 * only input paths are a stdin pipe and a Windows named section. That is the
 * constraint behind the MVP's ~85ms floor at 2560x1440 with the network switched
 * off: every frame goes out through a pipe, into a D3D12 texture, back out
 * through a pipe. Named sections are not reachable from a native Linux process,
 * which is what blocked shared memory. A FILE is reachable: Wine maps "/" as
 * "Z:\", so a native Linux process and a Wine process can map the same file, and
 * the kernel page cache makes those the same physical pages.
 *
 * This is the smallest thing that proves or disproves that. It is not the
 * worker, and it does not touch D3D12 or NGX — if the pages are not shared, none
 * of the rest matters and the whole own-host pathway is dead.
 *
 * Build (on the Linux box, cross-compiling):
 *   x86_64-w64-mingw32-gcc -O2 -o bridge_win.exe bridge_win.c
 *
 * Run (under Wine, driven by bridge_check.py):
 *   wine bridge_win.exe 'Z:\tmp\nsb\frame.bin' 10
 *
 * Exit codes: 0 all rounds coherent, 1 a mismatch or a failed call, 2 bad usage.
 */

#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bridge_layout.h"

static unsigned char *g_view;
static unsigned int   g_len;
static int            g_flush;   /* argv[2] == "flush"; see set_state */

/* Little-endian 32-bit accessors. The native side writes with struct.pack("<I")
 * and this must agree byte for byte. */
static unsigned int rd32(unsigned int off)
{
    unsigned char *p = g_view + off;
    return (unsigned int)p[0] | ((unsigned int)p[1] << 8) |
           ((unsigned int)p[2] << 16) | ((unsigned int)p[3] << 24);
}

static void wr32(unsigned int off, unsigned int v)
{
    unsigned char *p = g_view + off;
    p[0] = (unsigned char)(v & 0xFF);
    p[1] = (unsigned char)((v >> 8) & 0xFF);
    p[2] = (unsigned char)((v >> 16) & 0xFF);
    p[3] = (unsigned char)((v >> 24) & 0xFF);
}

static void set_state(unsigned int v)
{
    wr32(NSB_STATE_OFF, v);
    /* Flushing is off by default, and the reason is a measurement: a per-round
     * flush forces writeback and dominated the first version's numbers, 14ms
     * for a 3MB write that should take 0.3ms. Coherence does not need it — two
     * mappings of one file are the same physical pages — so the real
     * implementation must not pay it per frame. Kept behind a flag so the cost
     * can be measured rather than assumed. */
    if (g_flush)
        FlushViewOfFile(g_view, NSB_HDR_BYTES);
}

/* Wait for either of two states. Needed because DONE can only arrive after a
 * round, so waiting on it alone blocks for the full timeout on every round —
 * which is what the first version of this loop did. */
static int wait_for_either(unsigned int a, unsigned int b, unsigned int timeout_ms)
{
    unsigned int waited = 0;
    for (;;) {
        unsigned int st = rd32(NSB_STATE_OFF);
        if (st == a || st == b)
            return (int)st;
        if (waited >= timeout_ms) {
            fprintf(stderr, "bridge_win: timed out waiting for state %u or %u "
                            "(saw %u)\n", a, b, st);
            return -1;
        }
        Sleep(1);
        waited += 1;
    }
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: bridge_win <Z:\\path\\to\\frame.bin> [rounds]\n");
        return 2;
    }
    const char *path = argv[1];
    g_flush = (argc > 2 && strcmp(argv[2], "flush") == 0);
    int timed_out = 0;
    unsigned int rounds_seen = 0, mismatches = 0, round;
    double worst_ms = 0.0;

    HANDLE file = CreateFileA(path, GENERIC_READ | GENERIC_WRITE,
                              FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
                              OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) {
        fprintf(stderr, "bridge_win: CreateFileA('%s') failed: %lu\n",
                path, (unsigned long)GetLastError());
        return 1;
    }

    LARGE_INTEGER size;
    if (!GetFileSizeEx(file, &size)) {
        fprintf(stderr, "bridge_win: GetFileSizeEx failed: %lu\n",
                (unsigned long)GetLastError());
        CloseHandle(file);
        return 1;
    }
    printf("bridge_win: opened %s, %lld bytes\n", path, (long long)size.QuadPart);

    HANDLE map = CreateFileMappingA(file, NULL, PAGE_READWRITE, 0, 0, NULL);
    if (map == NULL) {
        fprintf(stderr, "bridge_win: CreateFileMapping failed: %lu\n",
                (unsigned long)GetLastError());
        CloseHandle(file);
        return 1;
    }
    g_view = (unsigned char *)MapViewOfFile(map, FILE_MAP_ALL_ACCESS, 0, 0, 0);
    if (g_view == NULL) {
        fprintf(stderr, "bridge_win: MapViewOfFile failed: %lu\n",
                (unsigned long)GetLastError());
        CloseHandle(map);
        CloseHandle(file);
        return 1;
    }

    if (memcmp(g_view + NSB_MAGIC_OFF, NSB_MAGIC, 4) != 0) {
        fprintf(stderr, "bridge_win: bad magic — the native side had not "
                        "written the file when we mapped it\n");
        return 1;
    }
    g_len = rd32(NSB_LEN_OFF);
    if (g_len == 0 || g_len > NSB_CAPACITY) {
        fprintf(stderr, "bridge_win: implausible payload_len %u\n", g_len);
        return 1;
    }
    printf("bridge_win: mapping is live, payload_len %u, telling the native "
           "side we are up\n", g_len);
    set_state(NSB_WIN_READY);

    for (;;) {
        int st = wait_for_either(NSB_DONE, NSB_NATIVE_WROTE, 20000);
        if (st < 0) {
            timed_out = 1;
            break;
        }
        if ((unsigned int)st == NSB_DONE)
            break;
        LARGE_INTEGER t0, t1, freq;
        QueryPerformanceFrequency(&freq);
        QueryPerformanceCounter(&t0);

        round = rd32(NSB_ROUND_OFF);

        /* Read what the native side wrote. Every byte must be its pattern: one
         * byte it never wrote means the pages are not shared. */
        unsigned int bad = 0, i;
        for (i = 0; i < g_len; i++) {
            if (g_view[NSB_PAYLOAD_OFF + i] != (unsigned char)NSB_NATIVE_BYTE)
                bad++;
        }
        if (bad) {
            mismatches++;
            fprintf(stderr, "bridge_win: round %u: %u of %u bytes were not "
                            "0x%02X\n", round, bad, g_len, NSB_NATIVE_BYTE);
        }

        /* Answer with our own pattern. */
        memset(g_view + NSB_PAYLOAD_OFF, NSB_WIN_BYTE, g_len);
        if (g_flush)
            FlushViewOfFile(g_view + NSB_PAYLOAD_OFF, g_len);

        QueryPerformanceCounter(&t1);
        double ms = (double)(t1.QuadPart - t0.QuadPart) * 1000.0
                    / (double)freq.QuadPart;
        if (ms > worst_ms)
            worst_ms = ms;
        printf("bridge_win: round %u: read %u bytes, wrote %u, %.1f ms\n",
               round, g_len, g_len, ms);
        fflush(stdout);

        rounds_seen++;
        set_state(NSB_WIN_WROTE);
    }

    printf("bridge_win: %u rounds, %u with mismatches, worst %.1f ms\n",
           rounds_seen, mismatches, worst_ms);
    UnmapViewOfFile(g_view);
    CloseHandle(map);
    CloseHandle(file);

    if (timed_out)
        return 1;
    return mismatches ? 1 : 0;
}