/* Read-only browser status, shared with RetroArch's core thread. */
#include "runtime-status.h"
#include <stdint.h>

#ifdef __EMSCRIPTEN__
#include <emscripten/emscripten.h>
#else
#define EMSCRIPTEN_KEEPALIVE
#endif

static uint32_t presented_frames;
static int restore_result;

EMSCRIPTEN_KEEPALIVE uint32_t runtime_get_frame_count(void)
{
   return __atomic_load_n(&presented_frames, __ATOMIC_ACQUIRE);
}

EMSCRIPTEN_KEEPALIVE int runtime_get_restore_result(void)
{
   return __atomic_load_n(&restore_result, __ATOMIC_ACQUIRE);
}

void runtime_frame_presented(void)
{
   __atomic_fetch_add(&presented_frames, 1, __ATOMIC_RELEASE);
}

void runtime_restore_started(void)
{
   __atomic_store_n(&restore_result, 0, __ATOMIC_RELEASE);
}

void runtime_restore_finished(bool success)
{
   __atomic_store_n(&restore_result, success ? 1 : -1, __ATOMIC_RELEASE);
}
