// What does one GPU round trip cost under Wine?
//
// The frame pipeline spends ~55ms per frame even when the frame is 64KB and NGX
// is switched off (bypass128 = 64.5ms, bypass at 1280x720 = 54.9ms), so the cost
// is neither the bytes nor the network. The remaining candidate is
// synchronisation: the host submits to the queue and waits on a fence every
// frame, and under Wine each of those is a wine-server and driver round trip.
// The host source shows both a per-frame fence wait (SetEventOnCompletion +
// WaitForSingleObject, lines 546-558 and 1784-1799) and a pipe poll loop with
// Sleep(8) per poll (lines 4741-4748).
//
// This measures that in isolation: no NGX, no swapchain, no window, no pipe.
// One question — if a submit+wait costs ~15ms, no host we write can avoid it and
// the pipeline's ceiling is real. If it costs ~1ms, the current host is spending
// ~50ms a frame on its own design and a host that pipelines could get past it.
//
// Headless on purpose: the worker's own M0 gate established that a standalone
// D3D12 device works here without a carrier or a swapchain, and adding a window
// would measure DXVK's present path instead of the sync path.

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <dxgi1_6.h>
#include <d3d12.h>
#include <cstdio>
#include <cstdint>

static double now_s()
{
    static LARGE_INTEGER freq = {};
    if (freq.QuadPart == 0) QueryPerformanceFrequency(&freq);
    LARGE_INTEGER t;
    QueryPerformanceCounter(&t);
    return static_cast<double>(t.QuadPart) / static_cast<double>(freq.QuadPart);
}

static void ms(const char *what, double total, int n)
{
    printf("    %-34s %8.3f ms each   (%d of them, %.1f ms total)\n",
           what, 1000.0 * total / n, n, 1000.0 * total);
}

static const char *hr_text(HRESULT hr, char *buf, size_t n)
{
    snprintf(buf, n, "0x%08lX", static_cast<unsigned long>(hr));
    return buf;
}

#define TRY(expr, what)                                                        \
    do {                                                                       \
        HRESULT hr_ = (expr);                                                  \
        if (FAILED(hr_)) {                                                     \
            char b_[32];                                                       \
            fprintf(stderr, "probe: %s failed: %s\n", what, hr_text(hr_, b_,   \
                    sizeof b_));                                               \
            return 1;                                                          \
        }                                                                      \
    } while (0)

// A frame-sized buffer, so the copies are the same size the real loop moves.
static const UINT64 FRAME_BYTES = 2560ull * 1440ull * 4ull;   // 14,745,600

int main()
{
    SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED);

    // --- adapter -----------------------------------------------------------
    IDXGIFactory1 *factory = nullptr;
    TRY(CreateDXGIFactory1(IID_PPV_ARGS(&factory)), "CreateDXGIFactory1");

    IDXGIAdapter1 *picked = nullptr;
    char name[256] = "<none>";
    UINT vendor = 0;
    for (UINT i = 0; factory->EnumAdapters1(i, &picked) == S_OK; ++i)
    {
        DXGI_ADAPTER_DESC1 d = {};
        picked->GetDesc1(&d);
        if (d.VendorId == 0x10DE)
        {
            vendor = d.VendorId;
            WideCharToMultiByte(CP_UTF8, 0, d.Description, -1, name,
                                sizeof name, nullptr, nullptr);
            break;
        }
        picked->Release();
        picked = nullptr;
    }
    if (picked == nullptr)
    {
        fprintf(stderr, "probe: no NVIDIA adapter (the worker rejects others)\n");
        return 1;
    }
    printf("  adapter: %s vendor=0x%04X\n", name, vendor);
    printf("  frame-sized buffers: %.1f MB\n", FRAME_BYTES / 1e6);

    // --- device, queue, list, fence ---------------------------------------
    ID3D12Device *dev = nullptr;
    TRY(D3D12CreateDevice(picked, D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&dev)),
        "D3D12CreateDevice");

    D3D12_COMMAND_QUEUE_DESC qd = {};
    qd.Type = D3D12_COMMAND_LIST_TYPE_DIRECT;
    ID3D12CommandQueue *queue = nullptr;
    TRY(dev->CreateCommandQueue(&qd, IID_PPV_ARGS(&queue)), "CreateCommandQueue");

    ID3D12CommandAllocator *alloc[4] = {};
    ID3D12GraphicsCommandList *list[4] = {};
    for (int i = 0; i < 4; ++i)
    {
        TRY(dev->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,
                                        IID_PPV_ARGS(&alloc[i])),
            "CreateCommandAllocator");
        TRY(dev->CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_DIRECT, alloc[i],
                                   nullptr, IID_PPV_ARGS(&list[i])),
            "CreateCommandList");
        list[i]->Close();
    }

    ID3D12Fence *fence = nullptr;
    TRY(dev->CreateFence(0, D3D12_FENCE_FLAG_NONE, IID_PPV_ARGS(&fence)),
        "CreateFence");
    HANDLE ev = CreateEventW(nullptr, FALSE, FALSE, nullptr);
    if (ev == nullptr) { fprintf(stderr, "probe: CreateEventW failed\n"); return 1; }
    UINT64 fv = 0;

    // --- buffers ----------------------------------------------------------
    D3D12_HEAP_PROPERTIES hp_up = {}, hp_def = {}, hp_rb = {};
    hp_up.Type  = D3D12_HEAP_TYPE_UPLOAD;
    hp_def.Type = D3D12_HEAP_TYPE_DEFAULT;
    hp_rb.Type  = D3D12_HEAP_TYPE_READBACK;

    D3D12_RESOURCE_DESC bd = {};
    bd.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
    bd.Width = FRAME_BYTES;
    bd.Height = 1;
    bd.DepthOrArraySize = 1;
    bd.MipLevels = 1;
    bd.SampleDesc.Count = 1;
    bd.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;

    ID3D12Resource *up = nullptr, *def = nullptr, *rb = nullptr;
    TRY(dev->CreateCommittedResource(&hp_up, D3D12_HEAP_FLAG_NONE, &bd,
        D3D12_RESOURCE_STATE_GENERIC_READ, nullptr, IID_PPV_ARGS(&up)),
        "CreateCommittedResource(upload)");
    TRY(dev->CreateCommittedResource(&hp_def, D3D12_HEAP_FLAG_NONE, &bd,
        D3D12_RESOURCE_STATE_COPY_DEST, nullptr, IID_PPV_ARGS(&def)),
        "CreateCommittedResource(default)");
    TRY(dev->CreateCommittedResource(&hp_rb, D3D12_HEAP_FLAG_NONE, &bd,
        D3D12_RESOURCE_STATE_COPY_DEST, nullptr, IID_PPV_ARGS(&rb)),
        "CreateCommittedResource(readback)");

    void *mapped = nullptr;
    TRY(up->Map(0, nullptr, &mapped), "Map(upload)");
    memset(mapped, 0xA5, static_cast<size_t>(FRAME_BYTES));

    int failures = 0;

    // Filled in by the blocks below and read by the verdict at the end.
    double a_submit_ms = 0, a_wait_ms = 0, a_total_ms = 0;
    double b_noop_ms = 0, c_spin_ms = 0, d_pipelined_ms = 0, e_total_ms = 0;

    // --- A: submit and wait, the way the host does it per frame -----------
    printf("\n  A. submit + fence wait, one frame at a time (the host's shape)\n");
    {
        const int N = 20;
        double submit = 0, wait = 0, total = 0;
        for (int i = 0; i < N; ++i)
        {
            alloc[0]->Reset();
            list[0]->Reset(alloc[0], nullptr);
            // A real submission, not an empty one: 4 bytes is enough.
            list[0]->CopyBufferRegion(def, 0, up, 0, 4);
            list[0]->Close();

            double t0 = now_s();
            ID3D12CommandList *cl = list[0];
            queue->ExecuteCommandLists(1, &cl);
            const UINT64 v = ++fv;
            queue->Signal(fence, v);
            double t1 = now_s();

            if (fence->GetCompletedValue() < v)
            {
                fence->SetEventOnCompletion(v, ev);
                if (WaitForSingleObject(ev, 5000) != WAIT_OBJECT_0)
                {
                    fprintf(stderr, "probe: fence wait timed out in A\n");
                    ++failures;
                    break;
                }
            }
            double t2 = now_s();
            submit += t1 - t0;
            wait += t2 - t1;
            total += t2 - t0;
        }
        ms("ExecuteCommandLists + Signal", submit, N);
        ms("the wait for it to finish", wait, N);
        ms("the whole round trip", total, N);
        a_submit_ms = 1000.0 * submit / N;
        a_wait_ms   = 1000.0 * wait / N;
        a_total_ms  = 1000.0 * total / N;
    }

    // --- B: the same wait with nothing to wait for ------------------------
    // Isolates the wine-server/event cost from the GPU work. If this is already
    // ~10ms, the cost is Wine's, not the card's.
    printf("\n  B. fence wait on an already-complete value (no GPU work)\n");
    {
        const int N = 20;
        double total = 0;
        for (int i = 0; i < N; ++i)
        {
            double t0 = now_s();
            fence->SetEventOnCompletion(fv, ev);   // fv is complete by now
            WaitForSingleObject(ev, 5000);
            total += now_s() - t0;
        }
        ms("SetEventOnCompletion + Wait", total, N);
        b_noop_ms = 1000.0 * total / N;
    }

    // --- C: same thing, spinning instead of waiting on an event -----------
    printf("\n  C. submit, then poll GetCompletedValue instead of waiting\n");
    {
        const int N = 20;
        double total = 0;
        for (int i = 0; i < N; ++i)
        {
            alloc[0]->Reset();
            list[0]->Reset(alloc[0], nullptr);
            list[0]->CopyBufferRegion(def, 0, up, 0, 4);
            list[0]->Close();

            double t0 = now_s();
            ID3D12CommandList *cl = list[0];
            queue->ExecuteCommandLists(1, &cl);
            const UINT64 v = ++fv;
            queue->Signal(fence, v);
            while (fence->GetCompletedValue() < v) Sleep(0);
            total += now_s() - t0;
        }
        ms("submit + spin to completion", total, N);
        c_spin_ms = 1000.0 * total / N;
    }

    // --- D: pipelined, no wait per frame ---------------------------------
    // If this is much cheaper per frame than A, the design that pays is depth:
    // the current loop is strictly serial, send then wait for the result.
    printf("\n  D. 20 submits back to back, one wait at the end\n");
    {
        const int N = 20;
        double t0 = now_s();
        for (int i = 0; i < N; ++i)
        {
            ID3D12CommandAllocator *a = alloc[i % 4];
            a->Reset();
            list[i % 4]->Reset(a, nullptr);
            list[i % 4]->CopyBufferRegion(def, 0, up, 0, 4);
            list[i % 4]->Close();
            ID3D12CommandList *cl = list[i % 4];
            queue->ExecuteCommandLists(1, &cl);
            queue->Signal(fence, ++fv);
        }
        if (fence->GetCompletedValue() < fv)
        {
            fence->SetEventOnCompletion(fv, ev);
            WaitForSingleObject(ev, 10000);
        }
        ms("submit, no per-frame wait", now_s() - t0, N);
        d_pipelined_ms = 1000.0 * (now_s() - t0) / N;
    }

    // --- E: a frame-sized copy, two of them, with the sync ---------------
    printf("\n  E. a 14.7MB upload copy + 14.7MB readback, with the sync\n");
    {
        const int N = 10;
        double record = 0, sync = 0, total = 0;
        for (int i = 0; i < N; ++i)
        {
            double t0 = now_s();
            alloc[0]->Reset();
            list[0]->Reset(alloc[0], nullptr);
            list[0]->CopyBufferRegion(def, 0, up, 0, FRAME_BYTES);
            list[0]->CopyBufferRegion(rb, 0, def, 0, FRAME_BYTES);
            list[0]->Close();
            double t1 = now_s();

            ID3D12CommandList *cl = list[0];
            queue->ExecuteCommandLists(1, &cl);
            const UINT64 v = ++fv;
            queue->Signal(fence, v);
            if (fence->GetCompletedValue() < v)
            {
                fence->SetEventOnCompletion(v, ev);
                if (WaitForSingleObject(ev, 10000) != WAIT_OBJECT_0)
                {
                    fprintf(stderr, "probe: fence wait timed out in E\n");
                    ++failures;
                    break;
                }
            }
            double t2 = now_s();
            record += t1 - t0;
            sync += t2 - t1;
            total += t2 - t0;
        }
        ms("recording the two copies", record, N);
        ms("submit + wait", sync, N);
        ms("the whole frame-shaped pass", total, N);
        e_total_ms = 1000.0 * total / N;
    }

    // --- verdict ----------------------------------------------------------
    printf("\n");
    if (failures) printf("  note: %d measurement(s) did not complete\n", failures);

    printf("  what the pipeline spends on a frame of ANY size, measured earlier:\n");
    printf("    a 64KB frame with NGX off   64.5ms\n");
    printf("    a 3.7MB frame with NGX off  54.9ms\n");
    printf("  so ~55ms a frame goes on something that is not the bytes.\n\n");

    printf("  one submit+wait round trip:  %7.2fms  (the wait alone: %.2fms)\n",
           a_total_ms, a_wait_ms);
    printf("  that wait with no GPU work:  %7.2fms  <- Wine's own cost, nothing\n",
           b_noop_ms);
    printf("                                       else in the process\n");
    printf("  submit then poll instead:    %7.2fms\n", c_spin_ms);
    printf("  submit, never wait per frame:%7.2fms\n", d_pipelined_ms);
    printf("  14.7MB copy + 14.7MB readback:%7.2fms  (with the sync)\n", e_total_ms);
    printf("\n");

    // The discriminator is B: waiting on an already-complete fence with no GPU
    // work involved. Whatever that costs is paid by every single wait, whoever
    // wrote the host, so it is the part that is not ours to fix.
    if (b_noop_ms >= 5.0)
    {
        printf("  RESULT: WAITING ITSELF COSTS %.1fms in Wine.\n", b_noop_ms);
        printf("  With no GPU work outstanding, no copies and no NGX, a single\n");
        printf("  fence wait already costs that. Three or four of those a frame is\n");
        printf("  the pipeline's ~55ms. No host we write avoids it — that is Wine's\n");
        printf("  synchronisation latency, and it is why the frame rate does not\n");
        printf("  move when the frame gets smaller.\n");
    }
    else if (a_wait_ms >= 5.0)
    {
        printf("  RESULT: THE WAIT FOR REAL WORK COSTS %.1fms, while waiting on an\n",
               a_wait_ms);
        printf("  already-complete fence costs %.1fms. So it is the round trip to the\n",
               b_noop_ms);
        printf("  GPU, not Wine's event handling. Real work is involved, which means\n");
        printf("  a host could overlap it instead of waiting: see the no-wait row.\n");
    }
    else if (a_total_ms >= 5.0)
    {
        printf("  RESULT: SUBMITTING COSTS %.1fms, not waiting (%.1fms). The host does\n",
               a_total_ms, a_wait_ms);
        printf("  several submits per frame, which would be where the ~55ms comes\n");
        printf("  from — and a host we write could use fewer.\n");
    }
    else
    {
        printf("  RESULT: SYNCHRONISATION IS CHEAP — %.1fms for a full round trip, and\n",
               a_total_ms);
        printf("  %.1fms for a frame-sized copy with the sync. Neither accounts for the\n",
               e_total_ms);
        printf("  pipeline's ~55ms, so the fixed cost is in the host's own design and\n");
        printf("  a host we write could plausibly get past it.\n");
    }

    up->Unmap(0, nullptr);
    for (int i = 0; i < 4; ++i) { list[i]->Release(); alloc[i]->Release(); }
    rb->Release(); def->Release(); up->Release();
    if (ev) CloseHandle(ev);
    fence->Release(); queue->Release(); dev->Release();
    picked->Release(); factory->Release();
    return failures ? 1 : 0;
}
